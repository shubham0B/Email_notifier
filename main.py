import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure Windows terminal prints unicode emojis without cp1252 encoding error
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

from email_fetcher import get_mock_college_emails, fetch_live_emails
from classifier import classify_email
from formatter import build_whatsapp_digest
from news_fetcher import fetch_important_news
from document_generator import generate_digest_pdf
from whatsapp_sender import (
    send_whatsapp_message, 
    send_via_whatsapp_web, 
    send_via_local_gateway,
    send_document_via_gateway
)
from db import save_digest_run

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Dean's Email Automation & WhatsApp Digest")
    parser.add_argument("--mock", action="store_true", help="Run with realistic simulated college emails")
    parser.add_argument("--dry-run", action="store_true", help="Print WhatsApp message preview instead of sending")
    parser.add_argument("--live", action="store_true", help="Connect to live mailbox configured in .env")
    parser.add_argument("--web", action="store_true", help="Send directly via WhatsApp Web browser")
    parser.add_argument("--gateway", action="store_true", help="Send silently via background Local WhatsApp Gateway")
    parser.add_argument("--today", action="store_true", help="Fetch emails specifically sent today (default)")
    parser.add_argument("--yesterday", action="store_true", help="Fetch emails specifically sent yesterday")
    parser.add_argument("--all-unseen", action="store_true", help="Fetch all unread emails across all dates")
    parser.add_argument("--date", type=str, default=None, help="Fetch emails for a specific date (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, default=None, help="Start date for range search (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date for range search (YYYY-MM-DD)")
    args = parser.parse_args()

    from datetime import datetime, timedelta
    start_date = args.start_date
    end_date = args.end_date
    target_date = None

    if start_date and end_date:
        pass  # range mode
    elif args.date:
        target_date = args.date
    elif args.yesterday:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.all_unseen:
        target_date = None
    elif args.today:
        target_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Default: ALWAYS summarize today's emails only
        target_date = datetime.now().strftime("%Y-%m-%d")

    # Default to mock simulation if no flags provided or if credentials missing
    use_mock = args.mock or (not args.live and not os.getenv("EMAIL_USER"))
    
    # Check if local gateway is running and ready
    gateway_ready = False
    gateway_port = os.getenv("PORT", os.getenv("GATEWAY_PORT", "4020"))
    try:
        import requests
        r = requests.get(f"http://127.0.0.1:{gateway_port}/status", timeout=2)
        if r.status_code == 200 and r.json().get("whatsapp_connected"):
            gateway_ready = True
    except Exception:
        gateway_ready = False

    use_gateway = args.gateway or (gateway_ready and not args.web and not args.dry_run)
    is_dry_run = args.dry_run or (not args.web and not use_gateway and not os.getenv("TWILIO_ACCOUNT_SID"))

    print("=" * 60)
    print("🏛️  STARTING DEAN'S EMAIL DIGEST PIPELINE")
    print(f"Mode: {'MOCK SIMULATION' if use_mock else 'LIVE MAILBOX'}")
    if start_date and end_date:
        print(f"Target Date Range Filter: {start_date} to {end_date}")
    elif target_date:
        print(f"Target Date Filter: {target_date}")
    dispatch_mode = "CONSOLE PREVIEW (DRY-RUN)" if is_dry_run else ("LOCAL WHATSAPP GATEWAY" if use_gateway else ("WHATSAPP WEB" if args.web else "TWILIO CLOUD"))
    print(f"WhatsApp Dispatch: {dispatch_mode}")
    print("=" * 60)

    # 1. Fetch Emails
    if use_mock:
        print("\n[Step 1/4] Fetching simulated emails from college departments...")
        raw_emails = get_mock_college_emails()
    else:
        if start_date and end_date:
            print(f"\n[Step 1/4] Fetching emails from live mailbox for {start_date} to {end_date}...")
            raw_emails = fetch_live_emails(start_date=start_date, end_date=end_date)
        else:
            print(f"\n[Step 1/4] Fetching emails from live mailbox{' for ' + target_date if target_date else ''}...")
            raw_emails = fetch_live_emails(target_date=target_date)

    print(f"-> Ingested {len(raw_emails)} emails for analysis.")

    # 2. Classify and summarize
    print("\n[Step 2/4] Categorizing and generating 1-sentence summaries...")
    processed_emails = []
    
    def process_single_email(item):
        analysis = classify_email(
            subject=item["subject"],
            body=item["body"],
            sender=item["sender"]
        )
        return {**item, **analysis}

    if len(raw_emails) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            processed_emails = list(executor.map(process_single_email, raw_emails))
    elif len(raw_emails) == 1:
        processed_emails = [process_single_email(raw_emails[0])]

    for combined in processed_emails:
        print(f"  • [{combined['category']}] {combined['sender_name']}: {combined['summary']}")

    # 3. Fetch News & Generate PDF Document
    print("\n[Step 3/4] Constructing formatted WhatsApp digest with arrival timestamps...")
    digest_date_str = None
    file_date_str = None
    is_range = bool(start_date and end_date)

    if is_range:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d")
            e_dt = datetime.strptime(end_date, "%Y-%m-%d")
            digest_date_str = f"{s_dt.strftime('%b %d')} - {e_dt.strftime('%b %d, %Y')}"
        except Exception:
            digest_date_str = f"{start_date} to {end_date}"
        file_date_str = f"{start_date}_to_{end_date}"
    elif target_date:
        try:
            dt = datetime.strptime(target_date, "%Y-%m-%d")
            digest_date_str = dt.strftime("%A, %b %d, %Y")
        except Exception:
            digest_date_str = target_date
        file_date_str = target_date
    else:
        digest_date_str = datetime.now().strftime("%A, %b %d, %Y")
        file_date_str = datetime.now().strftime("%Y-%m-%d")

    from pa_manager import get_pa_agenda
    agenda_date = target_date or datetime.now().strftime("%Y-%m-%d")
    pa_agenda = get_pa_agenda(agenda_date)
    meetings_count = len(pa_agenda.get("meetings", []))
    reminders_count = len(pa_agenda.get("reminders", []))
    if meetings_count or reminders_count:
        print(f"📋 Loaded PA Agenda for {agenda_date}: {meetings_count} meeting(s), {reminders_count} reminder(s).")

    digest_message = build_whatsapp_digest(
        processed_emails, 
        digest_date_str=digest_date_str,
        include_date_in_timestamp=is_range,
        pa_agenda=pa_agenda
    )

    print("\n[Step 3b/4] Fetching Tech & Higher Education news headlines and generating PDF document...")
    news_data = fetch_important_news()
    pdf_path = generate_digest_pdf(
        processed_emails, 
        news_data, 
        digest_date_str=digest_date_str, 
        file_date_str=file_date_str,
        pa_agenda=pa_agenda
    )

    # Record digest into personal_whatsapp_db
    try:
        mode_str = "range" if is_range else (target_date or "today")
        save_digest_run(
            target_date=file_date_str,
            mode=mode_str,
            processed_emails=processed_emails,
            news_data=news_data,
            pdf_path=pdf_path
        )
    except Exception as e:
        print(f"⚠️ Could not record run to MySQL: {e}")

    # 4. Dispatch
    if use_gateway:
        print("\n[Step 4/4] Delivering digest and PDF document via Local WhatsApp Gateway (Silent/Headless)...")
        send_via_local_gateway(digest_message)
        send_document_via_gateway(
            pdf_path, 
            caption=f"📄 *Executive Briefing Document ({digest_date_str or 'Today'})*\n• Today's Executive Schedule & Appointments\n• Inbound Email Action Summaries\n• Tech & AI Breakthroughs (1-Day Previous)\n• Higher Education Intelligence (India, Global & Rajasthan)"
        )
    elif args.web:
        print("\n[Step 4/4] Delivering digest via WhatsApp Web...")
        send_via_whatsapp_web(digest_message)
    else:
        print("\n[Step 4/4] Delivering digest to WhatsApp...")
        send_whatsapp_message(digest_message, dry_run=is_dry_run)
        if is_dry_run:
            print(f"📄 [DRY-RUN] Executive PDF document created at: {pdf_path}")

    print("✨ Pipeline execution complete.")

if __name__ == "__main__":
    main()
