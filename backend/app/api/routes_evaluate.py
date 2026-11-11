from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationRunRecord,
    PromptTemplate
)
from backend.app.services.evaluation_service import evaluation_service
from backend.app.core.logger import logger

router = APIRouter(prefix="/evaluate", tags=["Prompt Evaluation"])

@router.post("", response_model=EvaluationRunRecord)
async def evaluate_prompts(request: EvaluationRequest):
    """
    Run LLM-as-a-Judge evaluation comparing multiple prompt templates.
    """
    if not request.prompts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one prompt must be provided for evaluation."
        )

    try:
        record = evaluation_service.run_evaluation(request)
        return record
    except Exception as e:
        logger.error(f"Prompt evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )

@router.get("/templates", response_model=List[PromptTemplate])
async def get_templates():
    """
    Get built-in prompt templates.
    """
    return evaluation_service.get_templates()

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_evaluation_history():
    """
    List past prompt evaluation runs.
    """
    return evaluation_service.get_history()

@router.get("/history/{run_id}", response_model=EvaluationRunRecord)
async def get_evaluation_run(run_id: str):
    """
    Get details of a specific evaluation run.
    """
    record = evaluation_service.get_run_detail(run_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found."
        )
    return record

