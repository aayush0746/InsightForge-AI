import time
from typing import Dict, Any, List, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.research import AgentExecutionStep

class AnalystAgent:
    """
    Analyst Agent: Synthesizes evidence into deep thematic insights,
    contrasts different pieces of evidence, and cleanly separates
    document-stated facts from AI logical interpretations.
    """

    def analyze(
        self,
        question: str,
        evidence_chunks: List[Dict[str, Any]],
        plan: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"[Analyst Agent] Analyzing {len(evidence_chunks)} evidence chunks...")

        if not evidence_chunks:
            return {
                "analysis": {
                    "key_findings": ["No document evidence was available for analysis."],
                    "evidence_synthesis": "Documents in the system did not match the question requirements.",
                    "ai_interpretations": [],
                    "conflicts_or_gaps": ["Relevant data missing from uploaded library."]
                },
                "step": AgentExecutionStep(
                    agent_name="Analyst Agent",
                    title="Analysis completed with no evidence",
                    status="completed",
                    details="Zero evidence chunks were available.",
                    execution_time_seconds=0.1
                )
            }

        # Build evidence text for prompt
        evidence_text = "\n\n".join([
            f"[Source {i+1}] ({c.get('source')}, Page {c.get('page')}, ID: {c.get('chunk_id')}):\n{c.get('text')}"
            for i, c in enumerate(evidence_chunks)
        ])

        prompt = f"""
You are the Analyst Agent in an Agentic AI Research System.
Your job is to rigorously analyze the retrieved evidence chunks and extract deep insights.

Research Question: {question}

Retrieved Evidence:
{evidence_text}

Instructions:
1. Extract 3-5 key findings directly backed by document evidence.
2. Provide a cohesive evidence synthesis paragraph.
3. Explicitly list AI interpretations / strategic implications (clearly separate these from factual quotes).
4. Identify any contradictions, uncertainties, or gaps in the provided evidence.

Return ONLY valid JSON matching this schema:
{{
    "key_findings": [
        "Finding 1 with explicit reference to source...",
        "Finding 2..."
    ],
    "evidence_synthesis": "Comprehensive narrative analyzing the patterns...",
    "ai_interpretations": [
        "Interpretation 1 (derived implication)...",
        "Interpretation 2..."
    ],
    "conflicts_or_gaps": [
        "Gap or conflicting information 1..."
    ]
}}
"""
        analysis_data = gemini_client.generate_json(prompt, model=model)
        duration = round(time.time() - start_time, 2)

        step_log = AgentExecutionStep(
            agent_name="Analyst Agent",
            title="Generated deep thematic insights and evidence synthesis",
            status="completed",
            details=f"Formulated {len(analysis_data.get('key_findings', []))} key findings and identified {len(analysis_data.get('conflicts_or_gaps', []))} potential evidence gaps.",
            execution_time_seconds=duration,
            data=analysis_data
        )

        return {
            "analysis": analysis_data,
            "step": step_log
        }

analyst_agent = AnalystAgent()

