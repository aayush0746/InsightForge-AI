from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
from backend.app.core.config import settings
from backend.app.core.logger import logger

class Reranker:
    """
    CrossEncoder-based neural reranker.
    Cross-attention computes exact token-to-token semantic relevance
    between query and document chunks, overcoming bi-encoder representation limits.
    """
    _instance: Optional["Reranker"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Reranker, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        try:
            logger.info(f"Loading CrossEncoder reranker: {settings.CROSS_ENCODER_MODEL_NAME}")
            self.model = CrossEncoder(settings.CROSS_ENCODER_MODEL_NAME)
            logger.info("CrossEncoder model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int = settings.DEFAULT_RERANK_TOP_N
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks according to CrossEncoder relevance scores.
        """
        if not chunks:
            return []

        if len(chunks) <= top_n and not self.model:
            return chunks

        if not self.model:
            logger.warning("CrossEncoder not available, sorting by initial retrieval score.")
            return sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]

        # Prepare pairs: [(query, chunk_text), ...]
        pairs = [(query, chunk["text"]) for chunk in chunks]

        try:
            scores = self.model.predict(pairs)
            
            # Attach rerank score and sort
            reranked_chunks = []
            for chunk, score in zip(chunks, scores):
                chunk_copy = dict(chunk)
                chunk_copy["rerank_score"] = float(score)
                chunk_copy["score"] = float(score)  # updated primary score
                reranked_chunks.append(chunk_copy)

            reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
            logger.info(f"Reranked {len(chunks)} chunks down to top {top_n}.")
            return reranked_chunks[:top_n]

        except Exception as e:
            logger.error(f"CrossEncoder prediction failed: {e}. Falling back to original ranking.")
            return chunks[:top_n]

reranker = Reranker()

