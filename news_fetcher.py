import os
import sys
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def fetch_rss_candidates(query: str, max_items: int = 15) -> List[Dict[str, str]]:
    """
    Fetches raw news candidates from Google News RSS feed for a targeted search query.
    100% free, requires no API key.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    items = []
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item")[:max_items]:
                raw_title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                source = item.findtext("source", "")

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
                        "pub_date": pub_date[:16] if pub_date else "Recent",
                        "link": link
                    })
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

def curate_news_with_gemini(
    tech_candidates: List[Dict[str, str]], 
    edu_candidates: List[Dict[str, str]], 
    api_key: str
) -> Dict[str, List[Dict[str, str]]]:
    """
    Uses Google Gemini to curate, evaluate, and extract ONLY the top breakthrough, 
    high-impact news items from candidate pools.
    """
    import requests

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.6-flash"]

    prompt = f"""
You are an executive intelligence director curating high-impact briefings for university leadership and tech executives.
Analyze the candidate real-time headlines below.

--- CANDIDATE TECH & AI HEADLINES ---
{json.dumps(tech_candidates, indent=2)}

--- CANDIDATE HIGHER EDUCATION & PREMIER INSTITUTES HEADLINES ---
{json.dumps(edu_candidates, indent=2)}

CURATION RULES:
1. TECH & AI:
   - Select ONLY genuine major developments: New AI model launches (OpenAI, Gemini, Anthropic, DeepSeek, Meta), AI reasoning breakthroughs, major compute/chip milestones, or high-impact frontier AI shifts.
   - STRICTLY REJECT: Personal lifestyle pieces, opinion blogs, minor consumer gadgets, or trivial fluff.
2. HIGHER EDUCATION & PREMIER INSTITUTES:
   - Select ONLY major institutional milestones: Premier institutes (IITs, IISc, MIT, Stanford, Harvard, AIIMS, etc.) developing breakthrough tech/inventions, groundbreaking scientific discoveries, major international research partnerships, or high-impact campus innovations.
   - STRICTLY REJECT: Routine admission notices, seat vacancies, local student club events, commercial college advertisements/rankings PR, or basic college exams.

Select 3 to 5 top items for "tech_ai" and 3 to 5 top items for "education".
For each item:
- "title": Clean, professional headline (strip out redundant source suffix, fix corrupted characters)
- "summary": Exactly 1 crisp sentence explaining why this is significant or what was launched/discovered.
- "source": Publication or institute name
- "pub_date": Publication time tag

Return strictly valid JSON:
{{
  "tech_ai": [
    {{"title": "...", "summary": "...", "source": "...", "pub_date": "..."}}
  ],
  "education": [
    {{"title": "...", "summary": "...", "source": "...", "pub_date": "..."}}
  ]
}}
"""

    for m in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            res = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
            }, timeout=20)

            if res.status_code == 200:
                raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(raw_text)
                if "tech_ai" in data and "education" in data:
                    print(f"✅ News successfully curated using Gemini ({m}).")
                    return data
        except Exception as e:
            continue

    return None

def algorithmic_filter(tech_candidates: List[Dict[str, str]], edu_candidates: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Intelligent heuristic fallback if Gemini is offline or quota-limited.
    Scores candidates by breakthrough keywords and eliminates routine admission/PR fluff.
    """
    negative_edu = ["vacant", "seat", "admission", "admissions", "hall ticket", "counselling", "club", "fest", "exam date", "timetable"]
    priority_institutes = ["iit", "iisc", "stanford", "mit", "harvard", "oxford", "aiims", "imperial", "researchers"]

    filtered_edu = []
    for it in edu_candidates:
        title_lower = it["title"].lower()
        if any(neg in title_lower for neg in negative_edu):
            continue
        score = 0
        if any(inst in title_lower for inst in priority_institutes):
            score += 2
        if any(kw in title_lower for kw in ["breakthrough", "develops", "discovers", "innovation", "partnership", "launches", "patent"]):
            score += 2
        if score > 0:
            filtered_edu.append({
                **it,
                "summary": f"Key institutional milestone involving research, innovation, or technology development."
            })

    filtered_tech = []
    priority_tech = ["openai", "gemini", "anthropic", "deepseek", "meta", "nvidia", "model launch", "reasoning"]
    for it in tech_candidates:
        title_lower = it["title"].lower()
        if any(neg in title_lower for neg in ["father of", "parent", "kid", "movie", "how to"]):
            continue
        if any(kw in title_lower for kw in priority_tech) or "breakthrough" in title_lower:
            filtered_tech.append({
                **it,
                "summary": f"Major artificial intelligence frontier milestone and technology development."
            })

    return {
        "tech_ai": filtered_tech[:5] if filtered_tech else tech_candidates[:4],
        "education": filtered_edu[:5] if filtered_edu else edu_candidates[:4]
    }

def fetch_important_news() -> Dict[str, List[Dict[str, str]]]:
    """
    Fetches real-time, curated, high-impact headlines for:
    1. Tech & AI News (New AI model launches, frontier breakthroughs)
    2. Higher Education & Premier Institutions (Breakthrough discoveries, major tech & partnerships)
    """
    print("📰 Fetching real-time candidate headlines for Tech & AI...")
    tech_queries = [
        '(AI model launch OR new AI model OR OpenAI OR Anthropic OR DeepSeek OR "Google Gemini" OR "AI breakthrough") when:3d',
        '(frontier AI OR "AI reasoning" OR "autonomous agent" OR "NVIDIA AI") when:3d'
    ]
    tech_candidates = []
    for q in tech_queries:
        tech_candidates.extend(fetch_rss_candidates(q, max_items=10))

    print("🎓 Fetching real-time candidate headlines for Higher Education & Premier Institutes...")
    edu_queries = [
        '(IIT OR IISc OR Stanford OR MIT OR AIIMS OR "premier institute") (breakthrough OR develops OR discovers OR innovation OR "launches AI") when:7d',
        '("university researchers" OR "premier university") (breakthrough OR "develops new" OR "discovers" OR "patent" OR "partnership") when:7d'
    ]
    edu_candidates = []
    for q in edu_queries:
        edu_candidates.extend(fetch_rss_candidates(q, max_items=10))

    tech_candidates = deduplicate_items(tech_candidates)
    edu_candidates = deduplicate_items(edu_candidates)

    api_key = os.getenv("GEMINI_API_KEY")
    curated = None
    if api_key and api_key != "your_gemini_api_key_here":
        print("🧠 Passing candidates through Gemini intelligence curator...")
        curated = curate_news_with_gemini(tech_candidates, edu_candidates, api_key)

    if not curated:
        print("⚡ Using high-precision keyword curation filter...")
        curated = algorithmic_filter(tech_candidates, edu_candidates)

    return curated

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    news = fetch_important_news()
    print("\n" + "="*60)
    print("🤖 TECH & AI NEWS (High-Impact & Breakthroughs):")
    print("="*60)
    for idx, item in enumerate(news.get("tech_ai", []), 1):
        print(f"\n{idx}. ⚡ {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")

    print("\n" + "="*60)
    print("🏛️ HIGHER EDUCATION & INSTITUTES (Breakthroughs & Milestones):")
    print("="*60)
    for idx, item in enumerate(news.get("education", []), 1):
        print(f"\n{idx}. 🎓 {item.get('title')}")
        if item.get("summary"):
            print(f"   💡 {item.get('summary')}")
        print(f"   📰 {item.get('source')} | {item.get('pub_date')}")
