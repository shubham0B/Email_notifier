import os
import re
import json
from typing import Dict, Any

CATEGORIES = [
    "Admission",
    "Finance",
    "Academics",
    "Faculty",
    "Student Affairs",
    "Urgent",
    "General"
]

def rule_based_fallback_classify(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    Intelligent fallback classifier using heuristic keyword patterns.
    Ensures the system functions even without an active AI API key.
    """
    text = f"{subject} {body} {sender}".lower()

    # 1. Urgent detection
    urgent_keywords = ["urgent", "immediate", "emergency", "court notice", "audit deadline", "legal notice", "ragging", "disciplinary"]
    is_urgent = any(kw in text for kw in urgent_keywords)

    # 2. Category matching
    if is_urgent and any(kw in text for kw in ["court", "ragging", "disciplinary", "emergency"]):
        category = "Urgent"
    elif any(kw in text for kw in ["admission", "seat allotment", "quota", "application form", "counselling", "enrollment", "prospectus"]):
        category = "Admission"
    elif any(kw in text for kw in ["accreditation", "exam", "examination", "marksheet", "grade", "syllabus", "curriculum", "timetable", "nba", "naac", "ssr"]):
        category = "Academics"
    elif any(kw in text for kw in ["fee", "payment", "invoice", "refund", "grant", "budget", "accounts", "salary", "treasurer"]):
        category = "Finance"
    elif any(kw in text for kw in ["faculty", "leave application", "recruitment", "professor", "phd scholar", "staff", "tenure"]):
        category = "Faculty"
    elif any(kw in text for kw in ["hostel", "mess", "sports", "student union", "cultural", "complaint", "scholarship"]):
        category = "Student Affairs"
    elif is_urgent:
        category = "Urgent"
    else:
        category = "General"

    # Quick 1-sentence summary generation from subject or first sentence
    cleaned_subject = subject.strip()
    if not cleaned_subject:
        first_line = (body.strip().split("\n")[0])[:80]
        summary = first_line if first_line else "No description available."
    else:
        summary = cleaned_subject

    return {
        "category": category,
        "is_urgent": is_urgent,
        "summary": summary
    }

def classify_email(subject: str, body: str, sender: str, api_key: str = None) -> Dict[str, Any]:
    """
    Classifies an email and extracts a 1-sentence summary.
    Uses Google Gemini if GEMINI_API_KEY is available; otherwise uses rule-based fallback.
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        return rule_based_fallback_classify(subject, body, sender)

    try:
        import requests

        prompt = f"""
You are an intelligent executive email assistant.
Analyze this email and classify it based on its actual, real-world context and intent.

Sender: {sender}
Subject: {subject}
Content: {body[:800]}

Categorization Guidelines:
- If this is a college/university email: use relevant categories like "Admissions", "Finance & Accounts", "Academics & Exams", "Faculty & HR", "Student Affairs", or "Campus Admin".
- If this is a personal/professional email: use relevant categories like "Career & Jobs", "Courses & Learning", "Finance & Billing", "Security & System", "Social & Networking", "Shopping & Deals", or "Personal".
- If it requires immediate/critical action, set is_urgent to true.

Return ONLY a valid JSON object:
{{
  "category": "Short 1-3 word category name",
  "is_urgent": true or false,
  "summary": "Crisp 1-sentence executive summary under 15 words"
}}
"""
        model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(raw_text)
            return {
                "category": data.get("category", "General").strip(),
                "is_urgent": bool(data.get("is_urgent", False)),
                "summary": data.get("summary", subject).strip()
            }
        else:
            return rule_based_fallback_classify(subject, body, sender)
    except Exception:
        return rule_based_fallback_classify(subject, body, sender)
