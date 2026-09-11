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
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
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
    """Checks if the local WhatsApp gateway on port 3000 is online and connected."""
    try:
        r = requests.get("http://127.0.0.1:3000/status", timeout=3)
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
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TRIGGERING DIGEST DISPATCH ({mode.upper()})")
    print("=" * 60)

    ensure_gateway_started()

    flag = "--today" if mode == "today" else "--yesterday"
    cmd = [sys.executable, "-X", "utf8", "main.py", "--live", flag, "--gateway"]

    try:
        res = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8")
        print(res.stdout)
        if res.stderr:
            print("Errors/Warnings:\n", res.stderr)
        print("✅ Automated digest run finished.")
    except Exception as e:
        print(f"❌ Failed to run digest job: {e}")

def parse_hm(time_str: str) -> dtime:
    """Parses HH:MM into a time object."""
    h, m = map(int, time_str.strip().split(":"))
    return dtime(hour=h, minute=m)

def main():
    load_dotenv()
    import argparse
    parser = argparse.ArgumentParser(description="Automated Email Digest Scheduler with Smart Catch-Up")
    parser.add_argument("--now", action="store_true", help="Run the digest immediately and exit")
    parser.add_argument("--morning", type=str, default="09:00", help="Time for morning digest (HH:MM 24h, default 09:00)")
    parser.add_argument("--evening", type=str, default="20:00", help="Time for evening digest (HH:MM 24h, default 20:00)")
    parser.add_argument("--interval-hours", type=int, default=None, help="Run periodically every N hours")
    args = parser.parse_args()

    ensure_gateway_started()

    if args.now:
        print("⚡ Executing immediate digest dispatch...")
        run_digest_job(mode="today")
        return

    morning_time = parse_hm(args.morning)
    evening_time = parse_hm(args.evening)

    print("=" * 60)
    print("🤖 AUTOMATED WHATSAPP DIGEST SCHEDULER (SMART CATCH-UP ENABLED)")
    if args.interval_hours:
        print(f"🔁 Mode: Periodic interval every {args.interval_hours} hour(s)")
    else:
        print(f"📅 Daily Schedules -> Morning: {args.morning} | Evening: {args.evening}")
        print("💡 Smart Catch-up: If your PC was off during a scheduled time,")
        print("   it will trigger automatically upon boot/start.")
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

    # Daily scheduled times (Morning & Evening) with Smart Catch-up
    while True:
        now = datetime.now()
        cur_time = now.time()
        today_date = now.strftime("%Y-%m-%d")
        state = load_state()

        # Check if Evening Digest is due or missed
        if cur_time >= evening_time:
            if state.get("last_evening_run") != today_date:
                print(f"\n🔔 [Smart Catch-Up / Schedule] Triggering evening digest for {today_date}...")
                run_digest_job(mode="today")
                state["last_evening_run"] = today_date
                # If morning was also missed earlier, mark it so we don't send yesterday's digest late at night
                state["last_morning_run"] = today_date
                save_state(state)

        # Check if Morning Digest is due or missed (between morning and evening cutoff)
        elif cur_time >= morning_time:
            if state.get("last_morning_run") != today_date:
                print(f"\n🔔 [Smart Catch-Up / Schedule] Triggering morning digest for {today_date}...")
                run_digest_job(mode="yesterday")
                state["last_morning_run"] = today_date
                save_state(state)

        time.sleep(25)  # Check every 25 seconds

if __name__ == "__main__":
    main()
