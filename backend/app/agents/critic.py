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

    @staticmethod
    def _local_critique(analysis: Dict[str, Any], evidence_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        findings = analysis.get("key_findings", [])
        gaps = analysis.get("conflicts_or_gaps", [])
        passes = bool(evidence_chunks) and len(findings) > 0
        weaknesses = list(gaps) if gaps else []
        if len(evidence_chunks) < 3:
            weaknesses.append("Limited chunk coverage (<3 passages retrieved); additional documents may broaden coverage.")
        return {
            "passes_quality_threshold": passes,
            "critique_summary": (
                f"Reviewed {len(findings)} finding(s) backed by {len(evidence_chunks)} evidence passage(s) across operator decision gates."
            ),
            "identified_weaknesses": weaknesses,
            "actionable_improvements": [
                "Decision Gate 1: Verify clause precedence and effective dates if multiple document versions appear.",
                "Decision Gate 2: Check source diversity and sample coverage (<3 chunks or single-source claims need corroboration).",
                "Decision Gate 3: Cross-check extracted quantitative figures and SLA/penalty thresholds directly against cited pages."
            ],
            "risks_and_limitations": weaknesses or [
                "Extractive findings reflect retrieved chunks only; verify downstream operational decisions against primary source clauses."
            ],
        }

    def review(
        self,
        question: str,
        analysis: Dict[str, Any],
        evidence_chunks: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("[Critic Agent] Reviewing analysis quality and question alignment...")

        critique_data = None
        if gemini_client.is_configured:
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

Your goals (apply operator decision gates):
1. Determine if the proposed findings directly and fully answer the question, checking clause precedence and effective dates when multiple versions exist.
2. Check sample size / source diversity and identify any unsubstantiated assumptions or weak arguments.
3. Formulate concrete recommendations to cross-check extracted quantitative figures, SLAs, and penalty thresholds directly against cited pages.
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
            try:
                critique_data = gemini_client.generate_json(prompt, model=model)
            except Exception as e:
                logger.warning(f"[Critic Agent] Gemini failed ({e}); using local critique fallback.")

        if not critique_data or not isinstance(critique_data, dict):
            critique_data = self._local_critique(analysis, evidence_chunks)

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
