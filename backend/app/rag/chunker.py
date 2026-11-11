import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logger import logger

class TextChunker:
    """
    Intelligent paragraph- and sentence-aware text chunker.
    Preserves document structure, avoids breaking sentences in the middle,
    and maintains consistent overlap to avoid context loss at chunk borders.
    """
    def __init__(
        self,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        overlap_sentences: int = 1
    ):
        self.chunk_size = chunk_size
        self.overlap_sentences = overlap_sentences

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
            page_text = page["text"]

            # Split by paragraphs first
            paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [page_text]

            for paragraph in paragraphs:
                # Normalize internal spaces
                clean_para = re.sub(r"\s+", " ", paragraph).strip()
                if not clean_para:
                    continue

                # Split paragraph into sentences
                sentences = re.split(r"(?<=[.!?])\s+", clean_para)
                sentences = [s.strip() for s in sentences if s.strip()]

                current_sentences: List[str] = []
                current_word_count = 0

                for s in sentences:
                    s_words = len(s.split())

                    # If adding sentence exceeds chunk_size and we already have content
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

                        # Keep overlap sentences
                        current_sentences = current_sentences[-self.overlap_sentences:]
                        current_word_count = sum(len(x.split()) for x in current_sentences)

                    current_sentences.append(s)
                    current_word_count += s_words

                # Flush remaining sentences in paragraph
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    # Don't add tiny duplicate overlap fragments if alone
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
