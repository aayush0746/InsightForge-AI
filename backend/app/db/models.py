import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, LargeBinary
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
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
            "name": self.full_name,  # compatibility alias
            "email": self.email,
            "google_id": self.google_id,
            "profile_picture": self.profile_picture,
            "avatar_url": self.profile_picture,  # compatibility alias
            "auth_provider": self.auth_provider,
            "provider": self.auth_provider,  # compatibility alias
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
    file_data = Column(LargeBinary, nullable=True)  # Stores actual binary file content in Supabase Cloud
    source_type = Column(String(20), default="file")  # 'file' or 'url'
    source_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("UserModel", back_populates="documents")

class UserChatMessageModel(Base):
    """
    Cloud persistent chat message history for authenticated users on Supabase PostgreSQL.
    Restores the exact conversation when the user logs back in.
    """
    __tablename__ = "user_chat_messages"

    id = Column(String(64), primary_key=True, default=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    agent_mode = Column(String(30), default="fast")  # 'fast' or 'agentic'
    citations_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("UserModel", back_populates="chat_messages")
