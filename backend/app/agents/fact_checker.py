import time
from typing import Dict, Any, List, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.research import AgentExecutionStep, FactCheckItem

class FactCheckerAgent:
    """
    Fact Checker Agent: Rigorously verifies every factual claim against
    retrieved source documents to eliminate hallucinations, ensuring
    strict attribution and computing an empirical grounding score.
    """

    def verify_claims(
        self,
        key_findings: List[str],
        evidence_chunks: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"[Fact Checker Agent] Verifying {len(key_findings)} claims against evidence...")

        if not key_findings or not evidence_chunks:
            return {
                "fact_checks": [],
                "grounding_score": 0.0,
                "step": AgentExecutionStep(
                    agent_name="Fact Checker Agent",
                    title="No claims or evidence to verify",
                    status="completed",
                    details="Grounding score evaluated to 0.0%",
                    execution_time_seconds=0.1
                )
            }

        evidence_corpus = "\n\n".join([
            f"Source [{c.get('source')}, Page {c.get('page')}]:\n{c.get('text')}"
            for c in evidence_chunks
        ])

        claims_list = "\n".join([f"{i+1}. {claim}" for i, claim in enumerate(key_findings)])

        prompt = f"""
You are the Fact Checker Agent.
Evaluate whether each stated claim is directly supported by the document evidence.

EVIDENCE CORPUS:
{evidence_corpus}

CLAIMS TO VERIFY:
{claims_list}

Rules:
- Mark is_supported = true ONLY if the evidence explicitly states or unambiguously proves the claim.
- If the claim introduces outside numbers, names, or assumptions not found in the evidence, mark is_supported = false.
- Confidence must be between 0.0 and 1.0.
- Point to the specific [filename, page] if supported.

Return ONLY valid JSON matching this schema:
{{
    "items": [
        {{
            "claim": "The exact text of the claim",
            "is_supported": true,
            "confidence": 0.95,
            "source_citation": "filename.pdf, Page 1",
            "note": "Directly confirmed in section X."
        }}
    ]
}}
"""
        result = gemini_client.generate_json(prompt, model=model)
        items_data = result.get("items", [])

        fact_check_items: List[FactCheckItem] = []
        supported_count = 0

        for item in items_data:
            fc = FactCheckItem(
                claim=item.get("claim", ""),
                is_supported=bool(item.get("is_supported", False)),
                confidence=float(item.get("confidence", 0.5)),
                source_citation=item.get("source_citation"),
                note=item.get("note", "")
            )
            fact_check_items.append(fc)
            if fc.is_supported:
                supported_count += 1

        total = len(fact_check_items)
        grounding_score = round((supported_count / total * 100.0), 1) if total > 0 else 100.0

        duration = round(time.time() - start_time, 2)
        step_log = AgentExecutionStep(
            agent_name="Fact Checker Agent",
            title=f"Verified factual grounding: {grounding_score}% verified",
            status="completed",
            details=f"{supported_count}/{total} claims substantiated with direct document citations.",
            execution_time_seconds=duration,
            data={
                "grounding_score": grounding_score,
                "supported_count": supported_count,
                "total_claims": total
            }
        )

        return {
            "fact_checks": fact_check_items,
            "grounding_score": grounding_score,
            "step": step_log
        }

fact_checker_agent = FactCheckerAgent()

