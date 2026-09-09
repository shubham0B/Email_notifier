import os
import sys
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    digest_date_str: str = None
) -> str:
    """
    Generates an executive briefing PDF report containing:
    1. Daily categorized email summaries with arrival timestamps
    2. Important Tech & AI News Headlines
    3. Important Higher Education & University News Headlines
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    if not digest_date_str:
        digest_date_str = datetime.now().strftime("%A, %B %d, %Y")

    if not output_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"Daily_Executive_Digest_{today_str}.pdf")
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

    # Custom styles
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B')
    )
    
    sub_header_style = ParagraphStyle(
        'DocSubHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=6
    )

    category_header_style = ParagraphStyle(
        'CategoryHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563EB')
    )

    item_title_style = ParagraphStyle(
        'ItemTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    item_body_style = ParagraphStyle(
        'ItemBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#DC2626')
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("🏛️ EXECUTIVE BRIEFING & EMAIL DIGEST", header_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"📅 <b>Date:</b> {digest_date_str}  |  📬 <b>Inbound Emails:</b> {len(emails)}  |  🤖 <b>AI Analysis Active</b>", sub_header_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceBefore=2, spaceAfter=10))

    # 2. Section: Inbound Email Highlights
    story.append(Paragraph("📬 INBOUND EMAIL ACTION SUMMARIES", section_title_style))
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
            
            cat_header = Paragraph(f"<b>{cat_name.upper()} ({len(items)})</b>", ParagraphStyle('CatStyle', parent=category_header_style, textColor=cat_color))
            story.append(cat_header)
            story.append(Spacer(1, 4))

            table_data = []
            for item in items:
                time_str = format_time_stamp(item.get("timestamp", ""))
                sender_name = item.get("sender_name") or item.get("sender") or "Unknown"
                summary = item.get("summary") or item.get("subject") or "No description."

                content = [
                    Paragraph(f"<b>{time_str} {sender_name}:</b> {summary}", item_body_style)
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
            title = n.get("title", "")
            summary = n.get("summary", "")
            source = n.get("source", "News Desk")
            time_tag = n.get("pub_date", "Today")
            cell_content = [
                Paragraph(f"• <b>{title}</b>", item_title_style)
            ]
            if summary:
                cell_content.append(Paragraph(f"<font color='#1E293B' size='8.5'>{summary}</font>", item_body_style))
            cell_content.append(Paragraph(f"<font color='#64748B' size='7.5'>Source: {source}  |  {time_tag}</font>", item_body_style))
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
    story.append(Paragraph("🤖 TECH & ARTIFICIAL INTELLIGENCE DEVELOPMENTS (1-DAY PREVIOUS LOOKBACK)", section_title_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

    tech_items = news.get("tech_ai", [])
    if tech_items:
        story.append(build_news_table(tech_items[:5], bg_color='#F0FDF4', border_color='#BBF7D0', grid_color='#DCFCE7'))
    else:
        story.append(Paragraph("<i>No new tech headlines available.</i>", item_body_style))

    story.append(Spacer(1, 12))

    # 4. Section: India Higher Education (Top 10)
    story.append(Paragraph("🇮🇳 HIGHER EDUCATION & INSTITUTES (INDIA - TOP 10 | 1-DAY PREVIOUS)", section_title_style))
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
        story.append(Paragraph("🌍 GLOBAL HIGHER EDUCATION & UNIVERSITIES (WORLD - TOP 5 | 1-DAY PREVIOUS)", section_title_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))
        story.append(build_news_table(world_items[:5], bg_color='#F8FAFC', border_color='#CBD5E1', grid_color='#E2E8F0'))

    # 6. Section: Rajasthan Education Updates
    raj_items = news.get("education_rajasthan", [])
    if raj_items:
        story.append(Spacer(1, 12))
        story.append(Paragraph("🏰 RAJASTHAN HIGHER EDUCATION & STATE UPDATES (1-DAY PREVIOUS)", section_title_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))
        story.append(build_news_table(raj_items[:5], bg_color='#FFFBEB', border_color='#FDE68A', grid_color='#FEF3C7'))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceBefore=5, spaceAfter=5))
    story.append(Paragraph("<font color='#94A3B8' size='8'>Generated automatically by Dean Email Automation & Executive Assistant Suite.</font>", ParagraphStyle('Footer', parent=styles['Normal'], alignment=1)))

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
