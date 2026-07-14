import os
import random
import smtplib
from email.mime.text import MIMEText

from flask import session, current_app

from app import db
from app.models import OTPRequest
from app.config import Config



def generate_otp() -> str:
    """Generate a 6-digit OTP as string."""
    return str(random.randint(100000, 999999))


def is_valid_email(email: str) -> bool:
    """Very basic email check."""
    return "@" in email and "." in email



def send_email_otp(to_email: str, otp: str, name: str) -> bool:
    """Send OTP email using Gmail credentials from Config."""
    body = f"Hi {name},\n\nYour OTP is: {otp}\nIt expires in 5 minutes."

    msg = MIMEText(body)
    msg["Subject"] = "Your OTP Verification"
    msg["From"] = Config.EMAIL_USER
    msg["To"] = to_email

    try:
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(Config.EMAIL_USER, Config.EMAIL_PASS)
        server.sendmail(Config.EMAIL_USER, to_email, msg.as_string())
        server.quit()
        print("[OTP EMAIL SENT] to", to_email)
        return True
    except Exception as e:
        print("Email sending failed:", e)
        return False


def start_otp_flow(context: str, email: str, name: str, payload: dict) -> bool:
    """
    Create OTPRequest in DB, store its id in session, send email.
    context: 'user_register', 'shop_login', etc.
    """
    otp = generate_otp()

    
    req = OTPRequest(email=email, otp_code=otp, context=context, payload=payload)
    db.session.add(req)
    db.session.commit()

    
    session["otp_record_id"] = req.id

    
    send_email_otp(email, otp, name)
    return True


def get_current_record():
    otp_id = session.get("otp_record_id")
    if not otp_id:
        return None
    return OTPRequest.query.get(otp_id)


def verify_otp(submitted_code: str, expected_context: str):
    """
    Verify OTP value + context.
    Returns (ok: bool, data_or_error: dict|str)
    """
    record = get_current_record()
    if not record:
        return False, "No OTP session active."

    if record.context != expected_context:
        return False, "Wrong OTP context."

    if record.otp_code != submitted_code:
        return False, "Invalid OTP."

    data = {"email": record.email, "payload": record.payload}

    
    db.session.delete(record)
    db.session.commit()
    session.pop("otp_record_id", None)

    return True, data




def send_inventory_email(to_email: str, subject: str, body: str) -> None:
    """
    Generic email sender for inventory alerts (low stock / expiry).
    SAFE: if SMTP is not configured or sending fails, it just logs and returns.

    Uses env variables:
        SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

    If those are missing, it falls back to Config.EMAIL_USER/PASS (same Gmail as OTP).
    """

   
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))  
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    
    if not smtp_host:
        smtp_host = "smtp.gmail.com"
    if not smtp_user:
        smtp_user = Config.EMAIL_USER
    if not smtp_pass:
        smtp_pass = Config.EMAIL_PASS

    
    if not smtp_user or not smtp_pass:
        current_app.logger.warning(
            "Inventory email NOT sent: SMTP configuration missing "
            "(set SMTP_* env or Config.EMAIL_USER/EMAIL_PASS)."
        )
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        current_app.logger.info("Inventory email sent to %s", to_email)
    except Exception as e:
        current_app.logger.error("Failed to send inventory email: %s", e)
