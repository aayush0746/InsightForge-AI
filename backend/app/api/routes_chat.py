import json
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.rag.pipeline import rag_pipeline
from backend.app.services.document_service import document_service
from backend.app.api.routes_auth import get_current_user_optional
from backend.app.schemas.auth import User
from backend.app.core.security import sanitize_text_input
from backend.app.core.logger import logger
from backend.app.db.session import SessionLocal
from backend.app.db.models import UserChatMessageModel

router = APIRouter(prefix="/chat", tags=["Chat"])

class SaveChatMessageRequest(BaseModel):
    role: str
    content: str
    agent_mode: Optional[str] = "fast"
    citations: Optional[List[Dict[str, Any]]] = None

@router.get("/history")
async def get_chat_history(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Fetch cloud-persisted chat history from Supabase PostgreSQL for the logged-in user.
    Guests receive an empty list since guest messages are temporary and not stored.
    """
    if not current_user:
        return {"history": []}

    try:
        with SessionLocal() as db:
            messages = db.query(UserChatMessageModel).filter(
                UserChatMessageModel.user_id == current_user.id
            ).order_by(UserChatMessageModel.created_at.asc()).all()

            return {
                "history": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "agent_mode": m.agent_mode,
                        "citations": json.loads(m.citations_json) if m.citations_json else None,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in messages
                ]
            }
    except Exception as e:
        logger.error(f"Failed to fetch chat history from Supabase: {e}")
        return {"history": []}

@router.post("/history")
async def save_chat_message(
    payload: SaveChatMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Save a chat message to Supabase Cloud PostgreSQL for authenticated users.
    """
    if not current_user:
        return {"success": True, "saved": False, "message": "Guest message not persisted to cloud"}

    try:
        with SessionLocal() as db:
            msg = UserChatMessageModel(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                user_id=current_user.id,
                role=payload.role,
                content=payload.content,
                agent_mode=payload.agent_mode or "fast",
                citations_json=json.dumps(payload.citations) if payload.citations else None
            )
            db.add(msg)
            db.commit()
            return {"success": True, "saved": True, "id": msg.id}
    except Exception as e:
        logger.error(f"Failed to save chat message to Supabase: {e}")
        return {"success": False, "error": str(e)}

@router.delete("/history")
async def clear_chat_history(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Clear all saved chat messages in Supabase PostgreSQL for the logged-in user.
    """
    if not current_user:
        return {"success": True, "message": "Guest session chat cleared"}

    try:
        with SessionLocal() as db:
            deleted = db.query(UserChatMessageModel).filter(
                UserChatMessageModel.user_id == current_user.id
            ).delete()
            db.commit()
            logger.info(f"Cleared {deleted} chat messages from cloud for user {current_user.id}")
            return {"success": True, "deleted_count": deleted}
    except Exception as e:
        logger.error(f"Failed to clear chat history from Supabase: {e}")
        return {"success": False, "error": str(e)}

@router.post("", response_model=ChatResponse)
async def chat_rag(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Direct Q&A with grounded context, citations, and hallucination reduction.
    Strictly isolated: users can only search across documents accessible to their session.
    Automatically saves messages to Supabase Cloud PostgreSQL for logged-in users.
    """
    clean_question = sanitize_text_input(request.question)
    try:
        user_id = current_user.id if current_user else None
        accessible_docs = document_service.list_documents(user_id=user_id)
        accessible_ids = {d.document_id for d in accessible_docs}

        if request.document_ids:
            effective_doc_ids = [did for did in request.document_ids if did in accessible_ids]
        else:
            effective_doc_ids = list(accessible_ids) if accessible_ids else None

        response = rag_pipeline.answer_question(
            question=clean_question,
            document_ids=effective_doc_ids,
            use_reranker=request.use_reranker,
            enable_web_search=request.enable_web_search,
            top_k=request.top_k or 10,
            top_n=request.top_n or 4,
            history=request.history
        )

        # Automatically persist to Supabase Cloud PostgreSQL for authenticated users
        if current_user:
            try:
                with SessionLocal() as db:
                    u_msg = UserChatMessageModel(
                        id=f"msg_{uuid.uuid4().hex[:12]}",
                        user_id=current_user.id,
                        role="user",
                        content=clean_question,
                        agent_mode="fast"
                    )
                    a_msg = UserChatMessageModel(
                        id=f"msg_{uuid.uuid4().hex[:12]}",
                        user_id=current_user.id,
                        role="assistant",
                        content=response.answer,
                        agent_mode="fast",
                        citations_json=json.dumps([c.model_dump() for c in response.citations]) if response.citations else None
                    )
                    db.add(u_msg)
                    db.add(a_msg)
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not auto-persist chat exchange to Supabase: {e}")

        return response
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )

