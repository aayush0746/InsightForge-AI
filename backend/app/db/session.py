import os
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
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
                # PostgreSQL host is reachable, connect
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

    # SQLite fallback
    fallback_url = f"sqlite:///{settings.DATA_DIR / 'insightforge.db'}"
    sqlite_engine = create_engine(
        fallback_url,
        connect_args={"check_same_thread": False}
    )
    logger.info(f"Using database engine: {fallback_url}")
    return sqlite_engine, "sqlite"

engine, DB_DIALECT = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Creates all database tables (users, user_sessions) if they do not exist,
    and secures them with Row Level Security (RLS) on PostgreSQL.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database tables initialized successfully ({DB_DIALECT}).")

        # Automatically enable Row Level Security & lockdown public PostgREST access on PostgreSQL (Supabase Best Practice)
        if DB_DIALECT == "postgresql":
            with engine.connect() as conn:
                for tbl in ["users", "user_sessions", "user_documents", "user_chat_messages"]:
                    conn.execute(text(f"ALTER TABLE public.{tbl} ENABLE ROW LEVEL SECURITY;"))
                    conn.execute(text(f"REVOKE ALL ON TABLE public.{tbl} FROM anon, authenticated;"))
                
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'service_role_access_users'
                        ) THEN
                            CREATE POLICY service_role_access_users ON public.users FOR ALL TO service_role USING (true) WITH CHECK (true);
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'user_sessions' AND policyname = 'service_role_access_sessions'
                        ) THEN
                            CREATE POLICY service_role_access_sessions ON public.user_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'user_documents' AND policyname = 'service_role_access_docs'
                        ) THEN
                            CREATE POLICY service_role_access_docs ON public.user_documents FOR ALL TO service_role USING (true) WITH CHECK (true);
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'user_chat_messages' AND policyname = 'service_role_access_chat'
                        ) THEN
                            CREATE POLICY service_role_access_chat ON public.user_chat_messages FOR ALL TO service_role USING (true) WITH CHECK (true);
                        END IF;
                    END
                    $$;
                """))
                conn.commit()
            logger.info("Row Level Security (RLS) and access protection enforced on all Supabase tables.")
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
