from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool

from backend.app.api.routes_auth import get_effective_owner_id
from backend.app.core.logger import logger
from backend.app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationRunRecord,
    PromptTemplate
)
from backend.app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluate", tags=["Prompt Evaluation"])


@router.post("", response_model=EvaluationRunRecord)
async def evaluate_prompts(
    request: EvaluationRequest,
    owner_id: str = Depends(get_effective_owner_id)
):
    if not request.prompts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one prompt must be provided for evaluation."
        )

    try:
        return await run_in_threadpool(evaluation_service.run_evaluation, request, owner_id)
    except Exception as e:
        logger.error(f"Prompt evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.get("/templates", response_model=List[PromptTemplate])
async def get_templates():
    return evaluation_service.get_templates()


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_evaluation_history(owner_id: str = Depends(get_effective_owner_id)):
    return await run_in_threadpool(evaluation_service.get_history, owner_id)


@router.get("/history/{run_id}", response_model=EvaluationRunRecord)
async def get_evaluation_run(
    run_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    record = await run_in_threadpool(evaluation_service.get_run_detail, run_id, owner_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found."
        )
    return record
