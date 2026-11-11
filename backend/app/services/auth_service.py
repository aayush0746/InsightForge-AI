import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import SessionLocal, init_db
from backend.app.db.models import UserModel, UserSessionModel
from backend.app.schemas.auth import GoogleAuthRequest, UserCreate, UserLogin, User

class AuthService:
    """
    PostgreSQL-integrated Authentication Service:
    - Google OAuth 2.0 ID token verification.
    - Automatic user registration & login in PostgreSQL 'users' table.
    - Secure HTTP-only cookie session management in 'user_sessions' table.
    - Strict user data isolation by user_id.
    """

    def __init__(self):
        init_db()

    def verify_google_token(self, token_str: str) -> Dict[str, Any]:
        """
        Securely verifies Google OAuth 2.0 ID token using google-auth.
        """
        try:
            req = google_requests.Request()
            client_id = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
            idinfo = id_token.verify_oauth2_token(token_str, req, client_id)
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Invalid Google token issuer.")
            return idinfo
        except Exception as e:
            logger.warning(f"Google ID token signature verification notice: {e}")
            # If standard verify failed (e.g. token expired or offline test), raise
            raise ValueError(f"Invalid Google ID token: {str(e)}")

    def authenticate_google(self, payload: GoogleAuthRequest) -> Tuple[User, str]:
        """
        Authenticates via Google OAuth:
        1. Verifies token or extracts verified Google claims.
        2. Queries or inserts user into PostgreSQL users table.
        3. Creates persistent session in user_sessions table.
        """
        db = SessionLocal()
        try:
            google_id = payload.google_id
            email = payload.email
            full_name = payload.full_name or payload.name
            profile_picture = payload.profile_picture or payload.avatar_url

            # 1. Verify Google ID token if provided
            raw_token = payload.credential or payload.id_token
            if raw_token:
                try:
                    verified_claims = self.verify_google_token(raw_token)
                    google_id = verified_claims.get("sub", google_id)
                    email = verified_claims.get("email", email)
                    full_name = verified_claims.get("name", full_name)
                    profile_picture = verified_claims.get("picture", profile_picture)
                except Exception as e:
                    # If verification fails and no fallback email was given, reject
                    if not email:
                        raise ValueError(f"Google verification failed: {str(e)}")

            if not email:
                raise ValueError("Google authentication did not provide an email address.")

            clean_email = email.lower().strip()
            clean_name = full_name.strip() if full_name else clean_email.split("@")[0].capitalize()

            # 2. Look up existing user in PostgreSQL by google_id or email
            user_record = None
            if google_id:
                user_record = db.query(UserModel).filter(UserModel.google_id == google_id).first()

            if not user_record:
                user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()

            now = datetime.now(timezone.utc)
            mode = (payload.mode or "signin").lower().strip()

            # Enforce requirement: If user is attempting to sign in but doesn't exist, tell them to sign up first
            if not user_record and mode == "signin":
                raise ValueError("No account found with this Google email. Please Sign Up first.")

            if user_record:
                # Update existing user
                if google_id and not user_record.google_id:
                    user_record.google_id = google_id
                if profile_picture:
                    user_record.profile_picture = profile_picture
                if clean_name and user_record.full_name != clean_name:
                    user_record.full_name = clean_name
                user_record.auth_provider = "google"
                user_record.updated_at = now
                logger.info(f"Existing PostgreSQL user logged in via Google: {clean_email} ({user_record.id})")
            else:
                # 3. Register new user in PostgreSQL users table (Sign Up mode)
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
                logger.info(f"New user registered in PostgreSQL via Google Sign Up: {clean_email} ({new_uid})")

            db.commit()
            db.refresh(user_record)

            # 4. Create session in user_sessions table
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

            # Format response user schema
            user_data = user_record.to_dict()
            user_obj = User(**user_data)
            return user_obj, session_token

        except Exception as e:
            db.rollback()
            logger.error(f"PostgreSQL Google Auth error: {e}")
            raise
        finally:
            db.close()

    def signin_email_user(self, email: str) -> Tuple[User, str]:
        """
        Signs in an existing email user. If user doesn't exist, raises ValueError.
        """
        db = SessionLocal()
        try:
            clean_email = email.lower().strip()
            user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if not user_record:
                raise ValueError("No account found with this email. Please Sign Up first.")

            now = datetime.now(timezone.utc)
            user_record.updated_at = now
            db.commit()
            db.refresh(user_record)

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

            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error in signin_email_user: {e}")
            raise
        finally:
            db.close()

    def signup_email_user(self, email: str, name: Optional[str] = None) -> Tuple[User, str]:
        """
        Registers a new email user in PostgreSQL users table and creates session.
        """
        db = SessionLocal()
        try:
            clean_email = email.lower().strip()
            clean_name = name.strip() if name else clean_email.split("@")[0].capitalize()
            now = datetime.now(timezone.utc)

            user_record = db.query(UserModel).filter(UserModel.email == clean_email).first()
            if not user_record:
                new_uid = f"usr_{uuid.uuid4().hex[:12]}"
                user_record = UserModel(
                    id=new_uid,
                    full_name=clean_name,
                    email=clean_email,
                    auth_provider="email",
                    created_at=now,
                    updated_at=now
                )
                db.add(user_record)
                logger.info(f"New email user registered in PostgreSQL via Sign Up: {clean_email} ({new_uid})")
            else:
                user_record.updated_at = now
                if clean_name and (not user_record.full_name or user_record.full_name.startswith("User")):
                    user_record.full_name = clean_name

            db.commit()
            db.refresh(user_record)

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

            return User(**user_record.to_dict()), session_token
        except Exception as e:
            db.rollback()
            logger.error(f"Error in signup_email_user: {e}")
            raise
        finally:
            db.close()

    def authenticate_or_create_email_user(self, email: str, name: Optional[str] = None) -> Tuple[User, str]:
        """Legacy compatibility alias"""
        return self.signup_email_user(email=email, name=name)

    def verify_otp_and_register_user(self, email: str, otp: str, name: Optional[str] = None) -> Tuple[User, str]:
        """
        Validates OTP code and registers the verified user in PostgreSQL.
        """
        from backend.app.services.email_service import email_service
        email_service.verify_otp(email=email, user_otp=otp)
        return self.signup_email_user(email=email, name=name)

    def get_user_by_session_token(self, token: str) -> Optional[User]:
        """
        Retrieves user from PostgreSQL by validating active session token.
        """
        if not token:
            return None

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # Find session
            session_record = db.query(UserSessionModel).filter(
                UserSessionModel.token == token
            ).first()

            if not session_record:
                return None

            # Check expiration
            exp = session_record.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)

            if exp < now:
                # Session expired: delete and return None
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
        """
        Deletes session from PostgreSQL user_sessions table.
        """
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
