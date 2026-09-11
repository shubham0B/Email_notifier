import os
import sys
from typing import Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    Directly delivers the message to WhatsApp Web and automatically triggers the Send button.
    Eliminates pywhatkit's bug where clicking screen-center unfocuses the input box.
    """
    import time
    import urllib.parse
    import webbrowser
    import pyautogui
    import pyperclip

    pyautogui.FAILSAFE = False

    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO", "")
    # WhatsApp Web requires DIGITS ONLY in the URL. A '+' sign in query strings turns into a space (%20)
    clean_phone = "".join(filter(str.isdigit, recipient))

    # Copy message to clipboard as backup
    try:
        pyperclip.copy(body)
    except Exception:
        pass

    encoded_message = urllib.parse.quote(body)
    url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"

    print(f"🚀 Opening WhatsApp Web to deliver digest to {clean_phone}...")
    webbrowser.open(url)

    wait_seconds = int(os.getenv("WHATSAPP_WEB_WAIT", "20"))
    print(f"⏳ Waiting {wait_seconds}s for WhatsApp Web interface to load and ready the Send button...")
    for sec in range(wait_seconds, 0, -5):
        print(f"   [{sec}s remaining...]")
        time.sleep(min(5, sec))

    try:
        screen_w, screen_h = pyautogui.size()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        send_btn_path = os.path.join(base_dir, "send_button.png")

        print("⌨️  Locating WhatsApp Web Send button...")

        # 1. Bring browser window to foreground
        pyautogui.click(screen_w // 2, screen_h // 2)
        time.sleep(0.3)

        # 2. Computer Vision Recognition: Locate the exact green send button on screen
        clicked = False
        if os.path.exists(send_btn_path):
            print("🔍 Scanning screen with OpenCV for green Send button icon...")
            for attempt in range(8):
                try:
                    loc = pyautogui.locateCenterOnScreen(send_btn_path, confidence=0.85)
                    if not loc:
                        loc = pyautogui.locateCenterOnScreen(send_btn_path, confidence=0.75)
                    if loc:
                        print(f"🎯 Exact Send button detected on screen at: ({loc.x}, {loc.y})! Clicking now...")
                        pyautogui.click(loc.x, loc.y)
                        time.sleep(0.2)
                        pyautogui.click(loc.x, loc.y)
                        clicked = True
                        break
                except Exception:
                    pass
                time.sleep(0.8)

        # 3. Direct Keyboard Send
        print("⌨️  Triggering Enter and Ctrl+Enter keystrokes...")
        pyautogui.press("enter")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "enter")
        time.sleep(0.3)

        # Only press Enter from keyboard - absolutely NO random coordinate clicking
        if not clicked:
            print("⌨️ Pressing Enter on compose box...")
            pyautogui.press("enter")

        # Give WhatsApp Web 3 seconds to complete cloud sync with mobile device
        time.sleep(3)

        print("✅ Message automatically sent and synced via WhatsApp Web!")
        return {"status": "success", "provider": "whatsapp_web"}
    except Exception as e:
        print(f"❌ Error during auto-send: {e}")
        return {"status": "error", "error": str(e)}

def ensure_gateway_running() -> bool:
    """Checks if the local WhatsApp gateway is running, and starts it if not."""
    import requests
    try:
        r = requests.get("http://127.0.0.1:3000/status", timeout=2)
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
                r = requests.get("http://127.0.0.1:3000/status", timeout=2)
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
    Sends message via our local WhatsApp Gateway (http://127.0.0.1:3000/send).
    Completely headless, runs 24/7 in the background with no popups and zero fees.
    """
    ensure_gateway_running()
    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO", "")
    clean_phone = "".join(filter(str.isdigit, recipient))

    print(f"📡 Sending via Local WhatsApp Gateway to {clean_phone}...")
    try:
        import requests
        resp = requests.post(
            "http://127.0.0.1:3000/send",
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
        print(f"❌ Could not reach Local Gateway at http://127.0.0.1:3000: {e}")
        return {"status": "error", "error": str(e)}

def send_document_via_gateway(
    file_path: str,
    caption: str = "",
    file_name: str = None,
    to_number: str = None
) -> Dict[str, Any]:
    """
    Sends a PDF or document file via the Local WhatsApp Gateway (POST /send-document).
    Completely silent and headless.
    """
    ensure_gateway_running()
    recipient = to_number or os.getenv("DEAN_WHATSAPP_TO", "")
    clean_phone = "".join(filter(str.isdigit, recipient))

    resolved_name = file_name or os.path.basename(file_path)
    abs_path = os.path.abspath(file_path)

    print(f"📎 Sending document '{resolved_name}' via Local WhatsApp Gateway to {clean_phone}...")
    try:
        import requests
        resp = requests.post(
            "http://127.0.0.1:3000/send-document",
            json={
                "number": clean_phone,
                "filePath": abs_path,
                "fileName": resolved_name,
                "caption": caption,
                "mimetype": "application/pdf"
            },
            timeout=30
        )
        if resp.status_code == 200:
            print("✅ Document successfully delivered to WhatsApp!")
            return {"status": "success", "provider": "local_gateway_document", "data": resp.json()}
        else:
            print(f"⚠️ Gateway returned {resp.status_code}: {resp.text}")
            return {"status": "error", "error": resp.text}
    except Exception as e:
        print(f"❌ Could not reach Local Gateway at http://127.0.0.1:3000/send-document: {e}")
        return {"status": "error", "error": str(e)}



