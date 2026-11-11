from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.chat import Citation

class AgentExecutionStep(BaseModel):
    agent_name: str  # Planner, Research, Analyst, Critic, Fact Checker, Synthesizer
    title: str
    status: str = "completed"  # pending, in_progress, completed, failed
    details: str
    execution_time_seconds: float = 0.0
    data: Optional[Dict[str, Any]] = None

class FactCheckItem(BaseModel):
    claim: str
    is_supported: bool
    confidence: float  # 0.0 to 1.0
    source_citation: Optional[str] = None
    note: str

class ResearchReport(BaseModel):
    research_id: str
    question: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str
    methodology: str
    key_findings: List[str]
    evidence_analysis: str
    ai_interpretations: List[str]
    conflicts_or_gaps: List[str]
    risks_and_limitations: List[str]
    recommendations: List[str]
    citations: List[Citation]
    fact_check_results: List[FactCheckItem]
    grounding_score: float  # Percentage of claims supported by documents
    agent_steps: List[AgentExecutionStep]
    chart_data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    document_ids: Optional[List[str]] = None
    deep_analysis: bool = True
    enable_web_search: bool = False
    max_subtasks: int = 4

class ResearchResponse(BaseModel):
    success: bool
    report: ResearchReport
    message: str
