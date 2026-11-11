import time
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.rag.hybrid_search import hybrid_search
from backend.app.rag.reranker import reranker
from backend.app.rag.web_search import live_web_search
from backend.app.schemas.research import AgentExecutionStep
from backend.app.schemas.chat import Citation

class ResearchAgent:
    """
    Research Agent: Executes multi-query retrieval across documents,
    aggregates evidence, eliminates duplicate chunks, and compiles citations.
    """

    def gather_evidence(
        self,
        subtasks: List[Dict[str, Any]],
        document_ids: Optional[List[str]] = None,
        enable_web_search: bool = False,
        main_question: str = ""
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"[Research Agent] Executing retrieval across {len(subtasks)} subtasks (web: {enable_web_search})...")

        all_chunks: List[Dict[str, Any]] = []
        seen_chunk_ids = set()
        citations: List[Citation] = []

        candidate_pool: List[Dict[str, Any]] = []
        for subtask in subtasks:
            query = subtask.get("search_query") or subtask.get("title", "")
            if not query:
                continue

            # Hybrid retrieval
            subtask_candidates = hybrid_search.search(
                query=query,
                top_k=settings.DEFAULT_RETRIEVAL_TOP_K,
                document_ids=document_ids,
                enable_query_rewrite=False
            )
            for c in subtask_candidates:
                cid = c["chunk_id"]
                if cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    c_copy = dict(c)
                    c_copy["associated_subtask"] = subtask.get("title")
                    candidate_pool.append(c_copy)

        # Batch reranking in a single fast pass
        primary_query = subtasks[0].get("search_query") if subtasks else ""
        if candidate_pool:
            top_chunks = reranker.rerank(
                query=primary_query,
                chunks=candidate_pool,
                top_n=settings.DEFAULT_RERANK_TOP_N * len(subtasks)
            )
        else:
            top_chunks = []

        for chunk in top_chunks:
            all_chunks.append(chunk)
            citations.append(
                Citation(
                    source_filename=chunk["source"],
                    page_number=chunk["page"],
                    chunk_id=chunk["chunk_id"],
                    snippet=chunk["text"][:250] + ("..." if len(chunk["text"]) > 250 else ""),
                    relevance_score=chunk.get("rerank_score") or chunk.get("score")
                )
            )

        # Incorporate Live Web Search evidence if enabled
        if enable_web_search:
            search_target = main_question or primary_query
            web_ctx, web_citations = live_web_search.search(search_target, max_results=3)
            citations.extend(web_citations)
            if web_ctx:
                all_chunks.append({
                    "chunk_id": "web_live_results",
                    "source": "Live Web Search",
                    "page": 1,
                    "text": web_ctx,
                    "score": 0.95
                })

        duration = round(time.time() - start_time, 2)
        step_log = AgentExecutionStep(
            agent_name="Research Agent",
            title=f"Retrieved and reranked {len(all_chunks)} unique evidence chunks",
            status="completed",
            details=f"Gathered supporting text from {len({c.source_filename for c in citations})} documents across {len(subtasks)} subtasks.",
            execution_time_seconds=duration,
            data={
                "total_chunks_collected": len(all_chunks),
                "unique_sources": list({c.source_filename for c in citations})
            }
        )

        return {
            "evidence_chunks": all_chunks,
            "citations": citations,
            "step": step_log
        }

research_agent = ResearchAgent()

