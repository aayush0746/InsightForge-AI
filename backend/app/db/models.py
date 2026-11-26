import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, LargeBinary, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    profile_picture = Column(Text, nullable=True)
    auth_provider = Column(String(50), default="google", nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("UserDocumentModel", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("UserChatMessageModel", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "name": self.full_name,
            "email": self.email,
            "google_id": self.google_id,
            "profile_picture": self.profile_picture,
            "avatar_url": self.profile_picture,
            "auth_provider": self.auth_provider,
            "provider": self.auth_provider,
            "role": "Researcher",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    token = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserModel", back_populates="sessions")

class EmailOtpModel(Base):
    __tablename__ = "email_otps"

    email = Column(String(255), primary_key=True)
    otp_hash = Column(String(128), nullable=False)
    name = Column(String(120), nullable=True)
    purpose = Column(String(40), default="login", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

class UserDocumentModel(Base):
    """
    Cloud persistent document storage for authenticated users on Supabase PostgreSQL.
    Stores metadata and binary document bytes securely in the cloud.
    """
    __tablename__ = "user_documents"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    total_pages = Column(Integer, default=1)
    total_chunks = Column(Integer, default=0)
    status = Column(String(50), default="indexed")
    content_type = Column(String(100), nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    source_type = Column(String(20), default="file")
    source_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("UserModel", back_populates="documents")

class UserChatMessageModel(Base):
    """
    Cloud persistent chat message history for authenticated users on Supabase PostgreSQL.
    """
    __tablename__ = "user_chat_messages"

    id = Column(String(64), primary_key=True, default=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent_mode = Column(String(30), default="fast")
    citations_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("UserModel", back_populates="chat_messages")

class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, default="", nullable=False)
    color = Column(String(30), default="indigo", nullable=False)
    icon = Column(String(30), default="folder", nullable=False)
    document_ids_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    threads = relationship("ProjectThreadModel", back_populates="project", cascade="all, delete-orphan")

class ProjectThreadModel(Base):
    __tablename__ = "project_threads"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    title = Column(String(160), nullable=False)
    messages_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    project = relationship("ProjectModel", back_populates="threads")

class ResearchReportModel(Base):
    __tablename__ = "research_reports"

    research_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True, index=True)
    question = Column(Text, nullable=False)
    grounding_score = Column(Float, default=100.0, nullable=False)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    run_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True, index=True)
    question = Column(Text, nullable=False)
    best_prompt_name = Column(String(120), nullable=False)
    record_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
