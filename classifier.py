import os
import re
import json
from typing import Dict, Any

import unicodedata
from email_fetcher import sanitize_text

CATEGORIES = [
    "Admissions",
    "Finance & Accounts",
    "Academics & Exams",
    "Faculty & HR",
    "Student Affairs",
    "Campus Admin",
    "System Alerts & Security",
    "Careers & Internships",
    "Marketing & News",
    "Urgent",
    "General"
]

def rule_based_fallback_classify(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    Intelligent fallback classifier using heuristic keyword patterns.
    Ensures high-quality summaries even when AI quota is temporarily constrained.
    """
    subject_clean = sanitize_text(subject)
    body_clean = sanitize_text(body)
    sender_clean = sanitize_text(sender)

    text = f"{subject_clean} {body_clean} {sender_clean}".lower()

    # 1. Urgent detection
    urgent_keywords = [
        "urgent", "immediate", "emergency", "court notice", "audit deadline", 
        "legal notice", "ragging", "disciplinary", "down", "critical alert", "action required"
    ]
    is_urgent = any(kw in text for kw in urgent_keywords)

    # 2. Category matching
    if is_urgent and any(kw in text for kw in ["court", "ragging", "disciplinary", "emergency"]):
        category = "Urgent"
    elif any(kw in text for kw in ["admission", "seat allotment", "quota", "application form", "counselling", "enrollment", "prospectus"]):
        category = "Admissions"
    elif any(kw in text for kw in ["accreditation", "exam", "examination", "marksheet", "grade", "syllabus", "curriculum", "timetable", "nba", "naac", "ssr", "lecture", "course", "assignment"]):
        category = "Academics & Exams"
    elif any(kw in text for kw in ["fee", "payment", "invoice", "refund", "grant", "budget", "accounts", "salary", "treasurer", "billing", "stock", "portfolio", "crude", "nifty"]):
        category = "Finance & Accounts"
    elif any(kw in text for kw in ["faculty", "leave application", "recruitment", "professor", "phd scholar", "staff", "tenure", "vice-chancellor"]):
        category = "Faculty & HR"
    elif any(kw in text for kw in ["hostel", "mess", "sports", "student union", "cultural", "complaint", "scholarship"]):
        category = "Student Affairs"
    elif any(kw in text for kw in ["down", "monitor is down", "security alert", "unauthorized", "password reset", "verification code", "antivirus", "mcafee", "threat"]):
        category = "System Alerts & Security"
    elif any(kw in text for kw in ["internship", "stipend", "placement", "hiring", "ppo", "job vacancy", "hiring", "resume", "roles"]):
        category = "Careers & Internships"
    elif any(kw in text for kw in ["sale", "discount", "offer", "newsletter", "digest", "tickets", "snapchat", "stories"]):
        category = "Marketing & News"
    elif is_urgent:
        category = "Urgent"
    else:
        category = "General"

    # Intelligent summary generation from body text
    cleaned_body = re.sub(r'^(dear|respected|hello|hi|good morning|to whom it may concern)[^\n,]*[\n,]', '', body_clean, flags=re.IGNORECASE).strip()
    
    summary = ""
    if cleaned_body:
        # Split by periods, question marks, exclamation marks, or newlines
        raw_sentences = [s.strip() for s in re.split(r'[\r\n.!?]+', cleaned_body)]
        # Filter out lines that lack substantive letters (like spacers, codes, or boilerplate)
        meaningful_sentences = [
            s for s in raw_sentences 
            if len(re.findall(r'[a-zA-Z0-9]', s)) >= 15
        ]
        if meaningful_sentences:
            summary = meaningful_sentences[0]
            if len(summary) > 90:
                summary = summary[:87].rsplit(' ', 1)[0] + "..."
            if not summary.endswith("."):
                summary += "."

    # If body lacked substantive text (typical in promotional graphic emails), rely on subject
    if not summary or len(re.findall(r'[a-zA-Z0-9]', summary)) < 15:
        if subject_clean:
            summary = subject_clean if subject_clean.endswith(".") else f"{subject_clean}."
        else:
            summary = f"Update received from {sender_clean or 'sender'}."

    # Final cleanup to eliminate any remaining unwanted formatting
    summary = sanitize_text(summary)

    return {
        "category": category,
        "is_urgent": is_urgent,
        "summary": summary
    }

def classify_email(subject: str, body: str, sender: str, api_key: str = None) -> Dict[str, Any]:
    """
    Classifies an email and extracts an insightful 1-to-2 sentence executive summary.
    Uses Google Gemini with model cascading, fallback, and clear prompt instructions.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    subject_clean = sanitize_text(subject)
    body_clean = sanitize_text(body)
    sender_clean = sanitize_text(sender)

    api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        return rule_based_fallback_classify(subject_clean, body_clean, sender_clean)

    try:
        import requests

        prompt = f"""
You are an executive email assistant for busy leadership.
Analyze the email below and generate a brief, direct, to-the-point summary.
CRITICAL: Do NOT overexplain, elaborate, or write long paragraphs. Keep it strictly to 1 concise sentence (under 15 words).

SENDER: {sender_clean}
SUBJECT: {subject_clean}
EMAIL BODY CONTENT:
{body_clean[:2000]}

EXECUTIVE RULES:
1. MAXIMUM 1 short sentence (under 15 words).
2. DO NOT overexplain, transcribe background details, or list multiple offers/items.
3. State ONLY the single key takeaway or action required.
4. Examples of good concise summaries:
   - "Approval requested for Chemistry Lab invoice of Rs 4.8L."
   - "Registrations open for Agentic AI Hackathon (Rs 5.5L prize pool)."
   - "Student promotional discounts on laptops and smartphones."
   - "Server maintenance scheduled for Saturday midnight."
   - "Seat vacancy matrix released for Round 2 counselling."
5. Plain text only, no emojis or special markdown.

Return ONLY a valid JSON object:
{{
  "category": "Admissions | Finance & Accounts | Academics & Exams | Faculty & HR | Student Affairs | System Alerts | Careers & Internships | Marketing & News | Urgent | General",
  "is_urgent": true or false,
  "summary": "1 brief sentence under 15 words getting straight to the point."
}}
"""
        candidate_models = [
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash"
        ]
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        for model_name in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    result = response.json()
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(raw_text)
                    summary = sanitize_text(data.get("summary", ""))
                    if summary and len(re.findall(r'[a-zA-Z0-9]', summary)) > 10:
                        return {
                            "category": data.get("category", "General").strip(),
                            "is_urgent": bool(data.get("is_urgent", False)),
                            "summary": summary
                        }
            except Exception:
                continue

        return rule_based_fallback_classify(subject_clean, body_clean, sender_clean)
    except Exception:
        return rule_based_fallback_classify(subject_clean, body_clean, sender_clean)

if __name__ == "__main__":
    # Test on sample realistic emails
    from email_fetcher import get_mock_college_emails
    sample_emails = get_mock_college_emails()
    print("Testing improved email summarization on mock emails:\n")
    for em in sample_emails:
        res = classify_email(em["subject"], em["body"], em["sender"])
        print(f"[{res['category']}] (Urgent: {res['is_urgent']})")
        print(f"From: {em['sender_name']}")
        print(f"Summary: {res['summary']}")
        print("-" * 60)
