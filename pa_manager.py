import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
SCHEDULE_FILE = os.path.join(DATA_DIR, "pa_schedule.json")

def _ensure_data_file():
    """Ensures the data directory and schedule store exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SCHEDULE_FILE):
        default_store = {
            datetime.now().strftime("%Y-%m-%d"): {
                "meetings": [
                    {
                        "time": "10:00 AM - 11:00 AM",
                        "title": "Academic Council & Curriculum Review",
                        "attendees": "Department HODs, Dean Academics",
                        "notes": "Review draft curriculum changes for autonomous accreditation"
                    },
                    {
                        "time": "02:30 PM - 03:15 PM",
                        "title": "Budget Review & Vendor Sign-off",
                        "attendees": "Finance Officer, Borosil Supplies",
                        "notes": "Sign off on cleared Chemistry Lab invoice (Rs 4,80,000)"
                    },
                    {
                        "time": "04:30 PM - 05:00 PM",
                        "title": "VIP Briefing: State University Registrar",
                        "attendees": "State University Registrar, Dean",
                        "notes": "Review readiness for NAAC Peer Team inspection"
                    }
                ],
                "reminders": [
                    "Sign and endorse state scholarship merit-cum-means applications by 3:00 PM",
                    "Finalize faculty duty leave approvals for International Robotics Symposium"
                ]
            }
        }
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_store, f, indent=2, ensure_ascii=False)

def load_all_schedules() -> Dict[str, Any]:
    """Loads all scheduled dates from the JSON store."""
    _ensure_data_file()
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not read {SCHEDULE_FILE}: {e}")
        return {}

def save_all_schedules(store: Dict[str, Any]):
    """Saves entire schedule store to JSON."""
    _ensure_data_file()
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

def format_time_to_12h(time_str: str) -> str:
    """
    Converts 24-hour time or time ranges to clean 12-hour AM/PM format.
    Examples:
        "13:50" -> "01:50 PM"
        "8:39" -> "08:39 AM"
        "10:10" -> "10:10 AM"
        "12:39" -> "12:39 PM"
        "1:00 pm" -> "01:00 PM"
        "13:50 - 14:30" -> "01:50 PM - 02:30 PM"
    """
    if not time_str or not isinstance(time_str, str):
        return time_str or ""
    
    import re
    def repl(m):
        h = int(m.group(1))
        mins = int(m.group(2))
        raw_ampm = m.group(3)
        if raw_ampm:
            ampm = raw_ampm.upper()
            display_h = 12 if h in [0, 12] else h % 12
            return f"{display_h:02d}:{mins:02d} {ampm}"
        else:
            ampm = "AM" if h < 12 else "PM"
            display_h = 12 if h in [0, 12] else h % 12
            return f"{display_h:02d}:{mins:02d} {ampm}"

    return re.sub(r'\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?:\s*([aApP][mM]))?\b', repl, time_str)

def get_pa_agenda(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves the meetings and reminders for a specific date (YYYY-MM-DD).
    Defaults to today if no date is provided.
    Always converts meeting times to 12-hour AM/PM format.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    store = load_all_schedules()
    raw_agenda = store.get(target_date, {
        "meetings": [],
        "reminders": []
    })

    formatted_meetings = []
    for m in raw_agenda.get("meetings", []):
        m_copy = dict(m)
        m_copy["time"] = format_time_to_12h(m.get("time", ""))
        formatted_meetings.append(m_copy)

    return {
        "meetings": formatted_meetings,
        "reminders": raw_agenda.get("reminders", [])
    }

def set_pa_agenda(target_date: str, meetings: List[Dict[str, str]], reminders: List[str]):
    """Saves or updates meetings and reminders for a specific date in 12-hour format."""
    store = load_all_schedules()
    clean_meetings = []
    for m in (meetings or []):
        m_copy = dict(m)
        m_copy["time"] = format_time_to_12h(m.get("time", ""))
        clean_meetings.append(m_copy)

    store[target_date] = {
        "meetings": clean_meetings,
        "reminders": reminders or []
    }
    save_all_schedules(store)

def archive_pa_agenda(target_date: Optional[str] = None):
    """
    Archives a snapshot of the dispatched PA schedule to data/pa_schedule_history.json.
    Keeps the active schedule intact in data/pa_schedule.json so meetings are NEVER erased.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    _ensure_data_file()
    store = load_all_schedules()
    active_agenda = store.get(target_date, {"meetings": [], "reminders": []})

    # Only archive if there was actually schedule data
    if active_agenda.get("meetings") or active_agenda.get("reminders"):
        history_file = os.path.join(DATA_DIR, "pa_schedule_history.json")
        history = {}
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = {}
        
        now_str = datetime.now().isoformat()
        if target_date not in history:
            history[target_date] = []
        history[target_date].append({
            "dispatched_at": now_str,
            "agenda": active_agenda
        })
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Warning: Could not write schedule history: {e}")
        print(f"📁 PA schedule snapshot for {target_date} archived to history (active schedule preserved).")

# Alias for backwards compatibility
archive_and_reset_pa_agenda = archive_pa_agenda

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    agenda = get_pa_agenda(today)
    print(f"PA Agenda for {today}:")
    print(f"  • Meetings: {len(agenda.get('meetings', []))}")
    print(f"  • Reminders: {len(agenda.get('reminders', []))}")
