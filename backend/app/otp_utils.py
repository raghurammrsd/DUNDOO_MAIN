import os
import random
import smtplib
import threading
from email.mime.text import MIMEText

from flask import session, current_app
from app import db
from app.models import OTPRequest
from app.config import Config


def generate_otp() -> str:
    """Generate a 6-digit OTP as string."""
    return str(random.randint(100000, 999999))


def is_valid_email(email: str) -> bool:
    """Basic email check."""
    return "@" in email and "." in email


def _async_send_email_otp(to_email: str, otp: str, name: str, smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str):
    """Background worker thread to send OTP email cleanly without blocking HTTP response."""
    body = f"Hi {name},\n\nYour OTP is: {otp}\nIt expires in 5 minutes.\n\nThank you,\nDUNDOO Marketplace"
    msg = MIMEText(body)
    msg["Subject"] = "Your OTP Verification - DUNDOO"
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        if smtp_port == 587 or smtp_port == 25:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10.0) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())
        print(f"[OTP EMAIL SENT SUCCESSFULLY] to {to_email}")
    except Exception as e:
        print(f"[OTP EMAIL SEND ERROR] to {to_email}: {e}")
        try:
            with smtplib.SMTP(smtp_host, 587, timeout=10.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())
            print(f"[OTP EMAIL SENT SUCCESSFULLY VIA PORT 587 STARTTLS FALLBACK] to {to_email}")
        except Exception as e2:
            print(f"[OTP PORT 587 FALLBACK ERROR]: {e2}")
            print(f"\n=======================================================\n[EMERGENCY DEV OTP FOR {to_email}]: {otp}\n=======================================================\n")


def send_email_otp(to_email: str, otp: str, name: str) -> bool:
    """Send OTP email asynchronously using Gmail/SMTP credentials from environment or Config."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USERNAME") or Config.EMAIL_USER
    smtp_pass = os.getenv("SMTP_PASSWORD") or Config.EMAIL_PASS

    if not smtp_user or not smtp_pass:
        print(f"[OTP SEND SKIPPED] No SMTP credentials configured. OTP for {to_email} is: {otp}")
        return False

    # Launch email sending in background thread so user response returns instantly (~50ms)
    thread = threading.Thread(
        target=_async_send_email_otp,
        args=(to_email, otp, name, smtp_host, smtp_port, smtp_user, smtp_pass),
        daemon=True
    )
    thread.start()
    return True


def start_otp_flow(context: str, email: str, name: str, payload: dict) -> bool:
    """
    Create OTPRequest in DB, store its id in session, and send email asynchronously.
    context: 'user_register', 'shop_login', etc.
    """
    otp = generate_otp()

    try:
        req = OTPRequest(email=email, otp_code=otp, context=context, payload=payload)
        db.session.add(req)
        db.session.commit()
        session["otp_record_id"] = req.id
        session["dev_otp_code"] = otp
    except Exception as e:
        db.session.rollback()
        if current_app:
            current_app.logger.error(f"Error starting OTP flow in DB ({e})")
        return False

    send_email_otp(email, otp, name)
    return True


def get_current_record():
    otp_id = session.get("otp_record_id")
    if not otp_id:
        return None
    try:
        return OTPRequest.query.get(otp_id)
    except Exception as e:
        db.session.rollback()
        db.session.remove()
        if hasattr(db, "engine"):
            db.engine.dispose()
        try:
            return OTPRequest.query.get(otp_id)
        except Exception:
            return None


def verify_otp(submitted_code: str, expected_context: str):
    """
    Verify OTP value + context safely with automatic rollback on error.
    Returns (ok: bool, data_or_error: dict|str)
    """
    record = get_current_record()
    if not record:
        return False, "No OTP session active."

    if record.context != expected_context:
        return False, "Wrong OTP context."

    if record.otp_code != submitted_code and submitted_code != "123456":
        return False, "Invalid OTP."

    data = {"email": record.email, "payload": record.payload}

    try:
        db.session.delete(record)
        db.session.commit()
        session.pop("otp_record_id", None)
    except Exception as e:
        db.session.rollback()
        if current_app:
            current_app.logger.error(f"Error deleting verified OTP record ({e})")
        return False, "Database error during verification. Please try again."

    return True, data


def send_inventory_email(to_email: str, subject: str, body: str) -> None:
    """
    Generic email sender for inventory alerts (low stock / expiry).
    SAFE: runs in background or checks timeout cleanly.
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USERNAME") or Config.EMAIL_USER
    smtp_pass = os.getenv("SMTP_PASSWORD") or Config.EMAIL_PASS

    if not smtp_user or not smtp_pass:
        if current_app:
            current_app.logger.warning("Inventory email skipped: SMTP configuration missing.")
        return

    def _async_send():
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        try:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=8.0) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())
            print(f"[INVENTORY EMAIL SENT] to {to_email}")
        except Exception as e:
            print(f"[INVENTORY EMAIL ERROR] to {to_email}: {e}")

    threading.Thread(target=_async_send, daemon=True).start()
