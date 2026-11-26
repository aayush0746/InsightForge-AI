import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger


class TextChunker:
    """
    Paragraph- and sentence-aware text chunker with configurable word overlap
    and automatic word-window splitting for long tables/code/JSON blocks.
    """
    def __init__(
        self,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP,
        overlap_sentences: Optional[int] = None,
    ):
        self.chunk_size = max(10, int(chunk_size))
        self.chunk_overlap = max(0, min(int(chunk_overlap), self.chunk_size - 1))
        self.overlap_sentences = overlap_sentences

    def _split_long_segment(self, text: str) -> List[str]:
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        step = max(1, self.chunk_size - self.chunk_overlap)
        segments: List[str] = []
        for idx in range(0, len(words), step):
            window = words[idx:idx + self.chunk_size]
            if window:
                segments.append(" ".join(window))
            if idx + self.chunk_size >= len(words):
                break
        return segments

    def _carry_overlap(self, sentences: List[str]) -> List[str]:
        if self.overlap_sentences is not None and self.overlap_sentences > 0:
            return sentences[-self.overlap_sentences:]
        if self.chunk_overlap <= 0:
            return []
        carried: List[str] = []
        word_total = 0
        for s in reversed(sentences):
            w = len(s.split())
            if carried and word_total + w > self.chunk_overlap:
                break
            carried.insert(0, s)
            word_total += w
            if word_total >= self.chunk_overlap:
                break
        return carried

    def chunk_pages(
        self,
        pages: List[Dict[str, Any]],
        document_id: str,
        source_name: str
    ) -> List[Dict[str, Any]]:
        """
        Takes extracted pages and produces structured chunks with full metadata.
        """
        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for page in pages:
            page_num = page["page"]
            page_text = str(page["text"])

            paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [page_text]

            for paragraph in paragraphs:
                clean_para = re.sub(r"\s+", " ", paragraph).strip()
                if not clean_para:
                    continue

                raw_sentences = re.split(r"(?<=[.!?])\s+", clean_para)
                sentences: List[str] = []
                for s in raw_sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(s.split()) > self.chunk_size:
                        sentences.extend(self._split_long_segment(s))
                    else:
                        sentences.append(s)

                current_sentences: List[str] = []
                current_word_count = 0

                for s in sentences:
                    s_words = len(s.split())
                    if current_sentences and (current_word_count + s_words > self.chunk_size):
                        chunk_text = " ".join(current_sentences)
                        chunk_id = f"{document_id}_p{page_num}_c{chunk_idx}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "source": source_name,
                            "page": page_num,
                            "text": chunk_text,
                            "word_count": current_word_count,
                            "timestamp": now_iso
                        })
                        chunk_idx += 1

                        current_sentences = self._carry_overlap(current_sentences)
                        current_word_count = sum(len(x.split()) for x in current_sentences)

                    current_sentences.append(s)
                    current_word_count += s_words

                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    if current_word_count > 3 or not chunks:
                        chunk_id = f"{document_id}_p{page_num}_c{chunk_idx}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "source": source_name,
                            "page": page_num,
                            "text": chunk_text,
                            "word_count": current_word_count,
                            "timestamp": now_iso
                        })
                        chunk_idx += 1

        logger.info(f"Chunked document '{source_name}' ({len(pages)} pages) into {len(chunks)} chunks.")
        return chunks
