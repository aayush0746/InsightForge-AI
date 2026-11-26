from typing import Optional, List, Dict, Any
from backend.app.core.logger import logger
from backend.app.schemas.research import ResearchReport
from backend.app.agents.orchestrator import agent_orchestrator
from backend.app.core.gemini import gemini_client


class ResearchService:
    """
    Coordinates multi-agent research operations, report retrieval, and audio briefings.
    """

    def execute_deep_research(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        max_subtasks: int = 4,
        deep_analysis: bool = True,
        enable_web_search: bool = False,
        user_id: Optional[str] = None
    ) -> ResearchReport:
        logger.info(f"Initiating deep multi-agent research for: '{question}' (web={enable_web_search})")
        return agent_orchestrator.run_research(
            question=question,
            document_ids=document_ids,
            max_subtasks=max_subtasks,
            deep_analysis=deep_analysis,
            enable_web_search=enable_web_search,
            user_id=user_id
        )

    def get_report(self, research_id: str, user_id: Optional[str] = None) -> Optional[ResearchReport]:
        return agent_orchestrator.get_report(research_id, user_id=user_id)

    def list_reports(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        raw_reports = agent_orchestrator.load_reports(user_id=user_id)
        summaries = []
        for rid, item in raw_reports.items():
            rep_uid = item.get("user_id")
            if user_id is not None and rep_uid != user_id:
                continue
            if user_id is None and rep_uid is not None:
                continue

            summaries.append({
                "research_id": rid,
                "question": item.get("question"),
                "created_at": item.get("created_at"),
                "grounding_score": item.get("grounding_score", 100.0),
                "key_findings_count": len(item.get("key_findings", [])),
                "citations_count": len(item.get("citations", [])),
                "user_id": rep_uid
            })
        summaries.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return summaries

    def generate_podcast_script(self, text: str, topic: str = "Research Briefing") -> str:
        """
        Transforms research text or report findings into a spoken executive podcast briefing script.
        Falls back cleanly to a structured spoken script when GEMINI_API_KEY is not configured.
        """
        if gemini_client.is_configured:
            prompt = f"""
You are an executive podcast host and intelligence director for InsightForge AI.
Turn the following research findings into an engaging, professional, 2-minute spoken audio briefing script.
The script will be spoken aloud to a busy executive or student commuting.

Topic: {topic}
Source Research / Findings:
{text[:4500]}

Guidelines:
1. Open with an engaging hook: "Welcome to your InsightForge Executive Briefing. Today, we're examining..."
2. Speak conversationally and directly to the listener as a trusted analyst.
3. Transform dense citations, legal terms, or percentages into clear, narrative insights.
4. Conclude with a crisp bottom-line verdict: "And that's your executive briefing. Stay ahead, and have a productive day."
5. Output ONLY the pure spoken script. Do NOT include markdown headers, stage directions like [Music], sound effects, or bullet points.
"""
            try:
                return gemini_client.generate(prompt)
            except Exception as e:
                logger.warning(f"Gemini podcast script generation failed ({e}); using local formatter.")

        clean_body = " ".join(line.strip("•-*# ") for line in text[:3500].splitlines() if line.strip())
        return (
            f"Welcome to your InsightForge Executive Briefing. Today, we're examining {topic}. "
            f"Here are the key verified insights from your workspace documents. {clean_body} "
            f"And that's your executive briefing. Stay ahead, and have a productive day."
        )


research_service = ResearchService()
