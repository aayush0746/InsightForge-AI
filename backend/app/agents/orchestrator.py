import concurrent.futures
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.app.agents.analyst import analyst_agent
from backend.app.agents.critic import critic_agent
from backend.app.agents.fact_checker import fact_checker_agent
from backend.app.agents.planner import planner_agent
from backend.app.agents.research import research_agent
from backend.app.agents.synthesizer import synthesizer_agent
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import ResearchReportModel
from backend.app.db.session import SessionLocal, init_db
from backend.app.schemas.research import ResearchReport, AgentExecutionStep


class AgentOrchestrator:
    """
    Coordinates the multi-agent research workflow and persists reports in SQL:
    Planner -> Research -> Analyst -> (Critic || Fact Checker) -> Synthesizer.
    """

    def __init__(self):
        init_db()

    def run_research(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        max_subtasks: int = 4,
        deep_analysis: bool = True,
        enable_web_search: bool = False,
        user_id: Optional[str] = None
    ) -> ResearchReport:
        logger.info(f"--- Starting Agentic Research Workflow for: '{question}' (web search: {enable_web_search}) ---")
        steps: List[AgentExecutionStep] = []
        reasoning_model = settings.DEFAULT_GEMINI_MODEL

        # 1. Planner Agent
        plan_out = planner_agent.plan(question=question, max_subtasks=max_subtasks)
        plan = plan_out["plan"]
        steps.append(plan_out["step"])

        # 2. Research Agent
        subtasks = plan.get("subtasks", [])
        if not subtasks:
            subtasks = [{"title": "General Context", "search_query": question}]

        research_out = research_agent.gather_evidence(
            subtasks=subtasks,
            document_ids=document_ids,
            enable_web_search=enable_web_search,
            main_question=question
        )
        evidence_chunks = research_out["evidence_chunks"]
        citations = research_out["citations"]
        steps.append(research_out["step"])

        # 3. Analyst Agent
        analyst_out = analyst_agent.analyze(
            question=question,
            evidence_chunks=evidence_chunks,
            plan=plan,
            model=reasoning_model
        )
        analysis = analyst_out["analysis"]
        steps.append(analyst_out["step"])

        # 4 & 5. Critic & Fact Checker concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            critic_future = executor.submit(
                critic_agent.review,
                question=question,
                analysis=analysis,
                evidence_chunks=evidence_chunks,
                model=reasoning_model
            )
            fact_future = executor.submit(
                fact_checker_agent.verify_claims,
                key_findings=analysis.get("key_findings", []),
                evidence_chunks=evidence_chunks,
                model=reasoning_model
            )
            critic_out = critic_future.result()
            fact_out = fact_future.result()

        critique = critic_out["critique"]
        steps.append(critic_out["step"])
        steps.append(fact_out["step"])

        # 6. Synthesizer Agent
        synth_out = synthesizer_agent.synthesize(
            question=question,
            plan=plan,
            analysis=analysis,
            critique=critique,
            fact_check_result=fact_out,
            citations=citations,
            agent_steps=steps,
            model=reasoning_model
        )
        report: ResearchReport = synth_out["report"]
        report.user_id = user_id

        self.save_report(report)
        logger.info(f"--- Completed Agentic Research: {report.research_id} ---")
        return report

    def save_report(self, report: ResearchReport) -> None:
        report_json = report.model_dump_json()
        with SessionLocal() as db:
            try:
                existing = db.query(ResearchReportModel).filter(
                    ResearchReportModel.research_id == report.research_id
                ).first()
                if existing:
                    existing.user_id = report.user_id
                    existing.question = report.question
                    existing.grounding_score = report.grounding_score
                    existing.report_json = report_json
                else:
                    db.add(ResearchReportModel(
                        research_id=report.research_id,
                        user_id=report.user_id,
                        question=report.question,
                        grounding_score=report.grounding_score,
                        report_json=report_json,
                        created_at=report.created_at or datetime.now(timezone.utc)
                    ))
                db.commit()
                logger.info(f"Persisted report {report.research_id} to SQL.")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to persist research report: {e}")

    def load_reports(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        with SessionLocal() as db:
            q = db.query(ResearchReportModel)
            if user_id is not None:
                q = q.filter(ResearchReportModel.user_id == user_id)
            rows = q.order_by(ResearchReportModel.created_at.desc()).all()
            out: Dict[str, Any] = {}
            for r in rows:
                try:
                    out[r.research_id] = json.loads(r.report_json)
                except Exception:
                    pass
            return out

    def get_report(self, research_id: str, user_id: Optional[str] = None) -> Optional[ResearchReport]:
        with SessionLocal() as db:
            row = db.query(ResearchReportModel).filter(
                ResearchReportModel.research_id == research_id
            ).first()
            if not row:
                return None
            if user_id is not None and row.user_id != user_id:
                return None
            if user_id is None and row.user_id is not None:
                return None
            return ResearchReport(**json.loads(row.report_json))


agent_orchestrator = AgentOrchestrator()
