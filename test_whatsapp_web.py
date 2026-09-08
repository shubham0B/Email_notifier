import os
import urllib.parse
import webbrowser
from dotenv import load_dotenv

load_dotenv()

phone = os.getenv("DEAN_WHATSAPP_TO", "+917378020506").replace("whatsapp:", "").replace(" ", "").replace("+", "")

test_msg = (
    "🏛️ *DEAN'S EMAIL AUTOMATION - TEST MESSAGE*\n\n"
    "✅ WhatsApp Web integration is working!\n"
    "📬 Your daily email digests with arrival timestamps and Gemini AI summaries will be delivered here."
)

print(f"Opening WhatsApp Web to send test to: +{phone}...")

try:
    import pywhatkit
    pywhatkit.sendwhatmsg_instantly(
        phone_no=f"+{phone}",
        message=test_msg,
        wait_time=15,
        tab_close=False
    )
    print("✅ WhatsApp Web launched and test message sent!")
except Exception as e:
    print(f"Note: {e}")
    # Fallback: direct browser link
    encoded_text = urllib.parse.quote(test_msg)
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
    print(f"Opening browser link: {url}")
    webbrowser.open(url)
