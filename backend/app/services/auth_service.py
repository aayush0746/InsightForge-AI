import uuid
import secrets
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import SessionLocal, init_db
from backend.app.db.models import UserModel, UserSessionModel
from backend.app.schemas.auth import GoogleAuthRequest, User


class AuthService:
    """
    Hardened Database-Integrated Authentication Service:
    - Cryptographically verified Google OAuth 2.0 ID tokens (no unsigned JWT fallback).
    - Safe email/password signup & signin (rejects duplicate signups and passwordless empty-password bypasses).
    - Verified email OTP login/registration and password reset.
    - Persistent token sessions stored in 'user_sessions'.
    """

    def __init__(self):
        init_db()

    def verify_google_token(self, token_str: str) -> Dict[str, Any]:
        """
        Strictly verifies Google OAuth 2.0 ID token signatures and audience using google-auth.
        Never accepts unsigned or unverified JWT payloads.
        """
        client_id = settings.GOOGLE_CLIENT_ID.strip() if settings.GOOGLE_CLIENT_ID else ""
        if not client_id:
            raise ValueError("Google OAuth is not configured on the server (missing GOOGLE_CLIENT_ID).")

        try:
            req = google_requests.Request()
            idinfo = id_token.verify_oauth2_token(token_str, req, client_id, clock_skew_in_seconds=15)
            if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Invalid Google token issuer.")
            if idinfo.get("email_verified") is False:
                raise ValueError("Google account email is not verified.")
            if not idinfo.get("email"):
                raise ValueError("Google token missing email claim.")
            return idinfo
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Google ID token verification failed: {e}")
            raise ValueError("Invalid or expired Google ID token.")

    def _issue_session(self, db, user_record: UserModel, now: datetime) -> str:
        session_token = secrets.token_urlsafe(48)
        expires_at = now + timedelta(days=settings.SESSION_EXPIRE_DAYS)
        session_record = UserSessionModel(
            token=session_token,
            user_id=user_record.id,
            created_at=now,
            expires_at=expires_at
        )
        db.add(session_record)
        db.commit()
        return session_token

    def authenticate_google(self, payload: GoogleAuthRequest) -> Tuple[User, str]:
        """
        Authenticates via Google OAuth using a cryptographically verified Google ID token.
        """
        raw_token = payload.credential or payload.id_token
        if not raw_token:
            raise ValueError("Verified Google ID token credential is required.")

        verified_claims = self.verify_google_token(raw_token)
        google_id = verified_claims.get("sub")
        email = verified_claims.get("email")
        full_name = verified_claims.get("name") or payload.full_name or payload.name
        profile_picture = verified_claims.get("picture") or payload.profile_picture or payload.avatar_url

        if not email:
            raise ValueError("Google authentication did not provide a verified email address.")

        clean_email = email.lower().strip()
        clean_name = full_name.strip() if full_name else clean_email.split("@")[0].capitalize()

        db = SessionLocal()
        try:
            user_record = None
            if google_id:
                user_record = db.query(UserModel).filter(UserModel.google_id == google_id).first()
            if not user_record:
                user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()

            now = datetime.now(timezone.utc)
            if user_record:
                if google_id and not user_record.google_id:
                    user_record.google_id = google_id
                if profile_picture:
                    user_record.profile_picture = profile_picture
                if clean_name and user_record.full_name != clean_name:
                    user_record.full_name = clean_name
                if not user_record.password_hash:
                    user_record.auth_provider = "google"
                user_record.updated_at = now
                db.commit()
                db.refresh(user_record)
                logger.info(f"Existing user logged in via Google: {clean_email} ({user_record.id})")
            else:
                new_uid = f"usr_{uuid.uuid4().hex[:12]}"
                user_record = UserModel(
                    id=new_uid,
                    full_name=clean_name,
                    email=clean_email,
                    google_id=google_id,
                    profile_picture=profile_picture,
                    auth_provider="google",
                    created_at=now,
                    updated_at=now
                )
                db.add(user_record)
                db.commit()
                db.refresh(user_record)
                logger.info(f"Registered new user via Google SSO: {clean_email} ({new_uid})")

            session_token = self._issue_session(db, user_record, now)
            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Google Auth error: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def signin_email_user(self, email: str, password: Optional[str] = None) -> Tuple[User, str]:
        """
        Signs in an existing user with strict password verification.
        """
        if not password:
            raise ValueError("Password is required.")

        db = SessionLocal()
        try:
            clean_email = email.lower().strip()
            user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if not user_record:
                raise ValueError("Invalid email or password.")

            if not user_record.password_hash:
                raise ValueError(
                    f"This account was registered via {user_record.auth_provider.upper()} without a password. "
                    "Please sign in using Email OTP or Google, or use 'Forgot Password' to set one."
                )

            if not self.verify_password(password, user_record.password_hash):
                raise ValueError("Incorrect password. Please check your credentials or use Forgot Password.")

            now = datetime.now(timezone.utc)
            user_record.updated_at = now
            db.commit()
            db.refresh(user_record)

            session_token = self._issue_session(db, user_record, now)
            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error in signin_email_user: {e}")
            raise
        finally:
            db.close()

    def signup_email_user(self, email: str, name: Optional[str] = None, password: Optional[str] = None) -> Tuple[User, str]:
        """
        Registers a brand-new email/password user.
        Rejects duplicate registrations so existing accounts cannot be overwritten.
        """
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        db = SessionLocal()
        try:
            clean_email = email.lower().strip()
            existing = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if existing:
                raise ValueError("An account with this email already exists. Please Sign In instead.")

            clean_name = name.strip() if name else clean_email.split("@")[0].capitalize()
            now = datetime.now(timezone.utc)
            new_uid = f"usr_{uuid.uuid4().hex[:12]}"
            user_record = UserModel(
                id=new_uid,
                full_name=clean_name,
                email=clean_email,
                password_hash=self.hash_password(password),
                auth_provider="email",
                created_at=now,
                updated_at=now
            )
            db.add(user_record)
            db.commit()
            db.refresh(user_record)
            logger.info(f"New email user registered via Sign Up: {clean_email} ({new_uid})")

            session_token = self._issue_session(db, user_record, now)
            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error in signup_email_user: {e}")
            raise
        finally:
            db.close()

    def complete_otp_login_or_register(
        self,
        email: str,
        otp: str,
        name: Optional[str] = None,
        password: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Verifies a 6-digit OTP and either signs in the existing verified owner
        (without overwriting an existing password) or registers a new user.
        """
        from backend.app.services.email_service import email_service
        clean_email = email.lower().strip()
        email_service.verify_otp(email=clean_email, user_otp=otp)

        if password is not None and len(password) > 0 and len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if user_record:
                user_record.updated_at = now
                if name and name.strip() and (not user_record.full_name or user_record.full_name.startswith("User")):
                    user_record.full_name = name.strip()
                if password and not user_record.password_hash:
                    user_record.password_hash = self.hash_password(password)
                db.commit()
                db.refresh(user_record)
                logger.info(f"Verified OTP login for existing user: {clean_email} ({user_record.id})")
            else:
                clean_name = name.strip() if name and name.strip() else clean_email.split("@")[0].capitalize()
                new_uid = f"usr_{uuid.uuid4().hex[:12]}"
                user_record = UserModel(
                    id=new_uid,
                    full_name=clean_name,
                    email=clean_email,
                    password_hash=self.hash_password(password) if password else None,
                    auth_provider="email",
                    created_at=now,
                    updated_at=now
                )
                db.add(user_record)
                db.commit()
                db.refresh(user_record)
                logger.info(f"Verified OTP signup for new user: {clean_email} ({new_uid})")

            session_token = self._issue_session(db, user_record, now)
            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error in complete_otp_login_or_register: {e}")
            raise
        finally:
            db.close()

    def verify_otp_and_register_user(
        self,
        email: str,
        otp: str,
        name: Optional[str] = None,
        password: Optional[str] = None
    ) -> Tuple[User, str]:
        """Compatibility wrapper calling complete_otp_login_or_register."""
        return self.complete_otp_login_or_register(email=email, otp=otp, name=name, password=password)

    def reset_password_with_otp(self, email: str, otp: str, new_password: str) -> Tuple[User, str]:
        """
        Validates the 6-digit OTP code, updates password hash, invalidates prior sessions,
        and issues a fresh session token.
        """
        from backend.app.services.email_service import email_service
        if not new_password or len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")

        clean_email = email.lower().strip()
        email_service.verify_otp(email=clean_email, user_otp=otp)

        db = SessionLocal()
        try:
            user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if not user_record:
                raise ValueError("No account found with this email.")

            now = datetime.now(timezone.utc)
            user_record.password_hash = self.hash_password(new_password)
            user_record.updated_at = now
            # Revoke previous sessions for safety on password reset
            db.query(UserSessionModel).filter(UserSessionModel.user_id == user_record.id).delete()
            db.commit()
            db.refresh(user_record)

            session_token = self._issue_session(db, user_record, now)
            logger.info(f"Password reset successfully for user: {clean_email} ({user_record.id})")
            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error resetting password: {e}")
            raise
        finally:
            db.close()

    def get_user_by_session_token(self, token: str) -> Optional[User]:
        if not token:
            return None

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            session_record = db.query(UserSessionModel).filter(
                UserSessionModel.token == token
            ).first()

            if not session_record:
                return None

            exp = session_record.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)

            if exp < now:
                db.delete(session_record)
                db.commit()
                return None

            user_record = session_record.user
            if not user_record:
                return None

            return User(**user_record.to_dict())
        except Exception as e:
            logger.error(f"Error fetching user by session token: {e}")
            return None
        finally:
            db.close()

    def logout_session(self, token: str) -> bool:
        if not token:
            return False

        db = SessionLocal()
        try:
            session_record = db.query(UserSessionModel).filter(
                UserSessionModel.token == token
            ).first()
            if session_record:
                db.delete(session_record)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error logging out session: {e}")
            return False
        finally:
            db.close()


auth_service = AuthService()
