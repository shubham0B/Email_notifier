import os
import re
import json
from typing import Dict, Any

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
    text = f"{subject} {body} {sender}".lower()

    # 1. Urgent detection
    urgent_keywords = [
        "urgent", "immediate", "emergency", "court notice", "audit deadline", 
        "legal notice", "ragging", "disciplinary", "down", "critical alert"
    ]
    is_urgent = any(kw in text for kw in urgent_keywords)

    # 2. Category matching
    if is_urgent and any(kw in text for kw in ["court", "ragging", "disciplinary", "emergency"]):
        category = "Urgent"
    elif any(kw in text for kw in ["admission", "seat allotment", "quota", "application form", "counselling", "enrollment", "prospectus"]):
        category = "Admissions"
    elif any(kw in text for kw in ["accreditation", "exam", "examination", "marksheet", "grade", "syllabus", "curriculum", "timetable", "nba", "naac", "ssr"]):
        category = "Academics & Exams"
    elif any(kw in text for kw in ["fee", "payment", "invoice", "refund", "grant", "budget", "accounts", "salary", "treasurer", "billing"]):
        category = "Finance & Accounts"
    elif any(kw in text for kw in ["faculty", "leave application", "recruitment", "professor", "phd scholar", "staff", "tenure", "vice-chancellor"]):
        category = "Faculty & HR"
    elif any(kw in text for kw in ["hostel", "mess", "sports", "student union", "cultural", "complaint", "scholarship"]):
        category = "Student Affairs"
    elif any(kw in text for kw in ["down", "monitor is down", "security alert", "unauthorized", "password reset", "verification code"]):
        category = "System Alerts & Security"
    elif any(kw in text for kw in ["internship", "stipend", "placement", "hiring", "ppo", "job vacancy"]):
        category = "Careers & Internships"
    elif any(kw in text for kw in ["sale", "discount", "offer", "newsletter", "digest", "tickets"]):
        category = "Marketing & News"
    elif is_urgent:
        category = "Urgent"
    else:
        category = "General"

    # Intelligent summary generation from body text
    cleaned_body = body.strip()
    # Strip common salutations
    cleaned_body = re.sub(r'^(dear|respected|hello|hi|good morning|to whom it may concern)[^\n,]*[\n,]', '', cleaned_body, flags=re.IGNORECASE).strip()
    
    summary = ""
    if cleaned_body:
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', cleaned_body) if len(s.strip()) > 15]
        if sentences:
            summary = sentences[0]
            if len(sentences) > 1 and len(summary) < 70:
                summary += f". {sentences[1]}"
            if not summary.endswith("."):
                summary += "."

    if not summary or len(summary) < 20:
        clean_subj = subject.strip()
        summary = f"Notice regarding: {clean_subj}." if clean_subj else "Routine communication received."

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

    api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        return rule_based_fallback_classify(subject, body, sender)

    try:
        import requests

        prompt = f"""
You are an expert executive email assistant for institutional leadership and busy professionals.
Analyze the email below and generate a high-quality, actionable, 1-to-2 sentence summary.

SENDER: {sender}
SUBJECT: {subject}
EMAIL BODY CONTENT:
{body[:2500]}

EXECUTIVE SUMMARIZATION RULES:
1. Identify the core message: What does the sender want, what happened, or what is being announced?
2. Mention critical specifics: Include amounts (₹/$/€), deadlines, dates, key names, or system status if present.
3. DO NOT simply repeat or paraphrase the subject line.
4. If it is an action item (e.g., approval, invoice, signature, compliance, deadline), state what action is required from the recipient.
5. If it is a system alert or downtime notification, specify what service is affected and current status.
6. If it is a career/internship opportunity, specify the role, stipend/prize, and company.
7. If it is a promotional offer/newsletter, state the specific product or offer clearly.

Return ONLY a valid JSON object:
{{
  "category": "Crisp category (e.g. Admissions, Finance & Accounts, Academics & Exams, Faculty & HR, Student Affairs, System Alerts, Careers & Internships, Marketing & News, or Campus Admin)",
  "is_urgent": true or false,
  "summary": "Concise, informative 1-2 sentence executive summary explaining the actual message, key specifics, and required action."
}}
"""
        candidate_models = [
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), 
            "gemini-3.7-flash", 
            "gemini-3.6-flash"
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
                    summary = data.get("summary", "").strip()
                    if summary and len(summary) > 10:
                        return {
                            "category": data.get("category", "General").strip(),
                            "is_urgent": bool(data.get("is_urgent", False)),
                            "summary": summary
                        }
            except Exception:
                continue

        return rule_based_fallback_classify(subject, body, sender)
    except Exception:
        return rule_based_fallback_classify(subject, body, sender)

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
