import os
import sys
import re
import html
import unicodedata
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Register Arial if available on Windows for enhanced unicode character coverage
DEFAULT_FONT = "Helvetica"
DEFAULT_FONT_BOLD = "Helvetica-Bold"
DEFAULT_FONT_ITALIC = "Helvetica-Oblique"

if os.name == "nt":
    arial_path = "C:/Windows/Fonts/arial.ttf"
    arial_bd_path = "C:/Windows/Fonts/arialbd.ttf"
    arial_i_path = "C:/Windows/Fonts/ariali.ttf"
    if os.path.exists(arial_path) and os.path.exists(arial_bd_path):
        try:
            pdfmetrics.registerFont(TTFont("Arial", arial_path))
            pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bd_path))
            if os.path.exists(arial_i_path):
                pdfmetrics.registerFont(TTFont("Arial-Italic", arial_i_path))
            DEFAULT_FONT = "Arial"
            DEFAULT_FONT_BOLD = "Arial-Bold"
            DEFAULT_FONT_ITALIC = "Arial-Italic" if os.path.exists(arial_i_path) else "Arial"
        except Exception:
            pass

def clean_pdf_text(text: str) -> str:
    """
    Cleans and prepares text for safe rendering in ReportLab Paragraphs:
    - Strips zero-width, invisible, and format control unicode characters.
    - Strips emojis and pictographic symbols (which render as black boxes).
    - Normalizes punctuation and replaces typographics (smart quotes, em-dashes).
    - XML-escapes special characters (&, <, >).
    """
    if not text:
        return ""
    
    # 1. Unescape existing HTML entities
    text = html.unescape(str(text))
    
    # 2. Strip invisible/zero-width characters & BOM
    text = re.sub(r'[\u200B-\u200F\uFEFF\u034F\u00AD\u2060\u180E\uFFF9-\uFFFB\u2028\u2029]', '', text)
    
    # 3. Strip URLs and raw tracking tokens/parameters
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\b(?:qs=)?[A-Za-z0-9_\-=+]{25,}\b', '', text)

    # 4. Replace typographic symbols with standard ASCII equivalents
    replacements = {
        '—': '-',
        '–': '-',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '…': '...',
        '•': '-',
        '™': '(TM)',
        '®': '(R)',
        '©': '(C)',
        '\u00a0': ' ',
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)

    # 5. Remove emojis and miscellaneous symbols (Unicode blocks: Emoticons, Symbols, Pictographs, etc.)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[\u2600-\u27bf]', '', text)
    
    # 6. Remove long divider repeats like --------, =======, etc.
    text = re.sub(r'[-_=~*.]{4,}', ' ', text)
    
    # 7. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 8. XML-escape special characters (&, <, >)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    return text

def format_time_stamp(iso_or_str: str) -> str:
    if not iso_or_str:
        return "[--:--]"
    try:
        dt = datetime.fromisoformat(iso_or_str.replace("Z", "+00:00"))
        return dt.strftime("[%I:%M %p]")
    except Exception:
        return f"[{iso_or_str[:8]}]"

def generate_digest_pdf(
    emails: List[Dict[str, Any]],
    news: Dict[str, List[Dict[str, str]]],
    output_path: str = None,
    digest_date_str: str = None,
    file_date_str: str = None,
    pa_agenda: Dict[str, Any] = None
) -> str:
    """
    Generates an executive briefing PDF report containing:
    1. Today's Executive Schedule & Appointments (From PA)
    2. Daily categorized email summaries with arrival timestamps
    3. Important Tech & AI News Headlines
    4. Important Higher Education & University News Headlines
    """
    date_tag = file_date_str or datetime.now().strftime("%Y-%m-%d")
    if not digest_date_str:
        digest_date_str = datetime.now().strftime("%A, %B %d, %Y")

    if not output_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"Daily_Executive_Digest_{date_tag}.pdf")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles using registered safe font
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    
    sub_header_style = ParagraphStyle(
        'DocSubHeader',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=8,
        spaceAfter=4
    )

    category_heading_style = ParagraphStyle(
        'CategoryHeading',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563EB')
    )
    category_header_style = category_heading_style

    item_title_style = ParagraphStyle(
        'ItemTitle',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    item_body_style = ParagraphStyle(
        'ItemBody',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#DC2626')
    )

    story = []

    # 1. Header Banner (Clean Typography without emojis)
    story.append(Paragraph("EXECUTIVE BRIEFING &amp; EMAIL DIGEST", header_style))
    story.append(Spacer(1, 4))
    
    pa_meetings_count = len(pa_agenda.get("meetings", [])) if pa_agenda else 0
    meta_text = (
        f"<b>Date:</b> {clean_pdf_text(digest_date_str)}  |  "
        f"<b>Scheduled Meetings:</b> {pa_meetings_count}  |  "
        f"<b>Inbound Emails:</b> {len(emails)}  |  "
        f"<b>AI Status:</b> Active Intelligence Report"
    )
    story.append(Paragraph(meta_text, sub_header_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceBefore=2, spaceAfter=10))

    # Section 1: Executive Schedule & Appointments (From PA)
    if pa_agenda and (pa_agenda.get("meetings") or pa_agenda.get("reminders")):
        story.append(Paragraph("EXECUTIVE SCHEDULE &amp; APPOINTMENTS (FROM PA)", section_title_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

        meetings = pa_agenda.get("meetings", [])
        if meetings:
            table_data = [
                [
                    Paragraph("<b>TIME</b>", ParagraphStyle('TH1', parent=item_title_style, textColor=colors.white, fontSize=8)),
                    Paragraph("<b>MEETING &amp; AGENDA</b>", ParagraphStyle('TH2', parent=item_title_style, textColor=colors.white, fontSize=8)),
                    Paragraph("<b>KEY ATTENDEES &amp; PREP NOTES</b>", ParagraphStyle('TH3', parent=item_title_style, textColor=colors.white, fontSize=8))
                ]
            ]
            for m in meetings:
                from pa_manager import format_time_to_12h
                t_str = clean_pdf_text(format_time_to_12h(m.get("time", "TBD")))
                title_str = clean_pdf_text(m.get("title", "Meeting"))
                att_str = clean_pdf_text(m.get("attendees", ""))
                notes_str = clean_pdf_text(m.get("notes", ""))
                
                details = f"<b>{att_str}</b>" if att_str else ""
                if notes_str:
                    details += f"<br/><i>Note: {notes_str}</i>" if details else f"<i>Note: {notes_str}</i>"

                table_data.append([
                    Paragraph(f"<b>{t_str}</b>", item_body_style),
                    Paragraph(f"<b>{title_str}</b>", item_title_style),
                    Paragraph(details or "-", item_body_style)
                ])

            t = Table(table_data, colWidths=[1.3 * inch, 3.2 * inch, 3.0 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))

        reminders = pa_agenda.get("reminders", [])
        if reminders:
            rem_html = "<b>Executive Priority Reminders &amp; Deadlines:</b><br/>" + "<br/>".join([f"• {clean_pdf_text(r)}" for r in reminders])
            rem_table = Table([[Paragraph(rem_html, item_body_style)]], colWidths=[7.5 * inch])
            rem_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF3C7')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F59E0B')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(rem_table)

        story.append(Spacer(1, 10))

    # 2. Section: Inbound Email Highlights
    story.append(Paragraph("INBOUND EMAIL ACTION SUMMARIES", section_title_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

    if not emails:
        story.append(Paragraph("<i>No unread inbound emails for the current reporting window.</i>", item_body_style))
        story.append(Spacer(1, 10))
    else:
        # Group emails by category
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for em in emails:
            cat = em.get("category", "General")
            grouped.setdefault(cat, []).append(em)

        for cat_name, items in grouped.items():
            is_urgent = cat_name.lower() in ["urgent", "action required"]
            cat_color = colors.HexColor('#DC2626') if is_urgent else colors.HexColor('#1D4ED8')
            
            clean_cat = clean_pdf_text(cat_name).upper()
            cat_header = Paragraph(f"<b>{clean_cat} ({len(items)})</b>", ParagraphStyle('CatStyle', parent=category_header_style, textColor=cat_color))
            story.append(cat_header)
            story.append(Spacer(1, 4))

            table_data = []
            for item in items:
                time_str = clean_pdf_text(format_time_stamp(item.get("timestamp", "")))
                sender_name = clean_pdf_text(item.get("sender_name") or item.get("sender") or "Unknown")
                summary = clean_pdf_text(item.get("summary") or item.get("subject") or "No description.")
                gmail_link = item.get("gmail_link", "")

                link_html = f"&nbsp;&nbsp;<a href='{gmail_link}'><font color='#2563EB'><u><b>[Open in Gmail ↗]</b></u></font></a>" if gmail_link else ""
                content = [
                    Paragraph(f"<b>{time_str} {sender_name}:</b> {summary}{link_html}", item_body_style)
                ]
                table_data.append([content])

            t = Table(table_data, colWidths=[7.2 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#EDF2F7')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 10))

    # Helper function to create news table
    def build_news_table(items, bg_color='#EFF6FF', border_color='#BFDBFE', grid_color='#DBEAFE'):
        table_rows = []
        for n in items:
            title = clean_pdf_text(n.get("title", ""))
            summary = clean_pdf_text(n.get("summary", ""))
            source = clean_pdf_text(n.get("source", "News Desk"))
            time_tag = clean_pdf_text(n.get("pub_date", "Today"))
            news_url = n.get("link", "")
            
            link_html = f"&nbsp;|&nbsp;<a href='{news_url}'><font color='#2563EB'><u><b>Read Article ↗</b></u></font></a>" if news_url else ""
            cell_content = [
                Paragraph(f"<b>{title}</b>", item_title_style)
            ]
            if summary:
                cell_content.append(Paragraph(f"<font color='#1E293B' size='8.5'>{summary}</font>", item_body_style))
            cell_content.append(Paragraph(f"<font color='#64748B' size='7.5'>Source: {source}  |  {time_tag}{link_html}</font>", item_body_style))
            table_rows.append([cell_content])

        t = Table(table_rows, colWidths=[7.2 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_color)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(border_color)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(grid_color)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    # 3. Section: Tech & AI News
    story.append(Paragraph("TECH &amp; ARTIFICIAL INTELLIGENCE DEVELOPMENTS (1-DAY LOOKBACK)", section_title_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

    tech_items = news.get("tech_ai", [])
    if tech_items:
        story.append(build_news_table(tech_items[:5], bg_color='#F0FDF4', border_color='#BBF7D0', grid_color='#DCFCE7'))
    else:
        story.append(Paragraph("<i>No new tech headlines available.</i>", item_body_style))

    story.append(Spacer(1, 12))

    # 4. Section: India Higher Education (Top 10)
    story.append(Paragraph("HIGHER EDUCATION &amp; INSTITUTES (INDIA - TOP 10 | 1-DAY LOOKBACK)", section_title_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

    india_items = news.get("education_india", news.get("education", []))
    if india_items:
        story.append(build_news_table(india_items[:10], bg_color='#EFF6FF', border_color='#BFDBFE', grid_color='#DBEAFE'))
    else:
        story.append(Paragraph("<i>No new national education headlines available.</i>", item_body_style))

    # 5. Section: World Higher Education (Top 5)
    world_items = news.get("education_world", [])
    if world_items:
        story.append(Spacer(1, 12))
        story.append(Paragraph("GLOBAL HIGHER EDUCATION &amp; UNIVERSITIES (WORLD - TOP 5 | 1-DAY LOOKBACK)", section_title_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))
        story.append(build_news_table(world_items[:5], bg_color='#F8FAFC', border_color='#CBD5E1', grid_color='#E2E8F0'))

    # 6. Section: Rajasthan Education Updates
    raj_items = news.get("education_rajasthan", [])
    if raj_items:
        story.append(Spacer(1, 12))
        story.append(Paragraph("RAJASTHAN HIGHER EDUCATION &amp; STATE UPDATES (1-DAY LOOKBACK)", section_title_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))
        story.append(build_news_table(raj_items[:5], bg_color='#FFFBEB', border_color='#FDE68A', grid_color='#FEF3C7'))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceBefore=5, spaceAfter=5))
    story.append(Paragraph("<font color='#94A3B8' size='8'>Generated automatically by Dean Email Automation &amp; Executive Assistant Suite.</font>", ParagraphStyle('Footer', parent=styles['Normal'], alignment=1)))

    doc.build(story)
    print(f"📄 PDF Executive Briefing successfully generated: {output_path}")
    return output_path

if __name__ == "__main__":
    from email_fetcher import get_mock_college_emails
    from news_fetcher import fetch_important_news
    sample_emails = get_mock_college_emails()
    sample_news = fetch_important_news()
    pdf_file = generate_digest_pdf(sample_emails, sample_news)
    print("Test PDF File created at:", pdf_file)
