import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.logger import logger
from backend.app.db.models import EvaluationRunModel
from backend.app.db.session import SessionLocal, init_db
from backend.app.schemas.evaluation import EvaluationRunRecord


class EvaluationHistoryStore:
    """
    SQL-backed persistence for prompt evaluation benchmark experiments,
    scoped per user / guest session.
    """

    def __init__(self):
        init_db()

    @staticmethod
    def save_run(record: EvaluationRunRecord, user_id: Optional[str] = None) -> None:
        record_json = record.model_dump_json()
        with SessionLocal() as db:
            try:
                db.add(EvaluationRunModel(
                    run_id=record.run_id,
                    user_id=user_id,
                    question=record.question,
                    best_prompt_name=record.best_prompt_name,
                    record_json=record_json,
                    created_at=record.timestamp or datetime.now(timezone.utc)
                ))
                db.commit()
                logger.info(f"Saved evaluation run {record.run_id} to SQL for '{user_id}'.")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to save evaluation run: {e}")

    @staticmethod
    def get_run(run_id: str, user_id: Optional[str] = None) -> Optional[EvaluationRunRecord]:
        with SessionLocal() as db:
            row = db.query(EvaluationRunModel).filter(EvaluationRunModel.run_id == run_id).first()
            if not row:
                return None
            if user_id is not None and row.user_id != user_id:
                return None
            if user_id is None and row.user_id is not None:
                return None
            return EvaluationRunRecord(**json.loads(row.record_json))

    @staticmethod
    def list_runs(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            q = db.query(EvaluationRunModel)
            if user_id is not None:
                q = q.filter(EvaluationRunModel.user_id == user_id)
            else:
                q = q.filter(EvaluationRunModel.user_id.is_(None))
            rows = q.order_by(EvaluationRunModel.created_at.desc()).all()

            summary_list = []
            for row in rows:
                try:
                    item = json.loads(row.record_json)
                    summary_list.append({
                        "run_id": row.run_id,
                        "timestamp": item.get("timestamp"),
                        "question": row.question,
                        "best_prompt_name": row.best_prompt_name,
                        "prompts_compared_count": len(item.get("results", {}))
                    })
                except Exception:
                    pass
            return summary_list


evaluation_history_store = EvaluationHistoryStore()
