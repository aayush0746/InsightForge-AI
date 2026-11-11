import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "InsightForge AI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    TEMPERATURE: float = 0.2
    GEMINI_FALLBACK_MODELS: List[str] = [
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
        "gemini-pro-latest"
    ]
    
    # Models for embeddings and reranking
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CROSS_ENCODER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # RAG Tuning Defaults
    DEFAULT_CHUNK_SIZE: int = 80  # words per chunk
    DEFAULT_CHUNK_OVERLAP: int = 15  # words overlap between chunks
    DEFAULT_RETRIEVAL_TOP_K: int = 10  # Initial candidates retrieved from Chroma + BM25
    DEFAULT_RERANK_TOP_N: int = 4  # Top candidate chunks after CrossEncoder reranking
    DEFAULT_HYBRID_ALPHA: float = 0.65  # Weight for dense vector search vs keyword search
    
    # Database & PostgreSQL Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/insightforge")
    
    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Session & Security Settings
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "insightforge_secret_session_key_2026_super_secure")
    SESSION_COOKIE_NAME: str = "insightforge_session"
    SESSION_EXPIRE_DAYS: int = 14
    
    # SMTP / Email Configuration for OTP Verification
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "InsightForge AI")
    
    # Storage Directories
    ROOT_PATH: Path = ROOT_DIR
    DOCUMENTS_DIR: Path = ROOT_DIR / "documents"
    CHROMA_DIR: Path = ROOT_DIR / "chroma_db"
    DATA_DIR: Path = ROOT_DIR / "data"
    
    # Security & Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".pptx", ".csv", ".xlsx", ".txt", ".md"]
    
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()

# Ensure directories exist
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
