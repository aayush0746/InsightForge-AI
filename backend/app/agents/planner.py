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

    def plan(self, question: str, max_subtasks: int = 4) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"[Planner Agent] Planning research for: '{question}'")

        prompt = f"""
You are the Planner Agent in an Agentic AI Research System.
Analyze the following user research question and break it down into an optimal execution plan.

Question: {question}

Create a structured plan with at most {max_subtasks} focused subtasks.
Each subtask must specify:
1. Subtask title
2. Specific search query for the document retriever
3. Objective of this subtask

Determine the task type (e.g., "Policy Analysis", "Comparative Research", "Fact Verification", "Synthesized Overview").

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
        plan_data = gemini_client.generate_json(prompt)
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

