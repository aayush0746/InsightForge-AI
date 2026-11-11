import os
import smtplib
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.core.logger import logger

class EmailService:
    """
    Email & OTP Verification Service:
    - Generates cryptographically secure 6-digit verification codes.
    - Sends styled verification emails via SMTP (e.g. Gmail SMTP or custom host).
    - Logs OTP to console for instant local development & testing.
    - Manages expiration and verification logic.
    """

    def __init__(self):
        # In-memory store: { email: { "otp": "...", "expires_at": datetime, "name": "...", "attempts": 0 } }
        self._otp_store: Dict[str, Dict[str, Any]] = {}

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

        # Generate secure 6-digit OTP code
        otp_code = str(secrets.randbelow(900000) + 100000)

        # Store in memory
        self._otp_store[clean_email] = {
            "otp": otp_code,
            "name": display_name,
            "purpose": purpose,
            "expires_at": expires_at,
            "attempts": 0,
            "created_at": now
        }

        # Check if SMTP is configured for real inbox delivery
        if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
            logger.warning(
                f"[InsightForge Auth] SMTP credentials not configured in .env. Cannot deliver email to {clean_email}."
            )
            # Log OTP to server terminal for backup
            border = "=" * 62
            logger.info(
                f"\n{border}\n"
                f" [INSIGHTFORGE AUTH] EMAIL OTP CODE (Terminal Backup)\n"
                f" To       : {clean_email} ({display_name})\n"
                f" Purpose  : {purpose.upper()}\n"
                f" OTP Code : {otp_code}\n"
                f" Validity : 10 minutes (Expires: {expires_at.strftime('%H:%M:%S UTC')})\n"
                f"{border}"
            )
            raise ValueError(
                "Email delivery is not configured. Please add SMTP_USER and SMTP_PASSWORD to your .env file so InsightForge AI can send the verification code to your email."
            )

        # Send real verification email via SMTP
        try:
            self._send_smtp_email(
                to_email=clean_email,
                to_name=display_name,
                otp_code=otp_code
            )
        except Exception as e:
            logger.error(f"SMTP dispatch to {clean_email} failed: {e}")
            raise ValueError(
                f"Failed to deliver verification email to {clean_email}: {str(e)}. Please check your SMTP settings in .env."
            )

        return {
            "success": True,
            "message": f"Verification code has been sent to {clean_email}. Please check your inbox.",
            "smtp_delivered": True
        }

    def verify_otp(self, email: str, user_otp: str) -> bool:
        """
        Validates OTP code against the store with expiration check.
        """
        clean_email = email.lower().strip()
        record = self._otp_store.get(clean_email)
        if not record:
            raise ValueError("No verification code found for this email. Please request a new code.")

        now = datetime.now(timezone.utc)
        if now > record["expires_at"]:
            self._otp_store.pop(clean_email, None)
            raise ValueError("Verification code has expired. Please request a new code.")

        if record.get("attempts", 0) >= 5:
            self._otp_store.pop(clean_email, None)
            raise ValueError("Too many failed attempts. Please request a new verification code.")

        # Check code
        if record["otp"].strip() != user_otp.strip():
            record["attempts"] = record.get("attempts", 0) + 1
            remaining = 5 - record["attempts"]
            raise ValueError(f"Invalid verification code. {remaining} attempt(s) remaining.")

        # Validated: Remove from store to prevent reuse
        self._otp_store.pop(clean_email, None)
        logger.info(f"OTP successfully verified for {clean_email}")
        return True

    def _send_smtp_email(self, to_email: str, to_name: str, otp_code: str) -> bool:
        """
        Transmits HTML verification email using configured SMTP provider.
        """
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        from_name = settings.SMTP_FROM_NAME or "InsightForge AI"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"InsightForge AI verification OTP is {otp_code}"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        text_content = (
            f"Hello {to_name},\n\n"
            f"InsightForge AI verification OTP is: {otp_code}\n\n"
            f"Use this 6-digit verification code to complete your InsightForge AI registration.\n"
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
            <div class="logo">✨ InsightForge AI</div>
            <h2 style="color: #ffffff; margin-top: 0;">Verify Your Email Address</h2>
            <p>Hello {to_name},</p>
            <p>InsightForge AI verification OTP is:</p>
            <div class="code-box">
              <div class="otp-code">{otp_code}</div>
            </div>
            <p style="color: #cbd5e1; font-size: 13px;">Use this 6-digit verification code to complete your registration. This code expires in <strong>10 minutes</strong>. Do not share this code with anyone.</p>
            <div class="footer">
              If you didn't create an account with InsightForge AI, you can safely ignore this email.
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Connect to SMTP server
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent OTP email to {to_email} via SMTP.")
        return True

email_service = EmailService()

