import os
from typing import Dict, Any

def send_whatsapp_message(
    body: str,
    to_number: str = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Sends a WhatsApp message via Twilio or simulates it in dry-run mode.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO")

    if dry_run or not account_sid or account_sid == "your_twilio_account_sid":
        print("\n" + "=" * 60)
        print("📱 [SIMULATED WHATSAPP DISPATCH - DRY RUN / PREVIEW]")
        print(f"To: {recipient or '+91XXXXXXXXXX (Configure in .env)'}")
        print("=" * 60)
        print(body)
        print("=" * 60 + "\n")
        return {"status": "simulated", "message_id": "mock_msg_12345"}

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        # Twilio requires numbers prefixed with 'whatsapp:'
        formatted_to = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
        formatted_from = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"

        message = client.messages.create(
            body=body,
            from_=formatted_from,
            to=formatted_to
        )
        print(f"✅ WhatsApp message sent successfully! SID: {message.sid}")
        return {"status": "success", "message_id": message.sid}
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message via Twilio: {str(e)}")
        return {"status": "error", "error": str(e)}

def send_via_whatsapp_web(body: str, to_number: str = None) -> Dict[str, Any]:
    """
    Directly delivers the message to WhatsApp Web without any Twilio templates or restrictions.
    """
    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO", "+917378020506")
    clean_phone = recipient.replace("whatsapp:", "").replace(" ", "").strip()
    if not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone

    print(f"🚀 Opening WhatsApp Web to deliver digest to {clean_phone}...")
    try:
        import pywhatkit
        pywhatkit.sendwhatmsg_instantly(
            phone_no=clean_phone,
            message=body,
            wait_time=15,
            tab_close=False
        )
        print("✅ Message sent via WhatsApp Web!")
        return {"status": "success", "provider": "whatsapp_web"}
    except Exception as e:
        print(f"❌ Error sending via WhatsApp Web: {e}")
        return {"status": "error", "error": str(e)}

def ensure_gateway_running() -> bool:
    """Checks if the local WhatsApp gateway is running, and starts it if not."""
    import requests
    try:
        r = requests.get("http://localhost:3000/status", timeout=2)
        if r.status_code == 200 and r.json().get("whatsapp_connected"):
            return True
    except Exception:
        pass

    # Attempt to start the server
    import subprocess
    import sys
    import time
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gateway_dir = os.path.join(base_dir, "whatsapp_server")
    print("🚀 Local WhatsApp Gateway not running. Auto-launching in background...")
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            ["node", "server.js"],
            cwd=gateway_dir,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(12):
            time.sleep(1)
            try:
                r = requests.get("http://localhost:3000/status", timeout=2)
                if r.status_code == 200 and r.json().get("whatsapp_connected"):
                    print("✅ Local WhatsApp Gateway auto-started and connected!")
                    return True
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ Could not auto-launch gateway: {e}")
    return False

def send_via_local_gateway(body: str, to_number: str = None) -> Dict[str, Any]:
    """
    Sends message via our local WhatsApp Gateway (http://localhost:3000/send).
    Completely headless, runs 24/7 in the background with no popups and zero fees.
    """
    ensure_gateway_running()
    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO", "917378020506")
    clean_phone = "".join(filter(str.isdigit, recipient))

    print(f"📡 Sending via Local WhatsApp Gateway to {clean_phone}...")
    try:
        import requests
        resp = requests.post(
            "http://localhost:3000/send",
            json={"number": clean_phone, "message": body},
            timeout=20
        )
        if resp.status_code == 200:
            print("✅ Message successfully sent via Local WhatsApp Gateway!")
            return {"status": "success", "provider": "local_gateway", "data": resp.json()}
        else:
            print(f"⚠️ Gateway returned {resp.status_code}: {resp.text}")
            return {"status": "error", "error": resp.text}
    except Exception as e:
        print(f"❌ Could not reach Local Gateway at http://localhost:3000: {e}")
        return {"status": "error", "error": str(e)}


