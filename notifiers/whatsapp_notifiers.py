from datetime import datetime, timedelta
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from twilio.rest import Client

from configurations.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    TWILIO_WHATSAPP_TO,
    BITLY_ACCESS_TOKEN,  # ensure it's added in your config
)

load_dotenv()  # Ensure environment variables are loaded

# ---------------------------------------------------------
# 🔹 Rate Limiting Config
# ---------------------------------------------------------
NOTIFICATION_COOLDOWN = timedelta(minutes=15)  # Minimum gap between alerts per sender
notification_cache = {}  # sender_email -> last_sent_time


def can_send_notification(sender: str) -> bool:
    """Check if a notification can be sent (rate limiting per sender)."""
    now = datetime.now()
    last_sent = notification_cache.get(sender)

    if last_sent and now - last_sent < NOTIFICATION_COOLDOWN:
        print(f"[RateLimit] ⚠️ Skipping duplicate alert for {sender} (cooldown active).")
        return False

    notification_cache[sender] = now
    return True


# ---------------------------------------------------------
# 🔹 Helper: Generate Short Gmail Links (Bitly)
# ---------------------------------------------------------
def shorten_gmail_link(subject: str):
    """Generate a Bitly short link to Gmail search for this subject."""
    if not BITLY_ACCESS_TOKEN:
        print("[Bitly] ⚠️ Missing BITLY_ACCESS_TOKEN, skipping link shortening.")
        return None

    try:
        # Encode subject safely for Gmail query
        encoded_subject = quote_plus(subject)
        gmail_web_link = f"https://mail.google.com/mail/u/0/#search/{encoded_subject}"

        response = requests.post(
            "https://api-ssl.bitly.com/v4/shorten",
            headers={
                "Authorization": f"Bearer {BITLY_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"long_url": gmail_web_link},
        )
        response.raise_for_status()
        short_url = response.json().get("link")
        print(f"[Bitly] 🔗 Short Gmail link generated: {short_url}")
        return short_url
    except Exception as e:
        print(f"[Bitly] ❌ Failed to shorten link: {e}")
        return None


# ---------------------------------------------------------
# 🔹 Send WhatsApp Notification via Twilio
# ---------------------------------------------------------
def send_whatsapp_message(subject: str, sender: str, priority: str, snippet: str, received_time: str = None):
    """Send WhatsApp message via Twilio for high-priority emails."""
    print("[Twilio] Preparing WhatsApp notification...")

    # Validate credentials
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO]):
        print("[Twilio] ⚠️ Missing Twilio credentials in environment variables.")
        return

    if not can_send_notification(sender):
        return

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Generate Gmail link (Bitly short link)
        gmail_short_link = shorten_gmail_link(subject)

        # Truncate long email snippets
        MAX_BODY_LENGTH = 600
        truncated = snippet[:MAX_BODY_LENGTH] + (
            "\n\n...(truncated preview)" if len(snippet) > MAX_BODY_LENGTH else ""
        )

        # 📨 WhatsApp Message Template
        body = (
            "🚨 *High Priority Email Alert*\n\n"
            f"📧 *From:* {sender}\n"
            f"🗒️ *Subject:* {subject}\n"
            f"⚡ *Priority:* {priority}\n\n"
            f"📝 *Body Preview:*\n{truncated}\n\n"
            f"📅 *Received:* {received_time or datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
        )

        if gmail_short_link:
            body += f"\n📨 *Open in Gmail (App / Web):* {gmail_short_link}\n"

        body += "\n🔕 Reply STOP to mute alerts temporarily."

        # Send WhatsApp Message
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=body,
            to=TWILIO_WHATSAPP_TO
        )

        print(f"[Twilio] ✅ WhatsApp notification sent successfully (SID: {message.sid})\n")

    except Exception as e:
        print(f"[Twilio] ❌ Failed to send WhatsApp message: {e}")


# ---------------------------------------------------------
# 🛑 Sandbox Expiry Notifier (SAME WhatsApp)
# ---------------------------------------------------------
def send_sandbox_expiry_notification():
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    body = (
        "⚠️ *WhatsApp Sandbox Expired*\n\n"
        "Your WhatsApp sandbox session has expired.\n\n"
        "Please re-enable notifications:\n"
        "1️⃣ Open WhatsApp\n"
        "2️⃣ Send the JOIN code shown in Twilio Console\n"
        "3️⃣ Send it to +14155238886\n\n"
        "🔄 Alerts will resume automatically after rejoining."
    )

    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=TWILIO_WHATSAPP_TO,
        body=body,
    )
