import os
import threading
import requests
from flask import current_app
from app import db
from app.models import WhatsAppMessage

def send_whatsapp_alert(shop, subject: str, body: str, message_type: str = "alert") -> None:
    """
    Automated WhatsApp Business notification engine for DUNDOO.
    Formats and dispatches notifications via WhatsApp API and logs directly to shop dashboard.
    """
    recipient = getattr(shop, "whatsapp_number", None) or getattr(shop, "phone", None) or os.getenv("DEFAULT_WHATSAPP_NUMBER") or "+919999999999"
    shop_name = getattr(shop, "shop_name", "DUNDOO Shop")
    shopkeeper_name = getattr(shop, "shopkeeper_name", "Member")
    shop_id = getattr(shop, "id", None)

    formatted_msg = f"""⚡ *DUNDOO Automated Alert* ⚡
*Account:* {shop_name} ({shopkeeper_name})
*DUNDOO ID:* #{shop_id or 'System'}
-----------------------------------------
*📌 Subject:* {subject}

{body}

-----------------------------------------
🤖 _Automated by DUNDOO AI Cloud Marketplace_
🌐 https://dundoo-main.onrender.com"""

    # Save to database record so shopkeeper sees it live in their WhatsApp Automation Dashboard
    try:
        if current_app:
            with current_app.app_context():
                record = WhatsAppMessage(
                    shop_id=shop_id,
                    recipient_number=recipient,
                    subject=subject,
                    message_body=formatted_msg,
                    message_type=message_type,
                    status="DELIVERED"
                )
                db.session.add(record)
                db.session.commit()
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error saving WhatsApp alert record: {e}")

    # Dispatch via live external WhatsApp API if configured (Twilio / UltraMsg / Meta API)
    def _async_send():
        print(f"\n[📲 DUNDOO WHATSAPP AUTOMATION TO {recipient}]")
        print(formatted_msg)
        print("--------------------------------------------------\n")

        # Twilio WhatsApp check
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_from = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        if twilio_sid and twilio_token:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                auth = (twilio_sid, twilio_token)
                to_formatted = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
                data = {
                    "From": twilio_from,
                    "To": to_formatted,
                    "Body": formatted_msg
                }
                requests.post(url, data=data, auth=auth, timeout=8.0)
            except Exception as ex:
                print(f"[TWILIO WHATSAPP ERROR] {ex}")
            return

        # UltraMsg API check
        ultramsg_instance = os.getenv("ULTRAMSG_INSTANCE_ID")
        ultramsg_token = os.getenv("ULTRAMSG_TOKEN")
        if ultramsg_instance and ultramsg_token:
            try:
                url = f"https://api.ultramsg.com/{ultramsg_instance}/messages/chat"
                payload = {
                    "token": ultramsg_token,
                    "to": recipient,
                    "body": formatted_msg
                }
                requests.post(url, data=payload, timeout=8.0)
            except Exception as ex:
                print(f"[ULTRAMSG WHATSAPP ERROR] {ex}")

    threading.Thread(target=_async_send, daemon=True).start()
