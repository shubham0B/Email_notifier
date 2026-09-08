import os
import sys
import email
from email.header import decode_header
import imaplib
from datetime import datetime, timedelta
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
            "body": "Respected Dean Sir, I have scored 96.4 percentile in JEE. Could you please clarify if management quota forms are open for the 2026-27 session?",
            "timestamp": f"{today_prefix}T08:15:00"
        },
        {
            "id": "msg_002",
            "sender": "finance.accounts@college.edu",
            "sender_name": "Accounts Department",
            "subject": "Approval needed: Chemistry Lab Equipment Vendor Invoice #INV-8821",
            "body": "Dean Sir, attached is the revised invoice of Rs 4,80,000 for glassware and spectrophotometer supplies. Awaiting your sign-off for payment release.",
            "timestamp": f"{today_prefix}T09:30:00"
        },
        {
            "id": "msg_003",
            "sender": "registrar@university-board.ac.in",
            "sender_name": "State University Registrar",
            "subject": "URGENT: Mandatory Accreditation Audit Committee Visit scheduled for Friday",
            "body": "Strictly Confidential: All college Deans must submit their SSR and faculty compliance reports by Thursday 5:00 PM ahead of Friday's inspection.",
            "timestamp": f"{today_prefix}T10:05:00"
        },
        {
            "id": "msg_004",
            "sender": "shreya.patel@student.college.edu",
            "sender_name": "Shreya Patel (Final Year CS)",
            "subject": "Application for Merit-cum-Means Post-Matric Scholarship Endorsement",
            "body": "Sir, I have submitted the state scholarship portal application. Need the Dean's digital signature on the income certificate verification.",
            "timestamp": f"{today_prefix}T11:45:00"
        },
        {
            "id": "msg_005",
            "sender": "hod.mechanical@college.edu",
            "sender_name": "Dr. A. K. Verma (HOD Mech)",
            "subject": "Faculty Leave Application & Guest Lecture arrangement for next week",
            "body": "Respected Dean, requesting 3 days of duty leave from 15th Sept to attend the International Robotics Symposium. Alternate classes arranged.",
            "timestamp": f"{today_prefix}T13:20:00"
        },
        {
            "id": "msg_006",
            "sender": "statecounselling2026@dte.gov.in",
            "sender_name": "State Counselling Board (DTE)",
            "subject": "Round 2 Seat Allotment Matrix & Vacancy Verification for Engineering",
            "body": "Please find attached the provisional vacancy list for Round 2 engineering admissions. Please confirm institutional seat counts.",
            "timestamp": f"{today_prefix}T14:50:00"
        }
    ]

def fetch_live_emails(lookback_hours: int = 24, target_date: str = None) -> List[Dict[str, Any]]:
    """
    Connects to mailbox via IMAP and fetches emails.
    If target_date is provided (YYYY-MM-DD), fetches emails received on that specific date.
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

        if target_date:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            next_day_dt = target_dt + timedelta(days=1)
            since_str = target_dt.strftime("%d-%b-%Y")
            before_str = next_day_dt.strftime("%d-%b-%Y")
            print(f"📅 Searching mailbox specifically for date: {target_date} ({since_str})...")
            status, messages = mail.search(None, "SINCE", since_str, "BEFORE", before_str)
        else:
            # Search for unread messages first
            status, messages = mail.search(None, "UNSEEN")

        msg_ids = messages[0].split() if (status == "OK" and messages and messages[0]) else []

        if not msg_ids:
            if target_date:
                print(f"📬 No emails found matching date {target_date}.")
                mail.logout()
                return []
            else:
                print("📬 No unread emails found in inbox. Fetching latest 10 recent emails for demonstration...")
                status, messages = mail.search(None, "ALL")
                if status == "OK" and messages and messages[0]:
                    msg_ids = messages[0].split()[-10:]
                else:
                    print("📬 Mailbox is completely empty.")
                    mail.logout()
                    return []
        else:
            print(f"📥 Found {len(msg_ids)} email(s) for target window. Parsing...")
            msg_ids = msg_ids[-30:] # Process up to 30 emails

        for msg_id in msg_ids[-30:]: # Process up to last 30 unread
            res, data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode Subject
            subject, encoding = decode_header(msg.get("Subject", "No Subject"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            # Decode From
            raw_from = msg.get("From", "Unknown Sender")
            from_parts = decode_header(raw_from)
            decoded_from = ""
            for part, enc in from_parts:
                if isinstance(part, bytes):
                    decoded_from += part.decode(enc or "utf-8", errors="ignore")
                else:
                    decoded_from += str(part)
            sender = decoded_from

            # Date / Timestamp
            date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            if date_tuple:
                local_dt = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                timestamp_str = local_dt.isoformat()
            else:
                timestamp_str = datetime.now().isoformat()

            # Body parsing
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")

            emails.append({
                "id": msg_id.decode(),
                "sender": sender,
                "sender_name": sender.split("<")[0].strip('" '),
                "subject": subject,
                "body": body[:1000],
                "timestamp": timestamp_str
            })

        mail.logout()
        return emails
    except Exception as e:
        print(f"❌ Error connecting to IMAP: {e}")
        return []
