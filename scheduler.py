import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
GATEWAY_DIR = os.path.join(PROJECT_DIR, "whatsapp_server")

def is_gateway_running() -> bool:
    """Checks if the local WhatsApp gateway on port 3000 is online and connected."""
    try:
        r = requests.get("http://localhost:3000/status", timeout=3)
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
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TRIGGERING AUTOMATED DIGEST DISPATCH")
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

def main():
    load_dotenv()
    import argparse
    parser = argparse.ArgumentParser(description="Automated Email Digest Scheduler")
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

    print("=" * 60)
    print("🤖 AUTOMATED WHATSAPP DIGEST SCHEDULER STARTED")
    if args.interval_hours:
        print(f"🔁 Mode: Periodic interval every {args.interval_hours} hour(s)")
    else:
        print(f"📅 Mode: Daily Schedules -> Morning: {args.morning} | Evening: {args.evening}")
    print("⚡ Press Ctrl+C at any time to stop.")
    print("=" * 60)

    last_run_date = None
    last_run_time_hour = None

    # If running on interval
    if args.interval_hours:
        while True:
            run_digest_job(mode="today")
            print(f"💤 Sleeping for {args.interval_hours} hour(s)...")
            time.sleep(args.interval_hours * 3600)

    # Daily scheduled times (Morning & Evening)
    while True:
        now = datetime.now()
        now_hm = now.strftime("%H:%M")
        today_date = now.strftime("%Y-%m-%d")

        if now_hm == args.morning and last_run_time_hour != f"{today_date}-morning":
            print(f"🔔 Morning digest time reached ({args.morning})!")
            run_digest_job(mode="yesterday")
            last_run_time_hour = f"{today_date}-morning"

        elif now_hm == args.evening and last_run_time_hour != f"{today_date}-evening":
            print(f"🔔 Evening digest time reached ({args.evening})!")
            run_digest_job(mode="today")
            last_run_time_hour = f"{today_date}-evening"

        time.sleep(25)  # Check every 25 seconds

if __name__ == "__main__":
    main()
