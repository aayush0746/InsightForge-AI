from typing import List, Dict, Any, Tuple
from ddgs import DDGS
from backend.app.core.logger import logger
from backend.app.schemas.chat import Citation

class LiveWebSearch:
    """
    Real-time web search aggregator using DDGS.
    Retrieves latest news, market data, and external verification.
    """
    @staticmethod
    def search(query: str, max_results: int = 4) -> Tuple[str, List[Citation]]:
        logger.info(f"Conducting live web search for: '{query}' (limit: {max_results})")
        web_context_blocks = []
        citations = []

        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=max_results)
            if not results:
                return "", []

            for idx, r in enumerate(results, start=1):
                title = r.get("title", f"Web Source {idx}")
                href = r.get("href", "")
                snippet = r.get("body", "")

                web_context_blocks.append(
                    f"[Live Web Result {idx}]: {title}\nURL: {href}\nSummary: {snippet}"
                )

                citations.append(
                    Citation(
                        source_filename=f"Web: {title[:28]}...",
                        page_number=1,
                        chunk_id=href,
                        snippet=snippet,
                        relevance_score=0.95
                    )
                )

            formatted_context = "\n\n".join(web_context_blocks)
            logger.info(f"Live web search returned {len(citations)} external sources.")
            return formatted_context, citations
        except Exception as e:
            logger.warning(f"Live web search failed or timed out: {e}")
            return "", []

live_web_search = LiveWebSearch()

