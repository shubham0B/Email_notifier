import os
import sys
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def fetch_rss_candidates(
    query: str, 
    max_items: int = 20, 
    max_lookback_hours: int = 24,
    hl: str = "en-IN", 
    gl: str = "IN", 
    ceid: str = "IN:en"
) -> List[Dict[str, str]]:
    """
    Fetches raw news candidates from Google News RSS feed for a targeted query,
    enforcing a strict recency filter (strictly past 24 hours).
    100% free, requires no API key.
    """
    now = datetime.now()
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    items = []
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item"):
                raw_title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date_raw = item.findtext("pubDate", "")
                source = item.findtext("source", "")

                # Parse and verify recency (1 day previous / <= 48 hours)
                pub_formatted = "Recent"
                if pub_date_raw:
                    try:
                        pub_dt = parsedate_to_datetime(pub_date_raw).replace(tzinfo=None)
                        age_hours = (now - pub_dt).total_seconds() / 3600
                        if age_hours > max_lookback_hours:
                            continue  # Exclude news older than 1-2 days
                        pub_formatted = pub_dt.strftime("%a, %d %b %Y")
                    except Exception:
                        pub_formatted = pub_date_raw[:16]

                cleaned_title = raw_title
                detected_source = source
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    cleaned_title = parts[0].strip()
                    if not detected_source:
                        detected_source = parts[1].strip()

                if cleaned_title:
                    items.append({
                        "title": cleaned_title,
                        "source": detected_source or "News Desk",
                        "pub_date": pub_formatted,
                        "link": link
                    })
                    if len(items) >= max_items:
                        break
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch RSS headlines for '{query}': {e}")

    return items

def deduplicate_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Removes duplicate or near-identical headlines."""
    seen = set()
    result = []
    for it in items:
        norm = "".join(c.lower() for c in it.get("title", "") if c.isalnum())
        if norm and norm not in seen:
            seen.add(norm)
            result.append(it)
    return result

def curate_all_news_with_gemini(
    tech_candidates: List[Dict[str, str]],
    india_candidates: List[Dict[str, str]],
    world_candidates: List[Dict[str, str]],
    rajasthan_candidates: List[Dict[str, str]],
    api_key: str
) -> Dict[str, List[Dict[str, str]]]:
    """
    Uses Google Gemini with multi-model fallback to curate:
    1. Top Tech & AI news (4-5 items)
    2. Top 10 India Education news (strictly 1 day previous / last 24-48h)
    3. Top 5 World Education news (strictly 1 day previous / last 24-48h)
    4. Top Rajasthan Education news (3-5 items, strictly 1 day previous / last 24-48h)
    """
    import requests

    now = datetime.now()
    cutoff_24h = now - timedelta(hours=24)
    target_window_str = f"{cutoff_24h.strftime('%d %b %I:%M %p')} to {now.strftime('%d %b %I:%M %p, %Y')}"

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.6-flash"]

    prompt = f"""
You are an executive intelligence director curating high-impact briefings for university leadership and education executives.
Target Recency Window: Strictly past 24 hours ({target_window_str}).

Analyze the candidate real-time headlines below and curate them into 4 distinct, high-value sections:

--- 1. TECH & AI HEADLINES ---
{json.dumps(tech_candidates, indent=2)}
Guidelines:
- Select 4 to 5 genuine frontier developments: New AI model launches (OpenAI, Gemini, Anthropic, DeepSeek, Meta), reasoning breakthroughs, major AI compute milestones. Reject generic blogs or minor app updates.

--- 2. INDIA EDUCATION SECTOR HEADLINES (TOP 10) ---
{json.dumps(india_candidates, indent=2)}
Guidelines:
- Select exactly the TOP 10 most important headlines covering national education policy, UGC/AICTE reforms, premier institutes (IIT/IIM/IISc/Central Universities), major research discoveries, accreditation, or national higher education initiatives.
- Reject trivial seat vacancies, local student club events, or routine exam schedules.

--- 3. WORLD EDUCATION SECTOR HEADLINES (TOP 5) ---
{json.dumps(world_candidates, indent=2)}
Guidelines:
- Select exactly the TOP 5 most significant global education headlines covering top international universities (MIT, Harvard, Oxford, Stanford, etc.), global university rankings, breakthrough university research, or international student/academic policy.

--- 4. RAJASTHAN EDUCATION HEADLINES (TOP 3 TO 5) ---
{json.dumps(rajasthan_candidates, indent=2)}
Guidelines:
- Select the TOP 3 to 5 education headlines specifically impacting Rajasthan (Rajasthan universities, state education department reforms, schools/colleges in Jaipur/Jodhpur/Kota/Udaipur, IIT Jodhpur, MNIT Jaipur, or state educational initiatives).
- Reject routine admit card download links or exam form alerts; prioritize policy, infrastructure, university innovations, or major reforms.

CRITICAL RECENCY INSTRUCTION:
- All selected news must strictly reflect the last 24-hour window up to the current run time.

For EVERY selected item provide:
- "title": Clean, professional headline (strip out redundant source suffix, fix any corrupted quotes or characters)
- "summary": Exactly 1 crisp sentence explaining what makes this significant or what decision was taken.
- "source": Source publication or institute name
- "pub_date": Clean publication date (e.g. {now.strftime('%a, %d %b %Y')})

Return strictly valid JSON:
{{
  "tech_ai": [ ... 4-5 items ... ],
  "education_india": [ ... 10 items ... ],
  "education_world": [ ... 5 items ... ],
  "education_rajasthan": [ ... 3-5 items ... ]
}}
"""

    headers = {"Content-Type": "application/json"}
    for m in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            res = requests.post(url, headers=headers, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
            }, timeout=25)

            if res.status_code == 200:
                raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(raw_text)
                if "education_india" in data and "education_world" in data:
                    print(f"✅ News successfully curated using Gemini ({m}).")
                    return data
        except Exception:
            continue

    return None

def heuristic_fallback(
    tech_cands: List[Dict[str, str]],
    india_cands: List[Dict[str, str]],
    world_cands: List[Dict[str, str]],
    raj_cands: List[Dict[str, str]]
) -> Dict[str, List[Dict[str, str]]]:
    """Smart heuristic fallback if Gemini is unreachable."""
    def clean_batch(items, max_n=5, summary_text="Key educational update"):
        negatives = ["admit card", "hall ticket", "seat vacant", "counselling date", "club"]
        cleaned = []
        for it in items:
            t = it["title"].lower()
            if not any(neg in t for neg in negatives):
                cleaned.append({
                    **it,
                    "summary": it.get("summary", summary_text)
                })
        return cleaned[:max_n] if cleaned else items[:max_n]

    return {
        "tech_ai": clean_batch(tech_cands, 4, "Major AI technology and model milestone from past 24-48 hours."),
        "education_india": clean_batch(india_cands, 10, "National educational and institutional development in India from past 24-48 hours."),
        "education_world": clean_batch(world_cands, 5, "Global higher education and international university development from past 24-48 hours."),
        "education_rajasthan": clean_batch(raj_cands, 5, "Key state-level educational and academic update for Rajasthan from past 24-48 hours.")
    }

def fetch_important_news() -> Dict[str, List[Dict[str, str]]]:
    """
    Fetches real-time, curated, high-impact news strictly from 1 day previous (last 24-48 hours) across:
    1. Tech & AI News
    2. India Higher Education News (Top 10)
    3. World Higher Education News (Top 5)
    4. Rajasthan Education News (Top 3-5)
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    from concurrent.futures import ThreadPoolExecutor

    print("📰 Fetching 1-day previous news headlines in parallel (Tech, India Ed, World Ed, Rajasthan)...")
    tasks = [
        ("tech", '(AI model launch OR new AI model OR OpenAI OR Anthropic OR DeepSeek OR "Google Gemini" OR "AI breakthrough") when:2d', 15, 48, "en-IN", "IN", "IN:en"),
        ("tech", '(frontier AI OR "AI reasoning" OR "autonomous agent" OR "NVIDIA AI") when:2d', 15, 48, "en-IN", "IN", "IN:en"),
        ("india", '(UGC OR AICTE OR "higher education" OR IIT OR IIM OR "NEP 2020") (reform OR research OR policy OR innovation OR ranking OR grant) when:2d', 20, 48, "en-IN", "IN", "IN:en"),
        ("india", '("Ministry of Education" OR "university grant" OR "autonomous college" OR "accreditation") India when:2d', 20, 48, "en-IN", "IN", "IN:en"),
        ("world", '("higher education" OR "world university" OR "global universities" OR MIT OR Harvard OR Oxford OR Stanford OR Cambridge) (breakthrough OR research OR ranking OR discovery OR policy) when:2d', 20, 48, "en-US", "US", "US:en"),
        ("world", '("Times Higher Education" OR "QS World University" OR "international students" OR "global academia") when:2d', 20, 48, "en-US", "US", "US:en"),
        ("raj", 'Rajasthan (university OR college OR "higher education" OR "school education" OR "education minister" OR "MNIT Jaipur" OR "IIT Jodhpur" OR "RU Jaipur") when:2d', 20, 48, "en-IN", "IN", "IN:en"),
        ("raj", '(Jaipur OR Jodhpur OR Kota OR Udaipur OR Bikaner) (university OR college OR "education department" OR "school infrastructure") when:2d', 20, 48, "en-IN", "IN", "IN:en")
    ]

    tech_cands = []
    india_cands = []
    world_cands = []
    raj_cands = []

    def fetch_task(t):
        cat, query, max_items, max_lookback_hours, hl, gl, ceid = t
        try:
            return cat, fetch_rss_candidates(query, max_items=max_items, max_lookback_hours=max_lookback_hours, hl=hl, gl=gl, ceid=ceid)
        except Exception:
            return cat, []

    with ThreadPoolExecutor(max_workers=8) as executor:
        for cat, items in executor.map(fetch_task, tasks):
            if cat == "tech":
                tech_cands.extend(items)
            elif cat == "india":
                india_cands.extend(items)
            elif cat == "world":
                world_cands.extend(items)
            elif cat == "raj":
                raj_cands.extend(items)

    tech_cands = deduplicate_items(tech_cands)
    india_cands = deduplicate_items(india_cands)
    world_cands = deduplicate_items(world_cands)
    raj_cands = deduplicate_items(raj_cands)

    api_key = os.getenv("GEMINI_API_KEY")
    curated = None
    if api_key and api_key != "your_gemini_api_key_here":
        print("🧠 Passing 1-day previous candidates through Gemini intelligence curator...")
        curated = curate_all_news_with_gemini(tech_cands, india_cands, world_cands, raj_cands, api_key)

    if not curated:
        print("⚡ Using high-precision keyword curation fallback...")
        curated = heuristic_fallback(tech_cands, india_cands, world_cands, raj_cands)

    # Maintain backward compatibility with 'education' key
    if "education" not in curated:
        curated["education"] = curated.get("education_india", [])

    return curated

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    news = fetch_important_news()

    print("\n" + "="*70)
    print("🤖 TECH & AI NEWS (1-Day Previous Breakthroughs & Launches):")
    print("="*70)
    for idx, item in enumerate(news.get("tech_ai", []), 1):
        print(f"\n{idx}. ⚡ {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")

    print("\n" + "="*70)
    print("🇮🇳 TOP 10 INDIA EDUCATION SECTOR NEWS (1-Day Previous):")
    print("="*70)
    for idx, item in enumerate(news.get("education_india", []), 1):
        print(f"\n{idx}. 🎓 {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")

    print("\n" + "="*70)
    print("🌍 TOP 5 WORLD EDUCATION SECTOR NEWS (1-Day Previous):")
    print("="*70)
    for idx, item in enumerate(news.get("education_world", []), 1):
        print(f"\n{idx}. 🌐 {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")

    print("\n" + "="*70)
    print("🏰 TOP RAJASTHAN EDUCATION NEWS (1-Day Previous):")
    print("="*70)
    for idx, item in enumerate(news.get("education_rajasthan", []), 1):
        print(f"\n{idx}. 🏛️ {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")
