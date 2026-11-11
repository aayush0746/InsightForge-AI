from typing import Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    id: str
    full_name: str
    email: str
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    auth_provider: str = "google"
    # Aliases for frontend compatibility
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    role: str = "Researcher"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=100)
    name: str = Field(..., min_length=2, max_length=80)

class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str

class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None  # Google JWT ID token
    id_token: Optional[str] = None   # alias for credential
    google_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_picture: Optional[str] = None
    mode: Optional[str] = "signin"   # "signin" or "signup"

class SendOtpRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    name: Optional[str] = None
    purpose: Optional[str] = "signup"

class VerifyOtpRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    otp: str = Field(..., min_length=4, max_length=10)
    name: Optional[str] = None
    password: Optional[str] = None

class AuthResponse(BaseModel):
    success: bool
    access_token: str
    token_type: str = "bearer"
    user: User
    message: str
