import time
import uuid
from typing import Dict, Any, List, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.rag.pipeline import AdvancedRAGPipeline
from backend.app.schemas.research import ResearchReport, AgentExecutionStep
from backend.app.schemas.chat import Citation


class SynthesizerAgent:
    """
    Synthesizer Agent: Assembles all findings, evaluations, and fact-checks
    into a comprehensive, publication-ready research report.
    """

    def synthesize(
        self,
        question: str,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        critique: Dict[str, Any],
        fact_check_result: Dict[str, Any],
        citations: List[Citation],
        agent_steps: List[AgentExecutionStep],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("[Synthesizer Agent] Generating final comprehensive research report...")

        findings = analysis.get("key_findings", [])
        interpretations = analysis.get("ai_interpretations", [])
        gaps = analysis.get("conflicts_or_gaps", [])
        risks = critique.get("risks_and_limitations", [])
        recommendations = critique.get("actionable_improvements", [])
        grounding_score = fact_check_result.get("grounding_score", 0.0)
        fact_check_items = fact_check_result.get("fact_checks", [])

        exec_summary = None
        methodology = None
        tier = (
            "HIGH"
            if grounding_score >= 80 and len(citations) >= 2
            else ("MODERATE" if grounding_score >= 50 and len(citations) >= 1 else "LOW")
        )

        if gemini_client.is_configured:
            prompt = f"""
You are the Synthesizer Agent in an Agentic AI Research System.
Generate a concise, professional Executive Summary and Methodology description for this research report.

Research Question: {question}
Task Classification: {plan.get('task_type', 'General Research')}
Number of Evidence Sources: {len(citations)}
Grounding Score: {grounding_score}% ({tier} Confidence)

Key Findings summary:
{findings}

Output ONLY valid JSON with:
{{
    "executive_summary": "Start with a 2-sentence BLUF Verdict stating {tier} confidence, key numeric takeaways, and strategic decision impact, followed by concise supporting synthesis...",
    "methodology": "Brief description of multi-agent retrieval, CrossEncoder reranking, source grading, and adversarial fact-checking applied..."
}}
"""
            try:
                synth_data = gemini_client.generate_json(prompt, model=model)
                exec_summary = synth_data.get("executive_summary")
                methodology = synth_data.get("methodology")
            except Exception as e:
                logger.warning(f"[Synthesizer Agent] Gemini failed ({e}); using Local Extractive synthesis.")

        if not exec_summary:
            if citations:
                source_count = len({c.source_filename for c in citations})
                bluf_lead = findings[0] if findings else "Review cited passages."
                exec_summary = (
                    f"BLUF Verdict [{tier} Confidence | {grounding_score}% Grounded | {len(citations)} Citations across {source_count} Source(s)]:\n"
                    f"{bluf_lead}\n\n"
                    f"Key Verified Takeaways for \"{question}\":\n"
                    + "\n".join(f"• {f}" for f in findings[:4])
                )
            else:
                exec_summary = (
                    f"No supporting passages were found in the current workspace documents for \"{question}\". "
                    "Upload relevant documents or enable Live Web Search and re-run."
                )

        if not methodology:
            mode_note = "Gemini generative synthesis" if gemini_client.is_configured else "Local Extractive synthesis (GEMINI_API_KEY not configured)"
            methodology = (
                f"Multi-stage research pipeline executing query decomposition, BM25 + ChromaDB dense Reciprocal Rank Fusion (RRF), "
                f"reranking, adversarial critique, lexical/citation fact-checking, and {mode_note}."
            )

        report_id = f"report_{uuid.uuid4().hex[:10]}"
        duration = round(time.time() - start_time, 2)
        step_log = AgentExecutionStep(
            agent_name="Synthesizer Agent",
            title="Compiled full publication-grade research report",
            status="completed",
            details=f"Synthesized executive summary, methodology, and verified sources into report {report_id}.",
            execution_time_seconds=duration,
            data={"report_id": report_id}
        )

        all_steps = list(agent_steps) + [step_log]

        chart_data = None
        if gemini_client.is_configured and findings:
            try:
                chart_prompt = f"""
Analyze these research findings and determine if there are quantitative numbers/metrics that can be displayed as a chart:
{findings}

If yes, output ONLY a valid JSON:
{{
  "type": "bar",
  "title": "Short Descriptive Title",
  "data": [
    {{"name": "Category A", "value": 10}},
    {{"name": "Category B", "value": 20}}
  ]
}}
If no quantitative data, return: {{}}
"""
                extracted_chart = gemini_client.generate_json(chart_prompt, model=model)
                if extracted_chart and "data" in extracted_chart and len(extracted_chart["data"]) >= 2:
                    chart_data = extracted_chart
            except Exception as chart_err:
                logger.debug(f"Synthesizer chart extraction skipped: {chart_err}")
        elif findings:
            chart_data = AdvancedRAGPipeline._extract_chart_fallback(question, "\n".join(findings))

        report = ResearchReport(
            research_id=report_id,
            question=question,
            executive_summary=exec_summary,
            methodology=methodology,
            key_findings=findings,
            evidence_analysis=analysis.get("evidence_synthesis", ""),
            ai_interpretations=interpretations,
            conflicts_or_gaps=gaps,
            risks_and_limitations=risks,
            recommendations=recommendations,
            citations=citations,
            fact_check_results=fact_check_items,
            grounding_score=grounding_score,
            agent_steps=all_steps,
            chart_data=chart_data
        )

        return {
            "report": report,
            "step": step_log
        }


synthesizer_agent = SynthesizerAgent()
