from datetime import datetime
from typing import List, Dict, Any

def get_category_icon(category_name: str) -> str:
    """Returns a context-appropriate emoji for any category name."""
    name = category_name.lower()
    if any(k in name for k in ["urgent", "action", "emergency"]):
        return "🚨"
    if any(k in name for k in ["career", "job", "intern", "hiring"]):
        return "💼"
    if any(k in name for k in ["course", "learn", "study", "academic", "exam", "nptel", "education"]):
        return "📚"
    if any(k in name for k in ["admission", "enroll", "seat"]):
        return "🎓"
    if any(k in name for k in ["finance", "bill", "payment", "bank", "fee", "money", "salary"]):
        return "💳"
    if any(k in name for k in ["security", "alert", "protect", "warning", "login"]):
        return "🔒"
    if any(k in name for k in ["social", "network", "chat", "linkedin", "snapchat"]):
        return "💬"
    if any(k in name for k in ["shop", "offer", "deal", "discount", "order", "flipkart"]):
        return "🛍️"
    if any(k in name for k in ["faculty", "hr", "staff", "professor"]):
        return "👥"
    if any(k in name for k in ["student", "campus", "hostel"]):
        return "🏛️"
    return "📁"

def format_time_stamp(iso_or_datetime_str: str) -> str:
    """Format an ISO timestamp or date string into clean 12-hour format e.g. [09:42 AM]"""
    if not iso_or_datetime_str:
        return "[--:--]"
    try:
        dt = datetime.fromisoformat(iso_or_datetime_str.replace("Z", "+00:00"))
        return dt.strftime("[%I:%M %p]")
    except Exception:
        return f"[{iso_or_datetime_str[:8]}]"

def build_whatsapp_digest(
    emails: List[Dict[str, Any]], 
    college_name: str = "Executive Inbox Monitor",
    digest_date_str: str = None
) -> str:
    """
    Constructs a clean, emoji-rich WhatsApp digest message from classified emails.
    Dynamically groups by any category returned by the AI based on real email context.
    """
    if not digest_date_str:
        digest_date_str = datetime.now().strftime("%A, %b %d, %Y")

    if not emails:
        return (
            f"📬 *Daily Email Digest*\n"
            f"📅 _{digest_date_str}_\n\n"
            f"✅ *All Clear:* No new unread emails received in the last monitoring period."
        )

    # Group emails dynamically by category
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    urgent_items: List[Dict[str, Any]] = []

    for email in emails:
        cat = email.get("category", "General").strip()
        if not cat:
            cat = "General"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(email)

        if email.get("is_urgent", False) or cat.lower() in ["urgent", "critical"]:
            urgent_items.append(email)

    total_emails = len(emails)
    
    # Message Header
    lines = [
        f"📬 *SMART EMAIL DIGEST*",
        f"📍 _{college_name}_",
        f"📅 *Date:* {digest_date_str}",
        f"📨 *Total Inbound:* {total_emails} emails",
        "─" * 22
    ]

    # Category overview breakdown summary (sorted by count)
    sorted_categories = sorted(grouped.keys(), key=lambda k: len(grouped[k]), reverse=True)
    lines.append("*📊 Category Breakdown:*")
    for cat in sorted_categories:
        icon = get_category_icon(cat)
        count = len(grouped[cat])
        lines.append(f"  {icon} *{cat}:* {count} email{'s' if count != 1 else ''}")
    
    lines.append("─" * 22)

    # Urgent Section (if any)
    if urgent_items:
        lines.append("🚨 *ACTION REQUIRED / URGENT:*")
        for item in urgent_items:
            time_str = format_time_stamp(item.get("timestamp", ""))
            sender = item.get("sender_name") or item.get("sender", "Unknown")
            summary = item.get("summary", "No summary provided")
            lines.append(f"• *{time_str}* *{sender}*: {summary}")
        lines.append("─" * 22)

    # Detailed Highlights grouped under their natural categories
    lines.append("*📋 Detailed Highlights:*")
    for cat in sorted_categories:
        items = grouped[cat]
        icon = get_category_icon(cat)
        lines.append(f"\n{icon} *{cat.upper()} ({len(items)})*")
        for item in items:
            time_str = format_time_stamp(item.get("timestamp", ""))
            sender = item.get("sender_name") or item.get("sender", "Unknown")
            summary = item.get("summary", "No summary provided")
            lines.append(f"• *{time_str}* _{sender}_: {summary}")

    lines.append("\n" + "─" * 22)
    lines.append("📌 _Auto-categorized by AI based on email context._")

    return "\n".join(lines)
