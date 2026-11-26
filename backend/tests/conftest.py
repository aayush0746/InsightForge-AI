import shutil
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.core.config as config_mod
import backend.app.db.session as session_mod
import backend.app.services.auth_service as auth_service_mod
import backend.app.services.email_service as email_service_mod
import backend.app.services.document_service as doc_service_mod
import backend.app.services.project_service as project_service_mod
import backend.app.agents.orchestrator as orchestrator_mod
import backend.app.prompts.history as history_mod
import backend.app.api.routes_auth as routes_auth_mod
import backend.app.api.routes_chat as routes_chat_mod
import backend.app.api.routes_research as routes_research_mod
from backend.app.db.models import Base
from backend.app.rag.vector_store import vector_store


@pytest.fixture(scope="session", autouse=True)
def isolated_test_env(tmp_path_factory):
    """
    Isolates SQLite DB, ChromaDB directory, documents directory, and metadata JSON
    inside a temporary pytest directory so tests never mutate live data/ or chroma_db/.
    """
    root = tmp_path_factory.mktemp("insightforge_test")
    docs_dir = root / "documents"
    chroma_dir = root / "chroma_db"
    data_dir = root / "data"
    docs_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Copy sample college_rules.pdf if present
    orig_sample = config_mod.settings.DOCUMENTS_DIR / "college_rules.pdf"
    if orig_sample.exists():
        shutil.copy(orig_sample, docs_dir / "college_rules.pdf")

    config_mod.settings.DOCUMENTS_DIR = docs_dir
    config_mod.settings.CHROMA_DIR = chroma_dir
    config_mod.settings.DATA_DIR = data_dir
    config_mod.settings.APP_ENV = "development"
    config_mod.settings.SMTP_HOST = ""
    config_mod.settings.SMTP_USER = ""
    config_mod.settings.SMTP_PASSWORD = ""
    config_mod.settings.GEMINI_API_KEY = ""
    doc_service_mod.DOC_METADATA_FILE = data_dir / "documents_metadata.json"

    test_db_url = f"sqlite:///{data_dir / 'test_insightforge.db'}"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.create_all(bind=test_engine)

    # Point all modules that imported SessionLocal to the isolated test session maker
    for mod in (
        session_mod,
        auth_service_mod,
        email_service_mod,
        doc_service_mod,
        project_service_mod,
        orchestrator_mod,
        history_mod,
        routes_auth_mod,
        routes_chat_mod,
        routes_research_mod,
    ):
        setattr(mod, "SessionLocal", TestSessionLocal)

    session_mod.engine = test_engine
    session_mod.DB_DIALECT = "sqlite"

    # Reset vector_store singleton client to point at temp chroma_dir
    vector_store._client = None
    vector_store._collection = None
    vector_store._chroma_path = None

    # Index sample college_rules.pdf cleanly in isolated env
    doc_service_mod.document_service.ensure_sample_documents_indexed()

    yield root
