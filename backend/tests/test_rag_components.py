import pytest
from pathlib import Path
from backend.app.rag.extractor import PDFExtractor
from backend.app.rag.chunker import TextChunker
from backend.app.rag.vector_store import VectorStore
from backend.app.rag.reranker import Reranker
from backend.app.rag.pipeline import AdvancedRAGPipeline

def test_chunker_sentence_aware():
    chunker = TextChunker(chunk_size=25, overlap_sentences=1)
    pages = [
        {
            "page": 1,
            "text": "First sentence is here. Second sentence gives more details. Third sentence finishes the first paragraph.\n\nFourth sentence starts paragraph two. Fifth sentence concludes paragraph two."
        }
    ]
    chunks = chunker.chunk_pages(pages, document_id="test_doc", source_name="test.pdf")
    assert len(chunks) >= 2
    assert chunks[0]["page"] == 1
    assert chunks[0]["source"] == "test.pdf"
    assert "First sentence" in chunks[0]["text"]
    assert "chunk_id" in chunks[0]

def test_reranker_relevance_ordering():
    reranker = Reranker()
    query = "What is the policy for student attendance?"
    candidate_chunks = [
        {"chunk_id": "c1", "text": "The cafeteria is open from 8am to 8pm daily.", "source": "campus.pdf", "page": 1},
        {"chunk_id": "c2", "text": "Students must maintain a minimum of 75% attendance to qualify for final exams.", "source": "policy.pdf", "page": 2},
        {"chunk_id": "c3", "text": "Parking permits cost 50 dollars per semester.", "source": "parking.pdf", "page": 1}
    ]
    reranked = reranker.rerank(query=query, chunks=candidate_chunks, top_n=2)
    assert len(reranked) == 2
    # The attendance chunk should rank highest
    assert "attendance" in reranked[0]["text"].lower()
    assert reranked[0]["chunk_id"] == "c2"

def test_context_construction_and_citations():
    chunks = [
        {"chunk_id": "c1", "text": "KIIT requires 75% attendance.", "source": "college_rules.pdf", "page": 1, "score": 0.95}
    ]
    context_str, citations = AdvancedRAGPipeline.build_context(chunks)
    assert "Source 1" in context_str
    assert "college_rules.pdf" in context_str
    assert len(citations) == 1
    assert citations[0].page_number == 1
    assert citations[0].source_filename == "college_rules.pdf"

