import time
from typing import Dict, Any, List, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.research import AgentExecutionStep

class CriticAgent:
    """
    Critic Agent: Evaluates the depth, completeness, and objectivity
    of the preliminary analysis. Flags unsupported claims, biases,
    or missed nuances in the original research prompt.
    """

    def review(
        self,
        question: str,
        analysis: Dict[str, Any],
        evidence_chunks: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("[Critic Agent] Reviewing analysis quality and question alignment...")

        findings_text = "\n".join(f"- {f}" for f in analysis.get("key_findings", []))
        synthesis_text = analysis.get("evidence_synthesis", "")

        prompt = f"""
You are the Critic Agent in an Agentic AI Research System.
Critically evaluate the proposed findings and synthesis for the user question.

Question: {question}

Proposed Key Findings:
{findings_text}

Evidence Synthesis:
{synthesis_text}

Number of Supporting Chunks Available: {len(evidence_chunks)}

Your goals:
1. Determine if the proposed findings directly and fully answer the question.
2. Identify any unsubstantiated assumptions or weak arguments.
3. Formulate concrete recommendations to improve clarity, precision, and tone.
4. List risks and operational limitations.

Return ONLY valid JSON:
{{
    "passes_quality_threshold": true,
    "critique_summary": "Summary of critical assessment...",
    "identified_weaknesses": ["Weakness 1...", "Weakness 2..."],
    "actionable_improvements": ["Improvement 1..."],
    "risks_and_limitations": ["Risk/Limitation 1...", "Risk/Limitation 2..."]
}}
"""
        critique_data = gemini_client.generate_json(prompt, model=model)
        duration = round(time.time() - start_time, 2)

        step_log = AgentExecutionStep(
            agent_name="Critic Agent",
            title="Conducted adversarial review of findings and arguments",
            status="completed",
            details=f"Quality check passed: {critique_data.get('passes_quality_threshold', True)}. Identified {len(critique_data.get('risks_and_limitations', []))} risks/limitations.",
            execution_time_seconds=duration,
            data=critique_data
        )

        return {
            "critique": critique_data,
            "step": step_log
        }

critic_agent = CriticAgent()

