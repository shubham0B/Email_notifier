import os
import sys
import email
from email.header import decode_header
import imaplib
import re
import html
from datetime import datetime, timedelta
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import unicodedata

def sanitize_text(text: str) -> str:
    """Removes invisible, zero-width, non-printable characters, HTML entities, and normalizes spaces."""
    if not text:
        return ""
    # Unescape HTML entities (handles &zwnj;, &#847;, &nbsp;, etc.)
    text = html.unescape(text)
    # Remove zero-width chars, BOM, soft hyphens, combining grapheme joiners, control formatting
    text = re.sub(r'[\u200B-\u200F\uFEFF\u034F\u00AD\u2060\u180E\uFFF9-\uFFFB\u2028\u2029]', '', text)
    # Convert various non-breaking / special unicode spaces to normal space
    text = re.sub(r'[\u00A0\u2000-\u200A\u202F\u205F\u3000]', ' ', text)
    # Strip non-printable / control characters (except newline, carriage return, tab)
    text = ''.join(ch for ch in text if ch in ('\n', '\r', '\t') or not unicodedata.category(ch).startswith('C'))
    # Remove URLs/links and long tracking tokens
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\b(?:qs=)?[A-Za-z0-9_\-=+]{25,}\b', '', text)
    # Collapse long lines of divider characters (e.g., -------- or ====== or .....)
    text = re.sub(r'[-_=~*.]{4,}', ' ', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def clean_email_html(raw_html: str) -> str:
    """Strips tags, scripts, and CSS, leaving clean, readable human text."""
    if not raw_html:
        return ""
    # Strip script, style, head, noscript
    text = re.sub(r'<(script|style|head|noscript)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Convert structural HTML into newlines
    text = re.sub(r'<(br|p|div|tr|li|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Sanitize characters (remove hidden zero-width spaces, joiners, BOMs, entities)
    text = sanitize_text(text)
    # Filter blank lines and normalize whitespace
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
    clean = '\n'.join([l for l in lines if l])
    return clean

def extract_email_body(msg) -> str:
    """Extracts readable text from multipart or single-part message, falling back to clean HTML."""
    plain_text = ""
    html_text = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition"))
            if "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        decoded = payload.decode(charset, errors="ignore")
                    except Exception:
                        decoded = payload.decode("utf-8", errors="ignore")

                    if ctype == "text/plain" and not plain_text:
                        plain_text = decoded
                    elif ctype == "text/html" and not html_text:
                        html_text = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="ignore")
            except Exception:
                decoded = payload.decode("utf-8", errors="ignore")
            if msg.get_content_type() == "text/plain":
                plain_text = decoded
            else:
                html_text = decoded

    clean_plain = sanitize_text(plain_text)
    clean_html = clean_email_html(html_text) if html_text else ""

    # Count alphanumeric characters to pick whichever has real substance
    plain_alnum = len(re.findall(r'[a-zA-Z0-9]', clean_plain))
    html_alnum = len(re.findall(r'[a-zA-Z0-9]', clean_html))

    if html_alnum > plain_alnum and html_alnum > 25:
        return clean_html
    elif plain_alnum > 20:
        return clean_plain
    elif clean_html:
        return clean_html
    return clean_plain

def decode_full_header(header_val: str) -> str:
    """Decodes all chunks of an email header across multiple encodings."""
    if not header_val:
        return ""
    try:
        parts = decode_header(header_val)
        decoded = ""
        for chunk, enc in parts:
            if isinstance(chunk, bytes):
                decoded += chunk.decode(enc or "utf-8", errors="ignore")
            else:
                decoded += str(chunk)
        return sanitize_text(decoded)
    except Exception:
        return sanitize_text(str(header_val))

def get_mock_college_emails() -> List[Dict[str, Any]]:
    """
    Returns a realistic batch of college emails with timestamps for testing.
    """
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    return [
        {
            "id": "msg_001",
            "sender": "admissions.helpdesk@gmail.com",
            "sender_name": "Rohan Deshmukh (Applicant)",
            "subject": "Inquiry regarding B.Tech Computer Science Quota Admission & Eligibility",
            "body": "Respected Dean Sir, I have scored 96.4 percentile in JEE Mains 2026. Could you please clarify if management quota forms are open for the 2026-27 session, what the fee structure is, and the last date for registration?",
            "timestamp": f"{today_prefix}T08:15:00"
        },
        {
            "id": "msg_002",
            "sender": "finance.accounts@college.edu",
            "sender_name": "Accounts Department",
            "subject": "Approval needed: Chemistry Lab Equipment Vendor Invoice #INV-8821",
            "body": "Dean Sir, attached is the revised invoice of Rs 4,80,000 for glassware and spectrophotometer supplies delivered by Borosil Instruments. The audit team has cleared the bill; awaiting your final sign-off to release payment before Friday.",
            "timestamp": f"{today_prefix}T09:30:00"
        },
        {
            "id": "msg_003",
            "sender": "registrar@university-board.ac.in",
            "sender_name": "State University Registrar",
            "subject": "URGENT: Mandatory Accreditation Audit Committee Visit scheduled for Friday",
            "body": "Strictly Confidential: All affiliated college Deans and Principals must submit their SSR and faculty compliance documentation by Thursday 5:00 PM ahead of the NAAC peer team inspection scheduled for Friday morning.",
            "timestamp": f"{today_prefix}T10:05:00"
        },
        {
            "id": "msg_004",
            "sender": "shreya.patel@student.college.edu",
            "sender_name": "Shreya Patel (Final Year CS)",
            "subject": "Application for Merit-cum-Means Post-Matric Scholarship Endorsement",
            "body": "Respected Sir, I have submitted the state scholarship portal application for the academic year. The portal closes on 15th September and requires the Dean's digital signature on the income verification document.",
            "timestamp": f"{today_prefix}T11:45:00"
        },
        {
            "id": "msg_005",
            "sender": "hod.mechanical@college.edu",
            "sender_name": "Dr. A. K. Verma (HOD Mech)",
            "subject": "Faculty Leave Application & Guest Lecture arrangement for next week",
            "body": "Respected Dean, requesting 3 days of duty leave from 15th to 17th Sept to present a peer-reviewed paper at the International Robotics Symposium in Bangalore. Alternate faculty arrangements for B.Tech lectures have been scheduled.",
            "timestamp": f"{today_prefix}T13:20:00"
        },
        {
            "id": "msg_006",
            "sender": "statecounselling2026@dte.gov.in",
            "sender_name": "State Counselling Board (DTE)",
            "subject": "Round 2 Seat Allotment Matrix & Vacancy Verification for Engineering",
            "body": "Please find attached the provisional vacancy and seat matrix for Round 2 central engineering counselling. Institutional verification and sign-off on vacant branch seats must be completed on the DTE portal by 6:00 PM today.",
            "timestamp": f"{today_prefix}T14:50:00"
        }
    ]

def fetch_live_emails(lookback_hours: int = 24, target_date: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """
    Connects to mailbox via IMAP and fetches emails.
    If start_date and end_date are provided (YYYY-MM-DD), fetches emails received in that date range.
    If target_date is provided (YYYY-MM-DD), fetches emails received on that specific date.
    Extracts clean readable text (even from complex HTML emails).
    """
    host = os.getenv("EMAIL_HOST", "imap.gmail.com")
    port = int(os.getenv("EMAIL_PORT", "993"))
    user = (os.getenv("EMAIL_USER") or "").strip()
    password = (os.getenv("EMAIL_PASSWORD") or "").replace(" ", "").strip("'\"")

    if not user or not password or user == "dean.office@college.edu":
        print("⚠️ No valid live email credentials found in .env. Falling back to mock dataset.")
        return get_mock_college_emails()

    emails = []
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select("inbox")

        now = datetime.now()
        is_rolling_window = False
        cutoff_dt = now - timedelta(hours=lookback_hours)

        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            since_str = start_dt.strftime("%d-%b-%Y")
            before_str = end_dt.strftime("%d-%b-%Y")
            print(f"📅 Searching mailbox for date range: {start_date} to {end_date} ({since_str} to {before_str})...")
            status, messages = mail.search(None, "SINCE", since_str, "BEFORE", before_str)
        elif target_date:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            next_day_dt = target_dt + timedelta(days=1)
            since_str = target_dt.strftime("%d-%b-%Y")
            before_str = next_day_dt.strftime("%d-%b-%Y")
            print(f"📅 Searching mailbox specifically for date: {target_date} ({since_str})...")
            status, messages = mail.search(None, "SINCE", since_str, "BEFORE", before_str)
        else:
            # Rolling 24-hour window: search from yesterday's date, then filter precisely by timestamp
            is_rolling_window = True
            env_hours = os.getenv("EMAIL_LOOKBACK_HOURS")
            actual_lookback = int(env_hours) if env_hours and env_hours.isdigit() else (lookback_hours or 24)
            cutoff_dt = now - timedelta(hours=actual_lookback)
            since_str = cutoff_dt.strftime("%d-%b-%Y")
            print(f"📅 Searching mailbox for rolling {actual_lookback}-hour window (since {cutoff_dt.strftime('%d-%b-%Y %I:%M %p')})...")
            status, messages = mail.search(None, "SINCE", since_str)

        msg_ids = messages[0].split() if (status == "OK" and messages and messages[0]) else []

        if not msg_ids:
            if start_date and end_date:
                print(f"📬 No emails found in range {start_date} to {end_date}.")
            elif target_date:
                print(f"📬 No emails found matching date {target_date}.")
            else:
                print(f"📬 No emails found in mailbox since {cutoff_dt.strftime('%d-%b-%Y %I:%M %p')}.")
            mail.logout()
            return []
        else:
            print(f"📥 Found {len(msg_ids)} email candidate(s). Parsing and verifying 24-hour timestamps...")
            msg_ids = msg_ids[-75:]  # Process up to 75 latest emails

        for msg_id in msg_ids:
            res, data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Date / Timestamp
            date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            if date_tuple:
                local_dt = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                timestamp_str = local_dt.isoformat()
            else:
                local_dt = now
                timestamp_str = now.isoformat()

            # Strict 24-hour rolling cutoff check
            if is_rolling_window and local_dt < cutoff_dt:
                continue

            subject = decode_full_header(msg.get("Subject", "No Subject"))
            sender = decode_full_header(msg.get("From", "Unknown Sender"))

            # Clean Sender Name
            sender_name = sender.split("<")[0].strip('" ')
            if not sender_name or "@" in sender_name:
                sender_name = sender

            # Clean, readable body extraction (handles HTML, scripts, CSS, multipart)
            body = extract_email_body(msg)

            emails.append({
                "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                "sender": sender,
                "sender_name": sender_name,
                "subject": subject,
                "body": body[:2500],  # Full rich text for accurate AI analysis
                "timestamp": timestamp_str
            })

        print(f"-> Verified {len(emails)} email(s) strictly within the target window.")

        mail.logout()
        return emails
    except Exception as e:
        print(f"❌ Error connecting to IMAP: {e}")
        return []
