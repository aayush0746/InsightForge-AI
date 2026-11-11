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
    Extracts session token from HTTP-only cookie first, then Bearer header fallback.
    """
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]

    return None

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
            detail="Authentication required. Please sign in with Google."
        )
    return user

@router.post("/google", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest, response: Response):
    """
    Google OAuth 2.0 endpoint:
    - Verifies Google token.
    - Creates or updates user in PostgreSQL.
    - Sets secure HTTP-only session cookie.
    """
    try:
        user_obj, session_token = auth_service.authenticate_google(payload)

        # Set secure HTTP-only session cookie
        max_age_seconds = settings.SESSION_EXPIRE_DAYS * 24 * 3600
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age_seconds,
            expires=max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=False,  # True in HTTPS production
            path="/"
        )

        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Google authentication successful."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Google authentication failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/signin", response_model=AuthResponse)
async def signin(payload: UserLogin, response: Response):
    """
    Email login endpoint:
    - Finds existing user in PostgreSQL.
    - If user doesn't exist, instructs to sign up first.
    - Sets secure HTTP-only session cookie.
    """
    try:
        user_obj, session_token = auth_service.signin_email_user(
            email=payload.email
        )

        max_age_seconds = settings.SESSION_EXPIRE_DAYS * 24 * 3600
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age_seconds,
            expires=max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/"
        )

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
        raise HTTPException(status_code=500, detail=f"Sign in failed: {str(e)}")

@router.post("/signup", response_model=AuthResponse)
async def signup(payload: UserCreate, response: Response):
    """
    Email signup endpoint:
    - Registers user in PostgreSQL.
    - Sets secure HTTP-only session cookie.
    """
    try:
        user_obj, session_token = auth_service.signup_email_user(
            email=payload.email,
            name=payload.name
        )

        max_age_seconds = settings.SESSION_EXPIRE_DAYS * 24 * 3600
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age_seconds,
            expires=max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/"
        )

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
        raise HTTPException(status_code=500, detail=f"Sign up failed: {str(e)}")

@router.post("/send-otp")
async def send_otp(payload: SendOtpRequest):
    """
    Sends a 6-digit OTP to the user's email for verification before account creation.
    """
    try:
        clean_email = payload.email.lower().strip()
        # If signup purpose, verify account doesn't already exist
        if payload.purpose == "signup":
            db = SessionLocal()
            try:
                existing = db.query(UserModel).filter(UserModel.email == clean_email).first()
                if existing:
                    raise ValueError(f"An account with {clean_email} already exists. Please Sign In.")
            finally:
                db.close()

        result = email_service.generate_and_send_otp(
            email=clean_email,
            name=payload.name,
            purpose=payload.purpose or "signup"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to dispatch OTP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {str(e)}")

@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(payload: VerifyOtpRequest, response: Response):
    """
    Verifies 6-digit OTP code and creates the verified user in PostgreSQL.
    """
    try:
        user_obj, session_token = auth_service.verify_otp_and_register_user(
            email=payload.email,
            otp=payload.otp,
            name=payload.name
        )

        max_age_seconds = settings.SESSION_EXPIRE_DAYS * 24 * 3600
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age_seconds,
            expires=max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/"
        )

        return AuthResponse(
            success=True,
            access_token=session_token,
            user=user_obj,
            message="Email verified and account created successfully."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@router.post("/resend-otp")
async def resend_otp(payload: SendOtpRequest):
    """
    Resends a fresh 6-digit OTP code to the requested email.
    """
    return await send_otp(payload)

@router.get("/me", response_model=User)
async def get_me(request: Request, authorization: Optional[str] = Header(None)):
    """
    Validates session cookie / Bearer token and returns current user from PostgreSQL.
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
    Logs out user, deletes session from PostgreSQL, and clears the HTTP-only cookie.
    """
    token = extract_session_token(request, authorization)
    if token:
        auth_service.logout_session(token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/"
    )
    return {"success": True, "message": "Logged out successfully."}
