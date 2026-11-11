from typing import List, Dict, Any, Optional, Tuple
import json
import re
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.gemini import gemini_client
from backend.app.rag.hybrid_search import hybrid_search
from backend.app.rag.reranker import reranker
from backend.app.rag.web_search import live_web_search
from backend.app.schemas.chat import Citation, ChatResponse

class AdvancedRAGPipeline:
    """
    End-to-End Advanced RAG Pipeline:
    Query Rewriting -> Hybrid Retrieval (Dense + BM25) -> CrossEncoder Reranking
    -> Grounded Context Assembly -> Multi-turn Memory -> Gemini Generation -> Citations & Chart Extraction.
    """

    @staticmethod
    def build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
        """
        Builds clear grounded context format with numbered sources,
        and constructs Citation objects with document_id and page numbers.
        """
        context_blocks: List[str] = []
        citations: List[Citation] = []

        for idx, chunk in enumerate(chunks, start=1):
            source = chunk.get("source", "unknown_doc.pdf")
            page = chunk.get("page", 1)
            cid = chunk.get("chunk_id", f"chunk_{idx}")
            doc_id = chunk.get("document_id")
            text = chunk.get("text", "").strip()
            score = chunk.get("score") or chunk.get("rerank_score")

            context_blocks.append(
                f"[Source {idx}]: Document: {source} (ID: {doc_id}) | Page: {page} | Chunk ID: {cid}\n"
                f"{text}"
            )

            citations.append(
                Citation(
                    source_filename=source,
                    page_number=page,
                    chunk_id=cid,
                    document_id=doc_id,
                    snippet=text[:250] + ("..." if len(text) > 250 else ""),
                    relevance_score=score
                )
            )

        context_str = "\n\n".join(context_blocks)
        return context_str, citations

    @classmethod
    def answer_question(
        cls,
        question: str,
        document_ids: Optional[List[str]] = None,
        use_reranker: bool = True,
        enable_web_search: bool = False,
        top_k: int = settings.DEFAULT_RETRIEVAL_TOP_K,
        top_n: int = settings.DEFAULT_RERANK_TOP_N,
        model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ChatResponse:
        """
        Executes complete RAG workflow with multi-turn history and optional Live Web Search.
        """
        logger.info(f"RAG query received: '{question}' (history turns: {len(history) if history else 0}, web search: {enable_web_search})")

        # 1. Hybrid Search (with history resolution for follow-ups)
        candidates = hybrid_search.search(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
            enable_query_rewrite=bool(history),
            history=history
        )

        retrieved_count = len(candidates)

        # 2. Live Web Search if enabled
        web_context_str = ""
        web_citations = []
        if enable_web_search:
            web_context_str, web_citations = live_web_search.search(question, max_results=3)

        if not candidates and not web_citations:
            return ChatResponse(
                question=question,
                answer="No relevant documents or web sources were found to answer this question.",
                citations=[],
                retrieved_chunks_count=0,
                reranked_chunks_count=0,
                is_grounded=False,
                unanswered_reason="No documents available in vector store."
            )

        # 3. CrossEncoder Reranking
        if use_reranker and candidates:
            selected_chunks = reranker.rerank(
                query=question,
                chunks=candidates,
                top_n=top_n
            )
        else:
            selected_chunks = candidates[:top_n]

        reranked_count = len(selected_chunks)

        # 4. Context Construction
        context_str, citations = cls.build_context(selected_chunks)
        if web_context_str:
            context_str += f"\n\n============================================================\nLIVE WEB SEARCH RESULTS (REAL-TIME EXTERNAL DATA):\n============================================================\n{web_context_str}"
            citations.extend(web_citations)

        # 5. Multi-turn History Context
        history_str = ""
        if history:
            formatted_turns = []
            for h in history[-4:]:  # Keep last 4 turns for concise context
                role = "User" if h.get("role") == "user" else "Assistant"
                formatted_turns.append(f"{role}: {h.get('content', '')}")
            history_str = "PREVIOUS CONVERSATION HISTORY:\n" + "\n".join(formatted_turns) + "\n\n"

        # 5. Strict Grounding Prompt
        prompt = f"""
You are InsightForge AI, an expert research assistant.
Answer the user question using ONLY the provided document context below.

CRITICAL RULES:
1. Strict Grounding: Rely EXCLUSIVELY on the facts stated in the context. Do NOT extrapolate or assume.
2. In-text Citations: Whenever you state a fact, immediately cite its source in brackets, e.g. [Document.pdf, Page 2].
3. Unavailable Information: If the context does not contain sufficient facts to answer the question, state clearly:
   "Information not available in the provided documents."
   Do NOT attempt to guess or hallucinate an answer.
4. Professional tone: Be concise, structured, and factual.

{history_str}============================================================
DOCUMENT CONTEXT:
============================================================
{context_str}

============================================================
USER QUESTION:
============================================================
{question}

Provide your grounded answer with citations:
"""

        # 6. Gemini Generation
        answer_text = gemini_client.generate(prompt=prompt, model=model)

        # 7. Check for ungrounded / missing info signal
        is_grounded = True
        unanswered = None
        lower_answer = answer_text.lower()
        if "information not available" in lower_answer or "not mentioned in the provided documents" in lower_answer:
            is_grounded = False
            unanswered = "The uploaded documents do not contain sufficient evidence to answer this question."

        # 8. Check if quantitative data exists for chart visualization
        chart_data = None
        if any(word in question.lower() for word in ["chart", "graph", "compare", "breakdown", "stipend", "salary", "score", "percentage", "rate"]):
            try:
                chart_prompt = f"""
Analyze this answer and determine if it contains 2 or more quantitative numeric comparisons or metrics that can be visualized as a chart.
Answer text:
{answer_text}

If yes, output ONLY a valid JSON object matching:
{{
  "type": "bar",
  "title": "Short Descriptive Title",
  "data": [
    {{"name": "Category A", "value": 10}},
    {{"name": "Category B", "value": 25}}
  ]
}}
If no quantitative data is suitable, return: {{}}
"""
                extracted_chart = gemini_client.generate_json(chart_prompt)
                if extracted_chart and "data" in extracted_chart and len(extracted_chart["data"]) >= 2:
                    chart_data = extracted_chart
            except Exception as chart_err:
                logger.debug(f"Chart extraction skipped: {chart_err}")

        return ChatResponse(
            question=question,
            answer=answer_text,
            citations=citations,
            retrieved_chunks_count=retrieved_count,
            reranked_chunks_count=reranked_count,
            is_grounded=is_grounded,
            unanswered_reason=unanswered,
            chart_data=chart_data
        )

rag_pipeline = AdvancedRAGPipeline()
