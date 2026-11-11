from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings
from backend.app.core.logger import logger

class VectorStore:
    """
    Persistent Vector Database built on ChromaDB with Sentence Transformers.
    Stores and retrieves chunk embeddings with full metadata tracking.
    """
    _instance: Optional["VectorStore"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        logger.info(f"Connecting to persistent ChromaDB at: {settings.CHROMA_DIR}")
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.collection_name = "insightforge_research_docs"
        
        # Load SentenceTransformer embedding model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "InsightForge AI multi-document research collection"}
        )
        logger.info(f"ChromaDB collection '{self.collection_name}' ready. Count: {self.collection.count()}")

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        ids = [c["chunk_id"] for c in chunks]
        
        # Format metadata for ChromaDB (flat key-values only)
        metadatas = [
            {
                "document_id": str(c["document_id"]),
                "source": str(c["source"]),
                "page": int(c["page"]),
                "word_count": int(c["word_count"]),
                "timestamp": str(c["timestamp"])
            }
            for c in chunks
        ]

        # Compute embeddings
        logger.info(f"Computing embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(texts, convert_to_tensor=False).tolist()

        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks into ChromaDB.")

    def search(
        self,
        query: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic dense vector retrieval.
        Optionally filters by document_ids for tenant/document isolation.
        """
        if self.collection.count() == 0:
            return []

        # Generate query vector
        query_vec = self.embedding_model.encode(query, convert_to_tensor=False).tolist()

        # Construct filter if document_ids provided
        where_filter = None
        if document_ids and len(document_ids) == 1:
            where_filter = {"document_id": document_ids[0]}
        elif document_ids and len(document_ids) > 1:
            where_filter = {"document_id": {"$in": document_ids}}

        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, self.collection.count()),
            where=where_filter
        )

        retrieved: List[Dict[str, Any]] = []
        if not results or not results["documents"] or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        ids = results["ids"][0]
        metas = results["metadatas"][0]
        distances = results.get("distances", [[0.0] * len(docs)])[0]

        for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
            # Chroma L2 distance to normalized similarity score
            similarity = 1.0 / (1.0 + float(dist)) if dist is not None else 0.5
            retrieved.append({
                "chunk_id": chunk_id,
                "text": text,
                "document_id": meta.get("document_id", ""),
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", 1),
                "word_count": meta.get("word_count", 0),
                "score": round(similarity, 4)
            })

        return retrieved

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks associated with a specific document_id.
        """
        try:
            current_count = self.collection.count()
            self.collection.delete(where={"document_id": document_id})
            new_count = self.collection.count()
            deleted = current_count - new_count
            logger.info(f"Deleted {deleted} chunks for document_id '{document_id}'.")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting document '{document_id}' from vector store: {e}")
            raise e

    def get_all_chunks(self, document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks, used for BM25 inverted index in hybrid search.
        """
        if self.collection.count() == 0:
            return []

        where_filter = None
        if document_ids and len(document_ids) == 1:
            where_filter = {"document_id": document_ids[0]}
        elif document_ids and len(document_ids) > 1:
            where_filter = {"document_id": {"$in": document_ids}}

        data = self.collection.get(where=where_filter)
        chunks: List[Dict[str, Any]] = []
        if not data or not data["ids"]:
            return chunks

        for cid, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
            chunks.append({
                "chunk_id": cid,
                "text": doc,
                "document_id": meta.get("document_id", ""),
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", 1),
                "word_count": meta.get("word_count", 0)
            })
        return chunks

    def count(self) -> int:
        return self.collection.count()

vector_store = VectorStore()

