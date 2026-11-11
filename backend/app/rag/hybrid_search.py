import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.gemini import gemini_client
from backend.app.rag.vector_store import vector_store

class HybridSearchEngine:
    """
    Hybrid Search combining BM25 keyword matching and dense vector search
    with Reciprocal Rank Fusion (RRF) and query rewriting.
    """

    @staticmethod
    def rewrite_query(original_query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Rewrites conversational or ambiguous queries into search-optimized terms.
        Resolves follow-ups (e.g. 'Elaborate on point 2') using conversation context.
        """
        history_str = ""
        if history:
            turns = []
            for h in history[-3:]:
                role = "User" if h.get("role") == "user" else "Assistant"
                turns.append(f"{role}: {h.get('content', '')[:300]}")
            history_str = "CONVERSATION HISTORY:\n" + "\n".join(turns) + "\n\n"

        if len(original_query.split()) > 18 and not history_str:
            # Already detailed
            return original_query

        prompt = f"""
You are an expert search query optimizer for a RAG system.
Given the user's research question and prior conversation history (if any), produce an expanded, standalone, keyword-rich search query.
If the question is a follow-up (e.g., "Elaborate on point 2", "Rewrite that table", "What about liabilities?"), resolve references into a complete standalone search query based on the history.

{history_str}User Question: {original_query}

Respond ONLY with the rewritten search query. Do not add quotes or explanations.
"""
        try:
            rewritten = gemini_client.generate(prompt).strip()
            if rewritten and len(rewritten) < 300:
                logger.info(f"Query rewritten: '{original_query}' -> '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite skipped due to: {e}")

        return original_query

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    @classmethod
    def search(
        cls,
        query: str,
        top_k: int = settings.DEFAULT_RETRIEVAL_TOP_K,
        document_ids: Optional[List[str]] = None,
        alpha: float = settings.DEFAULT_HYBRID_ALPHA,
        enable_query_rewrite: bool = True,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval:
        1. Query rewriting (if enabled or if history exists)
        2. Semantic dense search (ChromaDB)
        3. Lexical keyword search (BM25)
        4. Reciprocal Rank Fusion (RRF) merging
        """
        if enable_query_rewrite or history:
            search_query = cls.rewrite_query(query, history=history)
        else:
            search_query = query

        # 1. Semantic retrieval
        semantic_results = vector_store.search(
            query=search_query,
            top_k=top_k * 2,  # retrieve extra candidates for fusion
            document_ids=document_ids
        )

        # 2. Get all candidate chunks for BM25
        all_chunks = vector_store.get_all_chunks(document_ids=document_ids)
        if not all_chunks:
            return semantic_results[:top_k]

        # Tokenize corpus for BM25
        tokenized_corpus = [cls.tokenize(c["text"]) for c in all_chunks]
        tokenized_query = cls.tokenize(search_query)

        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)

        # Map chunk_id to BM25 rank
        bm25_ranked = sorted(
            zip(all_chunks, bm25_scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k * 2]

        # 3. Reciprocal Rank Fusion (RRF)
        # score = 1 / (60 + rank_dense) + 1 / (60 + rank_bm25)
        rrf_constant = 60
        fused_scores: Dict[str, float] = {}
        chunks_by_id: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(semantic_results):
            cid = item["chunk_id"]
            chunks_by_id[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (alpha * (1.0 / (rrf_constant + rank + 1)))

        for rank, (item, b_score) in enumerate(bm25_ranked):
            if b_score <= 0:
                continue
            cid = item["chunk_id"]
            if cid not in chunks_by_id:
                chunks_by_id[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + ((1.0 - alpha) * (1.0 / (rrf_constant + rank + 1)))

        # Sort by fused score
        sorted_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)
        
        final_candidates: List[Dict[str, Any]] = []
        for cid in sorted_ids[:top_k]:
            chunk = dict(chunks_by_id[cid])
            chunk["hybrid_score"] = round(fused_scores[cid], 5)
            final_candidates.append(chunk)

        logger.info(f"Hybrid search returned {len(final_candidates)} candidates for query: '{query[:40]}...'")
        return final_candidates

hybrid_search = HybridSearchEngine()

