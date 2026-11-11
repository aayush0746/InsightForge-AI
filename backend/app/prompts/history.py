import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.schemas.evaluation import EvaluationRunRecord

HISTORY_FILE = settings.DATA_DIR / "evaluation_history.json"

class EvaluationHistoryStore:
    """
    Manages persistence of prompt evaluation benchmark experiments.
    """

    @staticmethod
    def save_run(record: EvaluationRunRecord) -> None:
        runs = EvaluationHistoryStore.load_all()
        runs[record.run_id] = json.loads(record.model_dump_json())

        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(runs, f, indent=2)
            logger.info(f"Saved evaluation run {record.run_id} to history.")
        except Exception as e:
            logger.error(f"Failed to save evaluation run: {e}")

    @staticmethod
    def load_all() -> Dict[str, Any]:
        if not HISTORY_FILE.exists():
            return {}
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read evaluation history: {e}")
            return {}

    @staticmethod
    def get_run(run_id: str) -> Optional[EvaluationRunRecord]:
        runs = EvaluationHistoryStore.load_all()
        data = runs.get(run_id)
        if not data:
            return None
        return EvaluationRunRecord(**data)

    @staticmethod
    def list_runs() -> List[Dict[str, Any]]:
        runs = EvaluationHistoryStore.load_all()
        summary_list = []
        for rid, item in runs.items():
            summary_list.append({
                "run_id": rid,
                "timestamp": item.get("timestamp"),
                "question": item.get("question"),
                "best_prompt_name": item.get("best_prompt_name"),
                "prompts_compared_count": len(item.get("results", {}))
            })
        summary_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return summary_list

evaluation_history_store = EvaluationHistoryStore()

