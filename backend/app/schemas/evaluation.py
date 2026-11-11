from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EvaluationMetrics(BaseModel):
    relevance: float = Field(..., ge=0, le=10)
    accuracy: float = Field(..., ge=0, le=10)
    clarity: float = Field(..., ge=0, le=10)
    completeness: float = Field(..., ge=0, le=10)
    actionability: float = Field(..., ge=0, le=10)
    faithfulness: float = Field(..., ge=0, le=10)
    overall: float = Field(..., ge=0, le=10)
    feedback: str

class PromptRunResult(BaseModel):
    prompt_name: str
    prompt_template: str
    generated_answer: str
    metrics: EvaluationMetrics
    execution_time_seconds: float = 0.0

class EvaluationRequest(BaseModel):
    question: str
    prompts: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping prompt name (e.g. 'Basic Prompt', 'Advanced Prompt') to prompt template"
    )
    context: Optional[str] = None
    save_to_history: bool = True

class EvaluationRunRecord(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    question: str
    results: Dict[str, PromptRunResult]
    best_prompt_name: str

class PromptTemplate(BaseModel):
    id: str
    name: str
    category: str
    description: str
    template: str
