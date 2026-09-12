import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

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
                        "location": "Board Room / Hybrid",
                        "attendees": "Department HODs, Dean Academics",
                        "notes": "Review draft curriculum changes for autonomous accreditation"
                    },
                    {
                        "time": "02:30 PM - 03:15 PM",
                        "title": "Budget Review & Vendor Sign-off",
                        "location": "Dean's Office",
                        "attendees": "Finance Officer, Borosil Supplies",
                        "notes": "Sign off on cleared Chemistry Lab invoice (Rs 4,80,000)"
                    },
                    {
                        "time": "04:30 PM - 05:00 PM",
                        "title": "VIP Briefing: State University Registrar",
                        "location": "Directorate Committee Room",
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

def get_pa_agenda(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves the meetings and reminders for a specific date (YYYY-MM-DD).
    Defaults to today if no date is provided.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    store = load_all_schedules()
    agenda = store.get(target_date, {
        "meetings": [],
        "reminders": []
    })
    return agenda

def set_pa_agenda(target_date: str, meetings: List[Dict[str, str]], reminders: List[str]):
    """Saves or updates meetings and reminders for a specific date."""
    store = load_all_schedules()
    store[target_date] = {
        "meetings": meetings or [],
        "reminders": reminders or []
    }
    save_all_schedules(store)

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    agenda = get_pa_agenda(today)
    print(f"PA Agenda for {today}:")
    print(f"  • Meetings: {len(agenda.get('meetings', []))}")
    print(f"  • Reminders: {len(agenda.get('reminders', []))}")
