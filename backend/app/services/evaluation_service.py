import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationRunRecord,
    PromptRunResult,
    PromptTemplate
)
from backend.app.prompts.evaluator import prompt_evaluator
from backend.app.prompts.history import evaluation_history_store
from backend.app.prompts.templates import get_default_templates

class EvaluationService:
    """
    Manages prompt evaluation benchmarking and template catalogs.
    """

    def run_evaluation(self, request: EvaluationRequest) -> EvaluationRunRecord:
        run_id = f"eval_{uuid.uuid4().hex[:8]}"
        
        # Run prompt comparison
        results: Dict[str, PromptRunResult] = prompt_evaluator.run_comparison(
            question=request.question,
            prompts=request.prompts,
            context=request.context
        )

        # Determine best prompt by overall score
        best_name = max(results.keys(), key=lambda k: results[k].metrics.overall) if results else "None"

        record = EvaluationRunRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            question=request.question,
            results=results,
            best_prompt_name=best_name
        )

        if request.save_to_history:
            evaluation_history_store.save_run(record)

        return record

    def get_templates(self) -> List[PromptTemplate]:
        return get_default_templates()

    def get_history(self) -> List[Dict[str, Any]]:
        return evaluation_history_store.list_runs()

    def get_run_detail(self, run_id: str) -> Optional[EvaluationRunRecord]:
        return evaluation_history_store.get_run(run_id)

evaluation_service = EvaluationService()
