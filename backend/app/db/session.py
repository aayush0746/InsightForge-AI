import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import Base

DATABASE_URL = settings.DATABASE_URL

def is_db_reachable(url: str, timeout: float = 3.0) -> bool:
    """
    Fast pre-flight socket probe to check if PostgreSQL host & port are reachable.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def create_db_engine():
    try:
        if DATABASE_URL.startswith("postgresql"):
            if is_db_reachable(DATABASE_URL, timeout=3.0):
                test_engine = create_engine(
                    DATABASE_URL,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20
                )
                with test_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"Connected to PostgreSQL database at {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
                return test_engine, "postgresql"
            else:
                logger.info("PostgreSQL server not detected on configured port. Using resilient SQLite engine.")
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite local database.")

    fallback_url = f"sqlite:///{settings.DATA_DIR / 'insightforge.db'}"
    sqlite_engine = create_engine(
        fallback_url,
        connect_args={"check_same_thread": False}
    )
    logger.info(f"Using database engine: {fallback_url}")
    return sqlite_engine, "sqlite"

engine, DB_DIALECT = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ALL_TABLES = [
    "users",
    "user_sessions",
    "email_otps",
    "user_documents",
    "user_chat_messages",
    "projects",
    "project_threads",
    "research_reports",
    "evaluation_runs",
]

def init_db():
    """
    Creates all database tables if they do not exist,
    and enforces Row Level Security (RLS) on PostgreSQL.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database tables initialized successfully ({DB_DIALECT}).")

        # Ensure password_hash column exists on pre-existing users tables
        try:
            with engine.connect() as conn:
                if DB_DIALECT == "postgresql":
                    conn.execute(text("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
                else:
                    try:
                        conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);"))
                    except Exception:
                        pass
                conn.commit()
        except Exception as col_err:
            logger.warning(f"Notice on ensuring password_hash column: {col_err}")

        if DB_DIALECT == "postgresql":
            with engine.connect() as conn:
                for tbl in ALL_TABLES:
                    conn.execute(text(f"ALTER TABLE public.{tbl} ENABLE ROW LEVEL SECURITY;"))
                    conn.execute(text(f"REVOKE ALL ON TABLE public.{tbl} FROM anon, authenticated;"))
                    policy_name = f"service_role_access_{tbl}"
                    conn.execute(text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_policies WHERE tablename = '{tbl}' AND policyname = '{policy_name}'
                            ) THEN
                                CREATE POLICY {policy_name} ON public.{tbl} FOR ALL TO service_role USING (true) WITH CHECK (true);
                            END IF;
                        END
                        $$;
                    """))
                conn.commit()
            logger.info("Row Level Security (RLS) and access protection enforced on all PostgreSQL tables.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

def get_db():
    """
    FastAPI dependency yielding a SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
