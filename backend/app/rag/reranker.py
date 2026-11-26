import os
import re
from typing import List, Dict, Any, Optional
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
        self._model = None
        self._loaded = False

    @property
    def is_enabled(self) -> bool:
        env_override = os.environ.get("DISABLE_CROSS_ENCODER")
        if env_override is not None:
            return env_override.lower() not in ("true", "1", "yes")
        return not settings.DISABLE_CROSS_ENCODER

    @property
    def model(self):
        if not self.is_enabled:
            return None
        if not self._loaded:
            self._loaded = True
            try:
                import torch
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder reranker on demand: {settings.CROSS_ENCODER_MODEL_NAME}")
                self._model = CrossEncoder(settings.CROSS_ENCODER_MODEL_NAME)
                logger.info("CrossEncoder model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder ({e}). Using hybrid rank fallback.")
                self._model = None
        return self._model

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int = settings.DEFAULT_RERANK_TOP_N
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks according to CrossEncoder relevance scores,
        or hybrid rank + lexical term overlap when CrossEncoder is disabled/unavailable.
        """
        if not chunks:
            return []

        if not self.model:
            logger.info("CrossEncoder not active. Using hybrid score & term overlap fallback.")
            stops = {"the", "is", "a", "an", "and", "or", "in", "on", "for", "of", "to", "at", "by", "what", "are"}
            q_words = {w.rstrip("s") for w in re.findall(r"\w+", query.lower()) if w not in stops}

            def fallback_score(c: Dict[str, Any]):
                existing_score = float(c.get("hybrid_score") or c.get("score") or 0.0)
                c_words = {w.rstrip("s") for w in re.findall(r"\w+", c.get("text", "").lower())}
                overlap = len(q_words.intersection(c_words))
                return (existing_score, overlap)

            return sorted(chunks, key=fallback_score, reverse=True)[:top_n]

        pairs = [(query, chunk["text"]) for chunk in chunks]
        try:
            scores = self.model.predict(pairs)
            reranked_chunks = []
            for chunk, score in zip(chunks, scores):
                chunk_copy = dict(chunk)
                chunk_copy["rerank_score"] = float(score)
                chunk_copy["score"] = float(score)
                reranked_chunks.append(chunk_copy)

            reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
            logger.info(f"Reranked {len(chunks)} chunks down to top {top_n}.")
            return reranked_chunks[:top_n]
        except Exception as e:
            logger.error(f"CrossEncoder prediction failed: {e}. Falling back to original ranking.")
            return chunks[:top_n]


reranker = Reranker()
