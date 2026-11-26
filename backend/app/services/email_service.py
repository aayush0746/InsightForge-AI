import hashlib
import hmac
import html
import secrets
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import EmailOtpModel
from backend.app.db.session import SessionLocal, init_db


class EmailService:
    """
    SQL-backed Email & OTP Verification Service:
    - Generates cryptographically secure 6-digit verification codes.
    - Stores HMAC-SHA256 OTP hashes in SQL (email_otps) so multi-worker/restarts work.
    - Sends styled, XSS-escaped HTML emails via SMTP when configured.
    - Supports explicit local development mode fallback when SMTP is not configured.
    """

    def __init__(self):
        init_db()

    @staticmethod
    def _hash_otp(email: str, otp_code: str) -> str:
        secret = settings.SESSION_SECRET.encode("utf-8")
        msg = f"{email.lower().strip()}:{otp_code.strip()}".encode("utf-8")
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()

    def generate_and_send_otp(
        self,
        email: str,
        name: Optional[str] = None,
        purpose: str = "signup"
    ) -> Dict[str, Any]:
        clean_email = email.lower().strip()
        display_name = name.strip() if name else clean_email.split("@")[0].capitalize()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10)
        otp_code = str(secrets.randbelow(900000) + 100000)
        otp_hash = self._hash_otp(clean_email, otp_code)

        db = SessionLocal()
        try:
            existing = db.query(EmailOtpModel).filter(EmailOtpModel.email == clean_email).first()
            if existing:
                existing.otp_hash = otp_hash
                existing.name = display_name[:120]
                existing.purpose = purpose[:40]
                existing.attempts = 0
                existing.expires_at = expires_at
                existing.created_at = now
            else:
                db.add(EmailOtpModel(
                    email=clean_email,
                    otp_hash=otp_hash,
                    name=display_name[:120],
                    purpose=purpose[:40],
                    attempts=0,
                    expires_at=expires_at,
                    created_at=now,
                ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist OTP record for {clean_email}: {e}")
            raise ValueError("Unable to initialize verification code. Please try again.")
        finally:
            db.close()

        is_prod = settings.APP_ENV.lower() == "production"
        if not is_prod:
            border = "=" * 62
            logger.info(
                f"\n{border}\n"
                f" [INSIGHTFORGE AUTH] LOCAL DEV EMAIL OTP CODE\n"
                f" To       : {clean_email} ({display_name})\n"
                f" Purpose  : {purpose.upper()}\n"
                f" OTP Code : {otp_code}\n"
                f" Validity : 10 minutes (Expires: {expires_at.strftime('%H:%M:%S UTC')})\n"
                f"{border}"
            )

        smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)
        if smtp_configured:
            try:
                self._send_smtp_email(
                    to_email=clean_email,
                    to_name=display_name,
                    otp_code=otp_code,
                )
                return {
                    "success": True,
                    "message": f"A 6-digit verification code has been sent to {clean_email}. Please check your inbox.",
                    "smtp_delivered": True,
                }
            except Exception as e:
                logger.error(f"SMTP dispatch to {clean_email} failed: {e}")
                if is_prod:
                    raise ValueError(
                        f"Could not send verification email to {clean_email}. "
                        "Please verify your email address or check back in a moment."
                    )
                logger.warning("SMTP failed in development mode; returning dev_otp fallback.")
                return {
                    "success": True,
                    "message": f"SMTP unavailable in local dev mode. Use the verification code shown below for {clean_email}.",
                    "smtp_delivered": False,
                    "dev_otp": otp_code,
                }

        if is_prod:
            logger.error("[InsightForge Auth] SMTP credentials missing in production.")
            raise ValueError("Email verification service is not configured on this server.")

        return {
            "success": True,
            "message": f"Local development mode: 6-digit verification code generated for {clean_email}.",
            "smtp_delivered": False,
            "dev_otp": otp_code,
        }

    def verify_otp(self, email: str, user_otp: str) -> bool:
        """
        Validates OTP code against SQL-stored HMAC hash with expiration and attempt limits.
        """
        clean_email = email.lower().strip()
        db = SessionLocal()
        try:
            record = db.query(EmailOtpModel).filter(EmailOtpModel.email == clean_email).first()
            if not record:
                raise ValueError("No verification code found for this email. Please request a new code.")

            now = datetime.now(timezone.utc)
            exp = record.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)

            if now > exp:
                db.delete(record)
                db.commit()
                raise ValueError("Verification code has expired. Please request a new code.")

            if (record.attempts or 0) >= 5:
                db.delete(record)
                db.commit()
                raise ValueError("Too many failed attempts. Please request a new verification code.")

            expected_hash = record.otp_hash
            candidate_hash = self._hash_otp(clean_email, user_otp)
            if not hmac.compare_digest(expected_hash, candidate_hash):
                record.attempts = (record.attempts or 0) + 1
                remaining = 5 - record.attempts
                if remaining <= 0:
                    db.delete(record)
                    db.commit()
                    raise ValueError("Too many failed attempts. Please request a new verification code.")
                db.commit()
                raise ValueError(f"Invalid verification code. {remaining} attempt(s) remaining.")

            db.delete(record)
            db.commit()
            logger.info(f"OTP successfully verified for {clean_email}")
            return True
        finally:
            db.close()

    def _send_smtp_email(self, to_email: str, to_name: str, otp_code: str) -> bool:
        """
        Transmits HTML verification email using configured SMTP provider.
        """
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        from_name = settings.SMTP_FROM_NAME or "InsightForge AI"
        safe_name = html.escape(to_name)
        safe_otp = html.escape(otp_code)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"InsightForge AI verification OTP is {otp_code}"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        text_content = (
            f"Hello {to_name},\n\n"
            f"InsightForge AI verification OTP is: {otp_code}\n\n"
            f"Use this 6-digit verification code to complete your InsightForge AI verification.\n"
            f"This code will expire in 10 minutes.\n\n"
            f"If you did not request this, please ignore this email."
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 24px; color: #f8fafc; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .logo {{ font-size: 20px; font-weight: bold; color: #818cf8; margin-bottom: 24px; }}
            .code-box {{ background: #0f172a; border-radius: 12px; padding: 20px; text-align: center; margin: 28px 0; border: 1px solid #4f46e5; }}
            .otp-code {{ font-size: 34px; letter-spacing: 8px; font-weight: 800; color: #ffffff; font-family: monospace; }}
            .footer {{ font-size: 12px; color: #94a3b8; margin-top: 32px; border-top: 1px solid #334155; padding-top: 16px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="logo">InsightForge AI</div>
            <h2 style="color: #ffffff; margin-top: 0;">Verify Your Email Address</h2>
            <p>Hello {safe_name},</p>
            <p>Your InsightForge AI verification code is:</p>
            <div class="code-box">
              <div class="otp-code">{safe_otp}</div>
            </div>
            <p style="color: #cbd5e1; font-size: 13px;">Use this 6-digit verification code to complete your action. This code expires in <strong>10 minutes</strong>. Do not share this code with anyone.</p>
            <div class="footer">
              If you didn't request this code, you can safely ignore this email.
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        smtp_password = settings.SMTP_PASSWORD.replace(" ", "") if settings.SMTP_PASSWORD else ""
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            server.starttls()

        server.login(settings.SMTP_USER, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent OTP email to {to_email} via SMTP.")
        return True


email_service = EmailService()
