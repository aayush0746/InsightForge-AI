import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.app.api.routes_auth import get_current_user_optional, get_effective_owner_id
from backend.app.core.logger import logger
from backend.app.core.security import sanitize_text_input
from backend.app.db.models import UserChatMessageModel
from backend.app.db.session import SessionLocal
from backend.app.schemas.auth import User
from backend.app.schemas.research import ResearchRequest, ResearchResponse, ResearchReport
from backend.app.services.document_service import document_service
from backend.app.services.research_service import research_service

router = APIRouter(prefix="/research", tags=["Agentic Research"])


class PodcastBriefingRequest(BaseModel):
    text: str
    topic: str = "Research Briefing"


class PodcastBriefingResponse(BaseModel):
    success: bool
    podcast_script: str
    estimated_duration_minutes: float


@router.post("/podcast-briefing", response_model=PodcastBriefingResponse)
async def generate_podcast_briefing(request: PodcastBriefingRequest):
    """
    Transforms research reports or document findings into an executive podcast script.
    """
    try:
        script = await run_in_threadpool(
            research_service.generate_podcast_script, request.text, request.topic
        )
        word_count = len(script.split())
        est_duration = max(0.2, round(word_count / 140, 1))
        return PodcastBriefingResponse(
            success=True,
            podcast_script=script,
            estimated_duration_minutes=est_duration
        )
    except Exception as e:
        logger.error(f"Failed to generate podcast script: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Podcast script generation failed: {str(e)}"
        )


@router.post("", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    owner_id: str = Depends(get_effective_owner_id)
):
    """
    Launch multi-agent deep research workflow strictly scoped to documents accessible by `owner_id`.
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

        report = await run_in_threadpool(
            research_service.execute_deep_research,
            question=clean_question,
            document_ids=effective_doc_ids,
            max_subtasks=request.max_subtasks,
            deep_analysis=request.deep_analysis,
            enable_web_search=request.enable_web_search,
            user_id=owner_id
        )

        if current_user and report:
            try:
                with SessionLocal() as db:
                    u_msg = UserChatMessageModel(
                        id=f"msg_{uuid.uuid4().hex[:12]}",
                        user_id=current_user.id,
                        role="user",
                        content=clean_question,
                        agent_mode="agentic"
                    )
                    a_msg = UserChatMessageModel(
                        id=f"msg_{uuid.uuid4().hex[:12]}",
                        user_id=current_user.id,
                        role="assistant",
                        content=report.executive_summary,
                        agent_mode="agentic"
                    )
                    db.add(u_msg)
                    db.add(a_msg)
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not persist research chat: {e}")

        return ResearchResponse(
            success=True,
            report=report,
            message="Deep multi-agent research completed successfully."
        )
    except Exception as e:
        logger.error(f"Research pipeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research agent orchestration failed: {str(e)}"
        )


@router.get("/reports", response_model=List[Dict[str, Any]])
async def list_reports(owner_id: str = Depends(get_effective_owner_id)):
    return await run_in_threadpool(research_service.list_reports, owner_id)


@router.get("/{research_id}", response_model=ResearchReport)
async def get_report(
    research_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    report = await run_in_threadpool(research_service.get_report, research_id, owner_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report '{research_id}' not found or access denied."
        )
    return report
