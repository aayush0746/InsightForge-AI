import re
from typing import List, Dict, Any, Optional, Tuple
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
    -> Grounded Context Assembly -> Multi-turn Memory -> Gemini Generation (or Local Extractive Mode) -> Citations & Chart Extraction.
    """

    @staticmethod
    def build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
        context_blocks: List[str] = []
        citations: List[Citation] = []

        for idx, chunk in enumerate(chunks, start=1):
            source = chunk.get("source", "unknown_doc.pdf")
            page = chunk.get("page", 1)
            cid = chunk.get("chunk_id", f"chunk_{idx}")
            doc_id = chunk.get("document_id")
            text = chunk.get("text", "").strip()
            score = chunk.get("rerank_score") if chunk.get("rerank_score") is not None else chunk.get("score")

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

    @staticmethod
    def _build_extractive_answer(
        question: str,
        selected_chunks: List[Dict[str, Any]],
        web_context_str: str = ""
    ) -> str:
        """
        Deterministic, zero-hallucination extractive synthesis used when GEMINI_API_KEY
        is not configured or unavailable.
        """
        lines = [
            f"Grounded Extractive Synthesis for: \"{question}\"",
            "(Running in Local Extractive Mode — configure GEMINI_API_KEY in .env for generative synthesis.)",
            ""
        ]
        for idx, chunk in enumerate(selected_chunks, start=1):
            src = chunk.get("source", "Document")
            page = chunk.get("page", 1)
            excerpt = chunk.get("text", "").strip()
            lines.append(f"{idx}. {excerpt} [{src}, Page {page}]")

        if web_context_str:
            lines.append("\nLive Web References:")
            lines.append(web_context_str[:1200])

        return "\n".join(lines)

    @staticmethod
    def _extract_chart_fallback(question: str, text: str) -> Optional[Dict[str, Any]]:
        if not any(w in question.lower() for w in ["chart", "graph", "compare", "breakdown", "stipend", "salary", "score", "percentage", "rate"]):
            return None
        matches = re.findall(r"([A-Za-z][A-Za-z0-9 _/-]{2,24})[:=\s]+(\d+(?:\.\d+)?)\s*%?", text)
        data = []
        seen = set()
        for label, num in matches:
            clean_label = label.strip(" -:")
            if clean_label.lower() in seen or clean_label.lower() in ("page", "source", "chunk"):
                continue
            seen.add(clean_label.lower())
            try:
                data.append({"name": clean_label[:24], "value": float(num)})
            except ValueError:
                continue
            if len(data) >= 6:
                break
        if len(data) >= 2:
            return {
                "type": "bar",
                "title": "Extracted Quantitative Metrics",
                "data": data
            }
        return None

    @classmethod
    def answer_question(
        cls,
        question: str,
        document_ids: Optional[List[str]] = None,
        use_reranker: bool = True,
        enable_web_search: bool = False,
        top_k: Optional[int] = None,
        top_n: Optional[int] = None,
        model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ChatResponse:
        effective_top_k = top_k if top_k is not None else settings.DEFAULT_RETRIEVAL_TOP_K
        effective_top_n = top_n if top_n is not None else settings.DEFAULT_RERANK_TOP_N

        logger.info(
            f"RAG query received: '{question}' (history turns: {len(history) if history else 0}, web search: {enable_web_search})"
        )

        candidates = hybrid_search.search(
            query=question,
            top_k=effective_top_k,
            document_ids=document_ids,
            alpha=settings.DEFAULT_HYBRID_ALPHA,
            enable_query_rewrite=bool(history),
            history=history
        )

        retrieved_count = len(candidates)

        web_context_str = ""
        web_citations = []
        if enable_web_search:
            web_context_str, web_citations = live_web_search.search(question, max_results=3)

        if not candidates and not web_citations:
            return ChatResponse(
                question=question,
                answer="Information not available in the provided documents. No matching passages were found in the selected workspace scope.",
                citations=[],
                retrieved_chunks_count=0,
                reranked_chunks_count=0,
                is_grounded=False,
                unanswered_reason="No matching document evidence found in the current workspace scope."
            )

        if use_reranker and candidates:
            selected_chunks = reranker.rerank(
                query=question,
                chunks=candidates,
                top_n=effective_top_n
            )
        else:
            selected_chunks = candidates[:effective_top_n]

        reranked_count = len(selected_chunks)
        context_str, citations = cls.build_context(selected_chunks)
        if web_context_str:
            context_str += (
                "\n\n============================================================\n"
                "LIVE WEB SEARCH RESULTS (REAL-TIME EXTERNAL DATA):\n"
                "============================================================\n"
                f"{web_context_str}"
            )
            citations.extend(web_citations)

        history_str = ""
        if history:
            formatted_turns = []
            for h in history[-4:]:
                role = "User" if h.get("role") == "user" else "Assistant"
                formatted_turns.append(f"{role}: {h.get('content', '')}")
            history_str = "PREVIOUS CONVERSATION HISTORY:\n" + "\n".join(formatted_turns) + "\n\n"

        answer_text: Optional[str] = None
        if gemini_client.is_configured:
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
            try:
                answer_text = gemini_client.generate(prompt=prompt, model=model)
            except Exception as llm_err:
                logger.warning(f"Gemini generation unavailable ({llm_err}); falling back to Local Extractive Mode.")

        if answer_text is None:
            answer_text = cls._build_extractive_answer(question, selected_chunks, web_context_str)

        is_grounded = True
        unanswered = None
        lower_answer = answer_text.lower()
        if "information not available" in lower_answer or "not mentioned in the provided documents" in lower_answer:
            is_grounded = False
            unanswered = "The uploaded documents do not contain sufficient evidence to answer this question."

        chart_data = None
        if gemini_client.is_configured and any(word in question.lower() for word in ["chart", "graph", "compare", "breakdown", "stipend", "salary", "score", "percentage", "rate"]):
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
        elif not gemini_client.is_configured:
            chart_data = cls._extract_chart_fallback(question, answer_text)

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
