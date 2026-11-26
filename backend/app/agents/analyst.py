import re
import time
from typing import Dict, Any, List, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.research import AgentExecutionStep


class AnalystAgent:
    """
    Analyst Agent: Synthesizes evidence into deep thematic insights,
    contrasts different pieces of evidence, grades source reliability,
    and cleanly separates document-stated facts from AI logical interpretations.
    """

    NUMERIC_SIGNAL_RE = re.compile(
        r"(?:\b\d+(?:\.\d+)?%|\$\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:INR|USD|EUR|days?|months?|minutes?|hours?|years?)\b)",
        re.IGNORECASE,
    )

    @staticmethod
    def _grade_source(source_name: str) -> str:
        low = (source_name or "").lower().strip()
        if low.startswith("web_") or low.endswith((".html", ".htm")):
            return "Grade C (Web / Secondary Source)"
        if low.endswith((".pdf", ".docx", ".pptx", ".rtf")):
            return "Grade A (Primary Document)"
        if low.endswith((".xlsx", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml")):
            return "Grade B (Structured Dataset/Config)"
        return "Grade B (Verified Workspace Text)"

    @classmethod
    def _extract_numeric_signals(cls, evidence_chunks: List[Dict[str, Any]]) -> List[str]:
        signals: List[str] = []
        seen = set()
        for c in evidence_chunks[:5]:
            src = c.get("source", "Document")
            page = c.get("page", 1)
            text = str(c.get("text", ""))
            for match in cls.NUMERIC_SIGNAL_RE.findall(text):
                clean_val = re.sub(r"\s+", " ", match).strip()
                key = (clean_val.lower(), src, page)
                if key not in seen:
                    seen.add(key)
                    signals.append(f"{clean_val} [{src}, p.{page}]")
                if len(signals) >= 6:
                    return signals
        return signals

    @classmethod
    def _local_analyze(cls, question: str, evidence_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        findings: List[str] = []
        sources = set()
        source_numbers: Dict[str, set] = {}
        for c in evidence_chunks[:5]:
            src = c.get("source", "Document")
            page = c.get("page", 1)
            sources.add(src)
            text = str(c.get("text", "")).strip()
            if text:
                findings.append(f"{text} [{src}, Page {page} | {cls._grade_source(src)}]")
                nums = {re.sub(r"\s+", " ", m).strip().lower() for m in cls.NUMERIC_SIGNAL_RE.findall(text)}
                if nums:
                    source_numbers.setdefault(src, set()).update(nums)

        synthesis = (
            f"Across {len(evidence_chunks)} retrieved passage(s) from {len(sources)} source(s), "
            f"direct evidence addressing \"{question}\" was extracted, source-graded (A-C), and ordered by hybrid & CrossEncoder relevance."
        )
        interpretations: List[str] = []
        signals = cls._extract_numeric_signals(evidence_chunks)
        if signals:
            interpretations.append(
                f"[TOOL-CHECKED METRICS] Extracted quantitative thresholds: {'; '.join(signals)}"
            )
        interpretations.append(
            "Extractive synthesis prioritizes verbatim passages with highest semantic and keyword overlap; verify full source context via citations for downstream policy decisions."
        )
        gaps: List[str] = []
        if len(sources) < 2:
            gaps.append("Only a single source contributed evidence; cross-source corroboration is limited.")
        elif len(source_numbers) >= 2:
            all_nums = set().union(*source_numbers.values())
            if len(all_nums) >= 2:
                gaps.append("Multiple numeric thresholds detected across sources; verify version precedence and effective dates.")
        return {
            "key_findings": findings or ["Evidence passages retrieved; review attached citations."],
            "evidence_synthesis": synthesis,
            "ai_interpretations": interpretations,
            "conflicts_or_gaps": gaps
        }

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
                    "evidence_synthesis": "Documents in the current workspace scope did not match the question requirements.",
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

        analysis_data = None
        if gemini_client.is_configured:
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
1. Extract 3-5 key findings directly backed by document evidence and tag each with its source reliability grade (`Grade A` primary documents, `Grade B` structured CSV/JSON/XLSX datasets, `Grade C` web/secondary pages).
2. Provide a cohesive evidence synthesis paragraph.
3. Explicitly list AI interpretations, quantitative thresholds/SLAs surfaced from the text, and strategic implications (clearly separated from factual quotes).
4. Identify any cross-document numerical variances, missing clauses, contradictions, or evidence gaps.

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
            try:
                analysis_data = gemini_client.generate_json(prompt, model=model)
            except Exception as e:
                logger.warning(f"[Analyst Agent] Gemini failed ({e}); using Local Extractive fallback.")

        if not analysis_data or not isinstance(analysis_data, dict):
            analysis_data = self._local_analyze(question, evidence_chunks)

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
