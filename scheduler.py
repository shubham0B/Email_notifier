import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime, time as dtime
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
GATEWAY_DIR = os.path.join(PROJECT_DIR, "whatsapp_server")
STATE_FILE = os.path.join(PROJECT_DIR, ".scheduler_state.json")

def load_state() -> dict:
    """Loads scheduler persistent state to detect missed runs."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state: dict):
    """Saves scheduler state to disk."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save scheduler state: {e}")

def is_gateway_running() -> bool:
    """Checks if the local WhatsApp gateway is online and connected."""
    port = os.getenv("PORT", os.getenv("GATEWAY_PORT", "3000"))
    try:
        r = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
        return r.status_code == 200 and r.json().get("whatsapp_connected", False)
    except Exception:
        return False

def ensure_gateway_started():
    """Starts the WhatsApp gateway in background if not already running."""
    if is_gateway_running():
        print("✅ Local WhatsApp Gateway is already active and connected.")
        return

    print("🚀 Starting Local WhatsApp Gateway (whatsapp_server/server.js)...")
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW
        
        subprocess.Popen(
            ["node", "server.js"],
            cwd=GATEWAY_DIR,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait up to 15 seconds for connection
        for i in range(15):
            time.sleep(1)
            if is_gateway_running():
                print("✅ WhatsApp Gateway started and connected successfully!")
                return
        print("⚠️ WhatsApp Gateway started, waiting for WhatsApp handshake...")
    except Exception as e:
        print(f"❌ Could not start WhatsApp gateway: {e}")

def run_digest_job(mode: str = "today"):
    """Executes the email digest pipeline and sends to WhatsApp."""
    print("\n" + "=" * 60)
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}] TRIGGERING DIGEST DISPATCH ({mode.upper()})")
    print("=" * 60)

    ensure_gateway_started()

    cmd = [sys.executable, "-X", "utf8", "main.py", "--live", "--gateway"]

    try:
        res = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8")
        print(res.stdout)
        if res.stderr:
            print("Errors/Warnings:\n", res.stderr)
        print("✅ Automated digest run finished.")
    except Exception as e:
        print(f"❌ Failed to run digest job: {e}")

def parse_hm(time_str: str) -> dtime:
    """Parses time string (supports 24h '14:30' and 12h '02:30 PM') into a time object."""
    clean = time_str.strip()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(clean, fmt).time()
        except ValueError:
            pass
    import re
    m = re.match(r'^(\d{1,2}):(\d{2})(?:\s*([APap][Mm]))?$', clean)
    if m:
        h = int(m.group(1))
        mins = int(m.group(2))
        ampm = m.group(3)
        if ampm:
            if ampm.upper() == 'PM' and h < 12:
                h += 12
            elif ampm.upper() == 'AM' and h == 12:
                h = 0
        return dtime(hour=h, minute=mins)
    return dtime(hour=9, minute=0)

def main():
    load_dotenv()
    import argparse
    parser = argparse.ArgumentParser(description="Automated Email Digest Scheduler (Single Daily Briefing)")
    parser.add_argument("--now", action="store_true", help="Run the digest immediately and exit")
    default_briefing_time = os.getenv("SCHEDULED_BRIEFING_TIME", "09:00")
    parser.add_argument("--time", type=str, default=default_briefing_time, help=f"Time for daily digest (default {default_briefing_time})")
    parser.add_argument("--interval-hours", type=int, default=None, help="Run periodically every N hours")
    args = parser.parse_args()

    ensure_gateway_started()

    if args.now:
        print("⚡ Executing immediate digest dispatch...")
        run_digest_job(mode="today")
        today_date = datetime.now().strftime("%Y-%m-%d")
        state = load_state()
        state["last_daily_run"] = today_date
        save_state(state)
        return

    briefing_time = parse_hm(args.time)
    display_time = briefing_time.strftime("%I:%M %p")

    print("=" * 60)
    print("🤖 AUTOMATED WHATSAPP DIGEST SCHEDULER (SINGLE DAILY REPORT)")
    if args.interval_hours:
        print(f"🔁 Mode: Periodic interval every {args.interval_hours} hour(s)")
    else:
        print(f"📅 Daily Briefing Schedule: {display_time} (Exactly 1 report per day)")
        print("💡 Smart Catch-up: If your PC was off during the scheduled time,")
        print("   it will trigger once upon boot/start for the day.")
    print("⚡ Press Ctrl+C at any time to stop.")
    print("=" * 60)

    # If running on interval
    if args.interval_hours:
        while True:
            state = load_state()
            now = datetime.now()
            last_run = state.get("last_interval_run")
            should_run = False
            if not last_run:
                should_run = True
            else:
                last_dt = datetime.fromisoformat(last_run)
                if (now - last_dt).total_seconds() >= (args.interval_hours * 3600):
                    should_run = True

            if should_run:
                run_digest_job(mode="today")
                state["last_interval_run"] = now.isoformat()
                save_state(state)

            time.sleep(60)

    # Single Daily scheduled time with Smart Catch-up
    while True:
        now = datetime.now()
        cur_time = now.time()
        today_date = now.strftime("%Y-%m-%d")
        state = load_state()

        # Check if the single daily digest is due or missed today
        if cur_time >= briefing_time:
            if state.get("last_daily_run") != today_date and state.get("last_morning_run") != today_date:
                print(f"\n🔔 [Schedule] Triggering single daily digest for {today_date}...")
                run_digest_job(mode="today")
                state["last_daily_run"] = today_date
                save_state(state)

        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()
