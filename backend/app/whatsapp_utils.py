import os
import threading
import requests
from flask import current_app
from app import db
from app.models import WhatsAppMessage

def send_whatsapp_alert(target, subject: str, body: str, message_type: str = "alert") -> None:
    """
    Automated WhatsApp Business notification engine for DUNDOO.
    Formats and dispatches notifications via WhatsApp API to Shopkeepers and Users.
    """
    if isinstance(target, str):
        recipient = target
        account_name = "Customer / Member"
        target_id = None
        shop_id = None
    else:
        recipient = getattr(target, "whatsapp_number", None) or getattr(target, "phone", None) or os.getenv("DEFAULT_WHATSAPP_NUMBER") or "+919876543210"
        if hasattr(target, "shop_name"):
            account_name = f"{getattr(target, 'shop_name', 'DUNDOO Shop')} ({getattr(target, 'shopkeeper_name', 'Member')})"
            target_id = getattr(target, "id", None)
            shop_id = target_id
        else:
            account_name = f"User ({getattr(target, 'username', 'Customer')})"
            target_id = getattr(target, "id", None)
            shop_id = None

    formatted_msg = f"""⚡ *DUNDOO Automated Alert* ⚡
*Recipient:* {account_name}
*DUNDOO ID:* #{target_id or 'System'}
-----------------------------------------
*📌 Subject:* {subject}

{body}

-----------------------------------------
🤖 _Automated by DUNDOO AI Cloud Marketplace_
🌐 https://dundoo-main.onrender.com"""

    # Save to database record
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

    # Dispatch via live external WhatsApp API if configured (CallMeBot / Twilio / UltraMsg / Meta API)
    def _async_send():
        print(f"\n[📲 DUNDOO WHATSAPP AUTOMATION TO {recipient}]")
        print(formatted_msg)
        print("--------------------------------------------------\n")

        # 1. CallMeBot Free WhatsApp API check
        callmebot_key = os.getenv("CALLMEBOT_API_KEY")
        if callmebot_key:
            try:
                phone_clean = ''.join(filter(str.isdigit, str(recipient)))
                url = f"https://api.callmebot.com/whatsapp.php?phone={phone_clean}&text={requests.utils.quote(formatted_msg)}&apikey={callmebot_key}"
                requests.get(url, timeout=8.0)
                print(f"[CALLMEBOT WHATSAPP SENT TO {phone_clean}]")
            except Exception as ex:
                print(f"[CALLMEBOT WHATSAPP ERROR] {ex}")

        # 2. Twilio WhatsApp check
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_from = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        if twilio_sid and twilio_token:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                auth = (twilio_sid, twilio_token)
                to_formatted = recipient if str(recipient).startswith("whatsapp:") else f"whatsapp:{recipient}"
                data = {
                    "From": twilio_from,
                    "To": to_formatted,
                    "Body": formatted_msg
                }
                requests.post(url, data=data, auth=auth, timeout=8.0)
            except Exception as ex:
                print(f"[TWILIO WHATSAPP ERROR] {ex}")
            return

        # 3. UltraMsg API check
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

        # 4. Meta Cloud API check
        meta_token = os.getenv("META_WHATSAPP_TOKEN")
        meta_phone_id = os.getenv("META_PHONE_NUMBER_ID")
        if meta_token and meta_phone_id:
            try:
                url = f"https://graph.facebook.com/v18.0/{meta_phone_id}/messages"
                headers = {
                    "Authorization": f"Bearer {meta_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": ''.join(filter(str.isdigit, str(recipient))),
                    "type": "text",
                    "text": {"body": formatted_msg}
                }
                requests.post(url, json=payload, headers=headers, timeout=8.0)
            except Exception as ex:
                print(f"[META WHATSAPP ERROR] {ex}")

    threading.Thread(target=_async_send, daemon=True).start()
