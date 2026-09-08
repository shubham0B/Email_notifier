import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure Windows terminal prints unicode emojis without cp1252 encoding error
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from email_fetcher import get_mock_college_emails, fetch_live_emails
from classifier import classify_email
from formatter import build_whatsapp_digest
from whatsapp_sender import send_whatsapp_message, send_via_whatsapp_web, send_via_local_gateway

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Dean's Email Automation & WhatsApp Digest")
    parser.add_argument("--mock", action="store_true", help="Run with realistic simulated college emails")
    parser.add_argument("--dry-run", action="store_true", help="Print WhatsApp message preview instead of sending")
    parser.add_argument("--live", action="store_true", help="Connect to live mailbox configured in .env")
    parser.add_argument("--web", action="store_true", help="Send directly via WhatsApp Web browser")
    parser.add_argument("--gateway", action="store_true", help="Send silently via background Local WhatsApp Gateway")
    parser.add_argument("--today", action="store_true", help="Fetch emails specifically sent today")
    parser.add_argument("--yesterday", action="store_true", help="Fetch emails specifically sent yesterday")
    parser.add_argument("--date", type=str, default=None, help="Fetch emails for a specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    from datetime import datetime, timedelta
    target_date = args.date
    if args.yesterday:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.today or (args.live and not target_date):
        target_date = datetime.now().strftime("%Y-%m-%d")

    # Default to mock simulation if no flags provided or if credentials missing
    use_mock = args.mock or (not args.live and not os.getenv("EMAIL_USER"))
    
    # Check if local gateway is running and ready
    gateway_ready = False
    try:
        import requests
        r = requests.get("http://localhost:3000/status", timeout=2)
        if r.status_code == 200 and r.json().get("whatsapp_connected"):
            gateway_ready = True
    except Exception:
        gateway_ready = False

    use_gateway = args.gateway or (gateway_ready and not args.web and not args.dry_run)
    is_dry_run = args.dry_run or (not args.web and not use_gateway and not os.getenv("TWILIO_ACCOUNT_SID"))

    print("=" * 60)
    print("🏛️  STARTING DEAN'S EMAIL DIGEST PIPELINE")
    print(f"Mode: {'MOCK SIMULATION' if use_mock else 'LIVE MAILBOX'}")
    if target_date:
        print(f"Target Date Filter: {target_date}")
    dispatch_mode = "CONSOLE PREVIEW (DRY-RUN)" if is_dry_run else ("LOCAL WHATSAPP GATEWAY" if use_gateway else ("WHATSAPP WEB" if args.web else "TWILIO CLOUD"))
    print(f"WhatsApp Dispatch: {dispatch_mode}")
    print("=" * 60)

    # 1. Fetch Emails
    if use_mock:
        print("\n[Step 1/4] Fetching simulated emails from college departments...")
        raw_emails = get_mock_college_emails()
    else:
        print(f"\n[Step 1/4] Fetching emails from live mailbox{' for ' + target_date if target_date else ''}...")
        raw_emails = fetch_live_emails(target_date=target_date)

    print(f"-> Ingested {len(raw_emails)} emails for analysis.")

    # 2. Classify and summarize
    print("\n[Step 2/4] Categorizing and generating 1-sentence summaries...")
    processed_emails = []
    for item in raw_emails:
        analysis = classify_email(
            subject=item["subject"],
            body=item["body"],
            sender=item["sender"]
        )
        combined = {**item, **analysis}
        processed_emails.append(combined)
        print(f"  • [{combined['category']}] {combined['sender_name']}: {combined['summary']}")

    # 3. Format WhatsApp Digest
    print("\n[Step 3/4] Constructing formatted WhatsApp digest with arrival timestamps...")
    digest_date_str = None
    if target_date:
        try:
            dt = datetime.strptime(target_date, "%Y-%m-%d")
            digest_date_str = dt.strftime("%A, %b %d, %Y")
        except Exception:
            digest_date_str = target_date
    digest_message = build_whatsapp_digest(processed_emails, digest_date_str=digest_date_str)

    # 4. Dispatch
    if args.gateway:
        print("\n[Step 4/4] Delivering digest via Local WhatsApp Gateway (Silent/Headless)...")
        send_via_local_gateway(digest_message)
    elif args.web:
        print("\n[Step 4/4] Delivering digest via WhatsApp Web...")
        send_via_whatsapp_web(digest_message)
    else:
        print("\n[Step 4/4] Delivering digest to WhatsApp...")
        send_whatsapp_message(digest_message, dry_run=is_dry_run)

    print("✨ Pipeline execution complete.")

if __name__ == "__main__":
    main()
