import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.schemas.research import ResearchReport, AgentExecutionStep
from backend.app.agents.planner import planner_agent
from backend.app.agents.research import research_agent
from backend.app.agents.analyst import analyst_agent
from backend.app.agents.critic import critic_agent
from backend.app.agents.fact_checker import fact_checker_agent
from backend.app.agents.synthesizer import synthesizer_agent

REPORTS_STORE_PATH = settings.DATA_DIR / "research_reports.json"

class AgentOrchestrator:
    """
    Coordinates the multi-agent research workflow:
    Planner -> Research -> Analyst -> Critic -> Fact Checker -> Synthesizer.
    """

    def run_research(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        max_subtasks: int = 4,
        deep_analysis: bool = True,
        enable_web_search: bool = False
    ) -> ResearchReport:
        logger.info(f"--- Starting Agentic Research Workflow for: '{question}' (web search: {enable_web_search}) ---")
        steps: List[AgentExecutionStep] = []

        # Model selection: fast flash for planner, deep reasoning model for analyst/critic/synthesizer if configured
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

        # 3. Analyst Agent (Deep synthesis)
        analyst_out = analyst_agent.analyze(
            question=question,
            evidence_chunks=evidence_chunks,
            plan=plan,
            model=reasoning_model
        )
        analysis = analyst_out["analysis"]
        steps.append(analyst_out["step"])

        # 4 & 5. Run Critic Agent and Fact Checker Agent concurrently for 2x faster execution
        import concurrent.futures
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

        # 6. Synthesizer Agent (Publication report compilation)
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

        # Persist report
        self.save_report(report)
        logger.info(f"--- Completed Agentic Research: {report.research_id} ---")
        return report

    def save_report(self, report: ResearchReport) -> None:
        try:
            records = self.load_reports()
            # Convert report to dict (handling datetime serialization)
            report_dict = json.loads(report.model_dump_json())
            records[report.research_id] = report_dict

            with open(REPORTS_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            logger.info(f"Persisted report {report.research_id} to disk.")
        except Exception as e:
            logger.error(f"Failed to persist research report: {e}")

    def load_reports(self) -> Dict[str, Any]:
        if not REPORTS_STORE_PATH.exists():
            return {}
        try:
            with open(REPORTS_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_report(self, research_id: str) -> Optional[ResearchReport]:
        reports = self.load_reports()
        data = reports.get(research_id)
        if not data:
            return None
        return ResearchReport(**data)

agent_orchestrator = AgentOrchestrator()

