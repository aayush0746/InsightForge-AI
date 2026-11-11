from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from backend.app.schemas.research import ResearchRequest, ResearchResponse, ResearchReport
from backend.app.services.research_service import research_service
from backend.app.api.routes_auth import get_current_user_optional
from backend.app.schemas.auth import User
from backend.app.core.security import sanitize_text_input
from backend.app.db.session import SessionLocal
from backend.app.db.models import UserChatMessageModel
import uuid

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
    Transforms research reports or document findings into an engaging 2-minute executive podcast script.
    """
    try:
        script = research_service.generate_podcast_script(request.text, request.topic)
        word_count = len(script.split())
        est_duration = round(word_count / 140, 1)
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
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Launch multi-agent deep research workflow:
    Planner -> Research -> Analyst -> Critic -> Fact Checker -> Synthesizer.
    """
    clean_question = sanitize_text_input(request.question)
    try:
        user_id = current_user.id if current_user else None
        report = research_service.execute_deep_research(
            question=clean_question,
            document_ids=request.document_ids,
            max_subtasks=request.max_subtasks,
            deep_analysis=request.deep_analysis,
            enable_web_search=request.enable_web_search,
            user_id=user_id
        )

        # Persist conversation to Supabase Cloud PostgreSQL for authenticated user
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
                logger.warning(f"Could not persist research chat to Supabase: {e}")

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
async def list_reports(current_user: Optional[User] = Depends(get_current_user_optional)):
    """
    List all generated research reports.
    """
    user_id = current_user.id if current_user else None
    return research_service.list_reports(user_id=user_id)

@router.get("/{research_id}", response_model=ResearchReport)
async def get_report(
    research_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Fetch a generated research report by ID with user ownership check.
    """
    user_id = current_user.id if current_user else None
    report = research_service.get_report(research_id, user_id=user_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report '{research_id}' not found or access denied."
        )
    return report

