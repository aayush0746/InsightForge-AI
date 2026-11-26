import re
from fastapi import APIRouter, HTTPException, Request, Response, Header, Depends, status
from typing import Optional

from backend.app.core.config import settings
from backend.app.schemas.auth import (
    User,
    UserCreate,
    UserLogin,
    GoogleAuthRequest,
    SendOtpRequest,
    VerifyOtpRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AuthResponse
)
from backend.app.services.auth_service import auth_service
from backend.app.services.email_service import email_service
from backend.app.db.session import SessionLocal
from backend.app.db.models import UserModel
from backend.app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/config")
async def get_auth_config():
    """
    Exposes public OAuth configuration (such as Google Client ID) to the frontend.
    Never exposes Client Secret or session secret.
    """
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID
    }


def extract_session_token(request: Request, authorization: Optional[str] = None) -> Optional[str]:
    """
    Extracts session token from explicit Authorization Bearer header first,
    then falls back to the HTTP-only session cookie.
    """
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
        if bearer_token:
            return bearer_token

    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


def _set_session_cookie(response: Response, session_token: str) -> None:
    max_age_seconds = settings.SESSION_EXPIRE_DAYS * 24 * 3600
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/"
    )


async def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Dependency returning the current authenticated user if session is valid, or None if guest.
    """
    token = extract_session_token(request, authorization)
    if not token:
        return None
    return auth_service.get_user_by_session_token(token)


async def get_effective_owner_id(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> str:
    """
    Returns authenticated user_id or an isolated guest owner identifier (`guest_<id>`)
    derived from `X-Guest-Session-Id` header or `insightforge_guest_id` cookie.
    """
    if current_user:
        return current_user.id

    raw_gid = (
        request.headers.get("X-Guest-Session-Id")
        or request.cookies.get("insightforge_guest_id")
        or ""
    )
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", raw_gid.strip())
    if sanitized.startswith("guest_"):
        sanitized = sanitized[6:]
    sanitized = sanitized[:32]
    if sanitized:
        return f"guest_{sanitized}"
    return "guest_anonymous"


async def require_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> User:
    """
    Dependency protecting routes: raises 401 if not logged in.
    """
    user = await get_current_user_optional(request, authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in."
        )
    return user


@router.post("/google", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest, response: Response):
    """
    Google OAuth 2.0 endpoint: verifies Google ID token and sets HTTP-only session cookie.
    """
    try:
        user_obj, session_token = auth_service.authenticate_google(payload)
        _set_session_cookie(response, session_token)
        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Google authentication successful."
        )
    except ValueError as e:
        logger.warning(f"Google auth client error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Google authentication unexpected failure: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google authentication failed.")


@router.post("/signin", response_model=AuthResponse)
async def signin(payload: UserLogin, response: Response):
    """
    Email & password login endpoint.
    """
    try:
        user_obj, session_token = auth_service.signin_email_user(
            email=payload.email,
            password=payload.password
        )
        _set_session_cookie(response, session_token)
        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Signed in successfully."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Sign in failed: {e}")
        raise HTTPException(status_code=500, detail="Sign in failed.")


@router.post("/signup", response_model=AuthResponse)
async def signup(payload: UserCreate, response: Response):
    """
    Email signup endpoint: registers a brand-new user with bcrypt password hash.
    """
    try:
        user_obj, session_token = auth_service.signup_email_user(
            email=payload.email,
            name=payload.name,
            password=payload.password
        )
        _set_session_cookie(response, session_token)
        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Account created successfully."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Sign up failed: {e}")
        raise HTTPException(status_code=500, detail="Sign up failed.")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """
    Sends a 6-digit password reset verification code to the registered email.
    Avoids disclosing whether unregistered emails exist in production.
    """
    try:
        clean_email = payload.email.lower().strip()
        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.email == clean_email).first()
            user_name = user.full_name if user else None
        finally:
            db.close()

        if not user_name:
            return {
                "success": True,
                "message": f"If an account exists for {clean_email}, a password reset verification code has been sent."
            }

        result = email_service.generate_and_send_otp(
            email=clean_email,
            name=user_name,
            purpose="password_reset"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to dispatch password reset OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send password reset code.")


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(payload: ResetPasswordRequest, response: Response):
    """
    Verifies 6-digit OTP code and updates user's password with a new bcrypt hash.
    """
    try:
        user_obj, session_token = auth_service.reset_password_with_otp(
            email=payload.email,
            otp=payload.otp,
            new_password=payload.new_password
        )
        _set_session_cookie(response, session_token)
        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Password reset successfully. You are now logged in."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed.")


@router.post("/send-otp")
async def send_otp(payload: SendOtpRequest):
    """
    Sends a 6-digit OTP to the user's email for verification & passwordless login.
    """
    try:
        clean_email = payload.email.lower().strip()
        purpose = (payload.purpose or "login").lower().strip()
        return email_service.generate_and_send_otp(
            email=clean_email,
            name=payload.name,
            purpose=purpose
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to dispatch OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code.")


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(payload: VerifyOtpRequest, response: Response):
    """
    Verifies 6-digit OTP code and signs in or creates the verified user.
    """
    try:
        user_obj, session_token = auth_service.complete_otp_login_or_register(
            email=payload.email,
            otp=payload.otp,
            name=payload.name,
            password=payload.password
        )
        _set_session_cookie(response, session_token)
        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Email verified successfully."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        raise HTTPException(status_code=500, detail="Verification failed.")


@router.post("/resend-otp")
async def resend_otp(payload: SendOtpRequest):
    """
    Resends a fresh 6-digit OTP code to the requested email.
    """
    return await send_otp(payload)


@router.get("/me", response_model=User)
async def get_me(request: Request, authorization: Optional[str] = Header(None)):
    """
    Validates session cookie / Bearer token and returns current user.
    """
    token = extract_session_token(request, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. No active session found."
        )

    user = auth_service.get_user_by_session_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again."
        )

    return user


@router.post("/logout")
async def logout(request: Request, response: Response, authorization: Optional[str] = Header(None)):
    """
    Logs out user, deletes session from user_sessions, and clears the HTTP-only cookie.
    """
    token = extract_session_token(request, authorization)
    if token:
        auth_service.logout_session(token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/"
    )
    return {"success": True, "message": "Logged out successfully."}
