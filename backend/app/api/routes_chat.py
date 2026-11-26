import json
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool

from backend.app.api.routes_auth import get_current_user_optional, get_effective_owner_id
from backend.app.core.logger import logger
from backend.app.core.security import sanitize_text_input
from backend.app.db.models import UserChatMessageModel
from backend.app.db.session import SessionLocal
from backend.app.rag.pipeline import rag_pipeline
from backend.app.schemas.auth import User
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.document_service import document_service

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
        logger.error(f"Failed to fetch chat history: {e}")
        return {"history": []}


@router.post("/history")
async def save_chat_message(
    payload: SaveChatMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
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
        logger.error(f"Failed to save chat message: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/history")
async def clear_chat_history(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if not current_user:
        return {"success": True, "message": "Guest session chat cleared"}

    try:
        with SessionLocal() as db:
            deleted = db.query(UserChatMessageModel).filter(
                UserChatMessageModel.user_id == current_user.id
            ).delete()
            db.commit()
            logger.info(f"Cleared {deleted} chat messages for user {current_user.id}")
            return {"success": True, "deleted_count": deleted}
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        return {"success": False, "error": str(e)}


@router.post("", response_model=ChatResponse)
async def chat_rag(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Direct Q&A with grounded context and strict per-user/guest document isolation.
    Never converts an empty accessible_ids list to None.
    """
    clean_question = sanitize_text_input(request.question)
    try:
        accessible_docs = await run_in_threadpool(document_service.list_documents, owner_id)
        accessible_ids = [d.document_id for d in accessible_docs]
        accessible_set = set(accessible_ids)

        if request.document_ids is not None:
            effective_doc_ids = [did for did in request.document_ids if did in accessible_set]
        else:
            effective_doc_ids = accessible_ids

        response = await run_in_threadpool(
            rag_pipeline.answer_question,
            question=clean_question,
            document_ids=effective_doc_ids,
            use_reranker=request.use_reranker,
            enable_web_search=request.enable_web_search,
            top_k=request.top_k,
            top_n=request.top_n,
            history=request.history
        )

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
                logger.warning(f"Could not auto-persist chat exchange: {e}")

        return response
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )
