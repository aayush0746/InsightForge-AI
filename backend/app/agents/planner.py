import re
import time
from typing import Dict, Any, List
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.research import AgentExecutionStep


class PlannerAgent:
    """
    Planner Agent: Analyzes the question, classifies its research intent,
    and decomposes complex questions into targeted subtasks with search queries.
    """

    @staticmethod
    def _local_plan(question: str, max_subtasks: int) -> Dict[str, Any]:
        q_low = question.lower()
        if any(k in q_low for k in ("diligence", "vendor", "sla", "company", "sec", "filing", "competitor")):
            task_type = "Due Diligence & Entity Audit"
        elif any(k in q_low for k in ("revenue", "budget", "variance", "margin", "cost", "kpi", "stipend", "fee", "price", "growth")):
            task_type = "Financial & KPI Variance Audit"
        elif any(k in q_low for k in ("compare", "diff", "clause", "liability", "penalty", "notice", "compliance", "policy", "attendance", "leave")):
            task_type = "Contract & Policy Redline Analysis"
        else:
            task_type = "Executive Decision Briefing"

        parts = [p.strip() for p in re.split(r"\b(?:and|vs\.?|versus|compared to|,)\b", question, flags=re.IGNORECASE) if len(p.strip()) > 3]
        subtasks: List[Dict[str, Any]] = []
        subtasks.append({
            "step_number": 1,
            "title": "Primary Evidence Retrieval",
            "search_query": question,
            "objective": f"Retrieve direct evidence answering: {question}"
        })
        for idx, part in enumerate(parts[:max(0, max_subtasks - 1)], start=2):
            if part.lower() != question.lower():
                subtasks.append({
                    "step_number": idx,
                    "title": f"Focused Sub-Query {idx - 1}",
                    "search_query": part,
                    "objective": f"Verify supporting details related to '{part}'"
                })
        if len(subtasks) < max_subtasks and max_subtasks >= 2:
            subtasks.append({
                "step_number": len(subtasks) + 1,
                "title": "Thresholds, Metrics & Exceptions Check",
                "search_query": f"{question} percentage fee deadline exception penalty",
                "objective": "Surface numeric thresholds, SLAs, financial figures, and policy exceptions"
            })
        return {
            "task_type": task_type,
            "complexity": "moderate" if len(subtasks) > 1 else "simple",
            "rationale": "Decomposed query into targeted retrieval, quantitative threshold verification, and exception checks for multi-stage hybrid & CrossEncoder search.",
            "subtasks": subtasks[:max_subtasks],
        }

    def plan(self, question: str, max_subtasks: int = 4) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"[Planner Agent] Planning research for: '{question}'")

        plan_data = None
        if gemini_client.is_configured:
            prompt = f"""
You are the Planner Agent in an Agentic AI Research System.
Analyze the following user research question and break it down into an optimal execution plan.

Question: {question}

Create a structured plan with at most {max_subtasks} focused subtasks.
Include a dedicated subtask for verifying quantitative thresholds, SLAs, financial figures, or policy exceptions whenever relevant.
Each subtask must specify:
1. Subtask title
2. Specific search query for the document retriever
3. Objective of this subtask

Determine the task type (prefer one of: "Due Diligence & Entity Audit", "Financial & KPI Variance Audit", "Contract & Policy Redline Analysis", "Executive Decision Briefing").

Return ONLY valid JSON matching this schema:
{{
    "task_type": "...",
    "complexity": "simple" | "moderate" | "complex",
    "rationale": "...",
    "subtasks": [
        {{
            "step_number": 1,
            "title": "...",
            "search_query": "...",
            "objective": "..."
        }}
    ]
}}
"""
            try:
                plan_data = gemini_client.generate_json(prompt)
            except Exception as e:
                logger.warning(f"[Planner Agent] Gemini failed ({e}); using local planner fallback.")

        if not plan_data or not isinstance(plan_data, dict):
            plan_data = self._local_plan(question, max_subtasks)

        duration = round(time.time() - start_time, 2)
        step_log = AgentExecutionStep(
            agent_name="Planner Agent",
            title="Decomposed question and created structured execution plan",
            status="completed",
            details=f"Task classified as '{plan_data.get('task_type', 'General Research')}' with {len(plan_data.get('subtasks', []))} subtasks.",
            execution_time_seconds=duration,
            data=plan_data
        )

        return {
            "plan": plan_data,
            "step": step_log
        }


planner_agent = PlannerAgent()
