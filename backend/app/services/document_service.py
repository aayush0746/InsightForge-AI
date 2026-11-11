import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.security import sanitize_filename, validate_document_content
from backend.app.rag.extractor import DocumentExtractor
from backend.app.rag.chunker import TextChunker
from backend.app.rag.vector_store import vector_store
from backend.app.schemas.document import DocumentMetadata
from backend.app.core.gemini import gemini_client
from backend.app.db.session import SessionLocal, DB_DIALECT
from backend.app.db.models import UserDocumentModel

DOC_METADATA_FILE = settings.DATA_DIR / "documents_metadata.json"

class DocumentService:
    """
    Manages document lifecycle:
    Validation -> Extraction -> Chunking -> Vector Indexing -> Metadata Persistence -> Document Comparison.
    """

    def __init__(self):
        self._sync_existing_folder()

    def _sync_existing_folder(self):
        """
        Indexes any pre-existing supported documents found in documents/
        if they are not already recorded in documents_metadata.json.
        """
        existing_docs = self.list_documents()
        indexed_filenames = {d.filename for d in existing_docs}

        if settings.DOCUMENTS_DIR.exists():
            for ext in settings.ALLOWED_EXTENSIONS:
                for doc_file in settings.DOCUMENTS_DIR.glob(f"*{ext}"):
                    if doc_file.name not in indexed_filenames and not doc_file.name.startswith("doc_"):
                        logger.info(f"Auto-indexing pre-existing document: {doc_file.name}")
                        try:
                            with open(doc_file, "rb") as f:
                                content = f.read()
                            self._process_and_index_document(doc_file.name, content)
                        except Exception as e:
                            logger.error(f"Failed to auto-index {doc_file.name}: {e}")

    def upload_document(self, file_bytes: bytes, original_filename: str, user_id: Optional[str] = None) -> DocumentMetadata:
        """
        Validates, saves, extracts, and indexes an uploaded document.
        """
        clean_name = sanitize_filename(original_filename)
        validate_document_content(file_bytes, clean_name)
        return self._process_and_index_document(clean_name, file_bytes, user_id=user_id)

    def upload_url(self, url: str, user_id: Optional[str] = None) -> DocumentMetadata:
        """
        Scrapes a live webpage, extracts text, chunks, and indexes it into ChromaDB.
        """
        pages = DocumentExtractor.extract_from_url(url)
        doc_id = f"doc_url_{uuid.uuid4().hex[:8]}"
        domain_name = url.split("//")[-1].split("/")[0]
        filename = f"web_{domain_name}_{doc_id[:8]}"

        chunker = TextChunker(
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            overlap_sentences=1
        )
        chunks = chunker.chunk_pages(pages, document_id=doc_id, source_name=filename)

        # Index to vector store
        vector_store.add_chunks(chunks)

        # Save metadata
        doc_meta = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_size_bytes=sum(len(str(p["text"])) for p in pages),
            total_pages=len(pages),
            total_chunks=len(chunks),
            upload_timestamp=datetime.now(timezone.utc),
            status="indexed",
            user_id=user_id
        )

        all_meta = self._load_metadata()
        all_meta[doc_id] = json.loads(doc_meta.model_dump_json())
        self._save_metadata(all_meta)

        # Persist to Supabase Cloud PostgreSQL for authenticated users
        if user_id:
            try:
                with SessionLocal() as db:
                    cloud_doc = UserDocumentModel(
                        id=doc_id,
                        user_id=user_id,
                        filename=filename,
                        file_size_bytes=doc_meta.file_size_bytes,
                        total_pages=len(pages),
                        total_chunks=len(chunks),
                        status="indexed",
                        source_type="url",
                        source_url=url,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cloud_doc)
                    db.commit()
                    logger.info(f"URL document '{doc_id}' persisted to Supabase Cloud PostgreSQL for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to persist URL document to cloud PostgreSQL: {e}")

        logger.info(f"URL '{url}' successfully indexed as document '{doc_id}' with {len(chunks)} chunks.")
        return doc_meta

    def _process_and_index_document(self, filename: str, content: bytes, user_id: Optional[str] = None) -> DocumentMetadata:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        saved_path = settings.DOCUMENTS_DIR / f"{doc_id}_{filename}"

        # Write to disk
        with open(saved_path, "wb") as f:
            f.write(content)

        # 1. Extract text with multi-format extractor
        pages = DocumentExtractor.extract_from_bytes(content, source_name=filename, temp_file_path=str(saved_path))
        total_pages = len(pages)

        # 2. Chunk text
        chunker = TextChunker(
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            overlap_sentences=1
        )
        chunks = chunker.chunk_pages(pages, document_id=doc_id, source_name=filename)
        total_chunks = len(chunks)

        # 3. Add to ChromaDB vector store
        vector_store.add_chunks(chunks)

        # 4. Save metadata
        doc_meta = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_size_bytes=len(content),
            total_pages=total_pages,
            total_chunks=total_chunks,
            upload_timestamp=datetime.now(timezone.utc),
            status="indexed",
            user_id=user_id
        )

        all_meta = self._load_metadata()
        all_meta[doc_id] = json.loads(doc_meta.model_dump_json())
        self._save_metadata(all_meta)

        # 5. Persist document binary and metadata to Supabase Cloud PostgreSQL for logged-in users
        if user_id:
            try:
                with SessionLocal() as db:
                    cloud_doc = UserDocumentModel(
                        id=doc_id,
                        user_id=user_id,
                        filename=filename,
                        file_size_bytes=len(content),
                        total_pages=total_pages,
                        total_chunks=total_chunks,
                        status="indexed",
                        file_data=content,  # Securely stored in Supabase Cloud
                        source_type="file",
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cloud_doc)
                    db.commit()
                    logger.info(f"Document '{filename}' ({doc_id}) safely stored in Supabase Cloud PostgreSQL for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to persist document to Supabase Cloud PostgreSQL: {e}")

        logger.info(f"Document '{filename}' successfully ingested with {total_chunks} chunks.")
        return doc_meta

    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentMetadata]:
        """
        Lists documents:
        - Authenticated user: Returns documents stored in Supabase Cloud PostgreSQL for this user + shared templates.
        - Guest (user_id=None): Returns ONLY shared template documents. Guest sessions never see or save to cloud.
        """
        docs_map: Dict[str, DocumentMetadata] = {}

        if user_id:
            # 1. Fetch from Supabase Cloud PostgreSQL
            try:
                with SessionLocal() as db:
                    cloud_rows = db.query(UserDocumentModel).filter(
                        (UserDocumentModel.user_id == user_id) | (UserDocumentModel.user_id == None)
                    ).all()

                    for r in cloud_rows:
                        # Reconstruct local file if missing (e.g. fresh environment or server restart)
                        if r.file_data:
                            target_path = settings.DOCUMENTS_DIR / f"{r.id}_{r.filename}"
                            if not target_path.exists():
                                try:
                                    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                                    with open(target_path, "wb") as f:
                                        f.write(r.file_data)
                                    
                                    # Ensure indexed in ChromaDB
                                    chroma_check = vector_store.collection.get(where={"document_id": r.id})
                                    if not chroma_check or not chroma_check.get("ids"):
                                        pages = DocumentExtractor.extract_from_bytes(r.file_data, source_name=r.filename, temp_file_path=str(target_path))
                                        chunker = TextChunker(chunk_size=settings.DEFAULT_CHUNK_SIZE, overlap_sentences=1)
                                        chunks = chunker.chunk_pages(pages, document_id=r.id, source_name=r.filename)
                                        vector_store.add_chunks(chunks)
                                except Exception as err:
                                    logger.warning(f"Failed to rehydrate local file from cloud DB: {err}")

                        meta = DocumentMetadata(
                            document_id=r.id,
                            filename=r.filename,
                            file_size_bytes=r.file_size_bytes,
                            total_pages=r.total_pages,
                            total_chunks=r.total_chunks,
                            upload_timestamp=r.created_at,
                            status=r.status,
                            user_id=r.user_id
                        )
                        docs_map[r.id] = meta
            except Exception as e:
                logger.error(f"Error querying cloud documents from PostgreSQL: {e}")

            # 2. Add local metadata documents for this user (or shared templates)
            all_meta = self._load_metadata()
            for v in all_meta.values():
                d = DocumentMetadata(**v)
                if d.user_id == user_id or d.user_id is None:
                    if d.document_id not in docs_map:
                        docs_map[d.document_id] = d
        else:
            # Guests ONLY see shared demo/template documents (user_id is None)
            all_meta = self._load_metadata()
            for v in all_meta.values():
                d = DocumentMetadata(**v)
                if d.user_id is None:
                    docs_map[d.document_id] = d

        docs = list(docs_map.values())
        
        def sort_key(d: DocumentMetadata):
            ts = d.upload_timestamp
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)

        docs.sort(key=sort_key, reverse=True)
        return docs

    def get_document(self, document_id: str, user_id: Optional[str] = None) -> Optional[DocumentMetadata]:
        # First check Cloud PostgreSQL
        try:
            with SessionLocal() as db:
                row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                if row:
                    if row.user_id and user_id and row.user_id != user_id:
                        return None
                    if row.user_id and not user_id:
                        return None
                    return DocumentMetadata(
                        document_id=row.id,
                        filename=row.filename,
                        file_size_bytes=row.file_size_bytes,
                        total_pages=row.total_pages,
                        total_chunks=row.total_chunks,
                        upload_timestamp=row.created_at,
                        status=row.status,
                        user_id=row.user_id
                    )
        except Exception as e:
            logger.error(f"Error checking cloud document: {e}")

        all_meta = self._load_metadata()
        data = all_meta.get(document_id)
        if not data:
            return None
        doc = DocumentMetadata(**data)
        if doc.user_id and user_id and doc.user_id != user_id:
            return None
        if doc.user_id and not user_id:
            return None
        return doc

    def get_document_file_path(self, document_id: str, user_id: Optional[str] = None) -> Optional[Path]:
        """
        Locates the actual file on disk for browser viewing / streaming with permission check.
        Restores from Cloud PostgreSQL if absent locally.
        """
        doc = self.get_document(document_id, user_id=user_id)
        if not doc:
            return None

        # Check local files first
        expected_path = settings.DOCUMENTS_DIR / f"{document_id}_{doc.filename}"
        if expected_path.exists():
            return expected_path
        
        matches = list(settings.DOCUMENTS_DIR.glob(f"{document_id}_*"))
        if matches and matches[0].exists():
            return matches[0]

        plain_path = settings.DOCUMENTS_DIR / doc.filename
        if plain_path.exists():
            return plain_path

        # If missing locally, restore from Supabase Cloud PostgreSQL
        try:
            with SessionLocal() as db:
                row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                if row and row.file_data:
                    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                    with open(expected_path, "wb") as f:
                        f.write(row.file_data)
                    return expected_path
        except Exception as e:
            logger.error(f"Error restoring file from cloud PostgreSQL: {e}")

        return None

    def delete_document(self, document_id: str, user_id: Optional[str] = None) -> bool:
        """
        Deletes document completely:
        - From Supabase Cloud PostgreSQL
        - From ChromaDB vector store embeddings
        - From local disk storage
        - From local metadata cache
        """
        deleted_from_cloud = False

        # 1. Delete from Supabase Cloud PostgreSQL
        try:
            with SessionLocal() as db:
                row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                if row:
                    if row.user_id and user_id and row.user_id != user_id:
                        logger.warning(f"Unauthorized delete attempt for {document_id} by user {user_id}")
                        return False
                    db.delete(row)
                    db.commit()
                    deleted_from_cloud = True
                    logger.info(f"Deleted document {document_id} from Supabase Cloud PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to delete document from cloud PostgreSQL: {e}")

        # 2. Check local metadata
        all_meta = self._load_metadata()
        if document_id in all_meta:
            meta = all_meta[document_id]
            doc_uid = meta.get("user_id")
            if doc_uid and user_id and doc_uid != user_id:
                logger.warning(f"Unauthorized delete attempt for {document_id} by user {user_id}")
                return False
            del all_meta[document_id]
            self._save_metadata(all_meta)

        # 3. Delete chunks from ChromaDB vector store
        try:
            vector_store.delete_document(document_id)
        except Exception as e:
            logger.warning(f"Could not delete ChromaDB chunks for {document_id}: {e}")

        # 4. Delete physical file if present
        for file in settings.DOCUMENTS_DIR.glob(f"{document_id}_*"):
            try:
                file.unlink()
                logger.info(f"Deleted physical file: {file.name}")
            except Exception as e:
                logger.warning(f"Could not delete file {file.name}: {e}")

        return True

    def clear_guest_data(self) -> int:
        """
        Purges any temporary documents uploaded by guest sessions.
        """
        all_meta = self._load_metadata()
        guest_doc_ids = [doc_id for doc_id, v in all_meta.items() if v.get("user_id") == "guest"]
        purged = 0
        for doc_id in guest_doc_ids:
            self.delete_document(doc_id)
            purged += 1
        return purged

    def compare_documents(self, doc_id_1: str, doc_id_2: str) -> Dict[str, Any]:
        """
        Performs in-depth comparative analysis between two indexed documents.
        Supports both uploaded physical files (.pdf, .docx, .xlsx, .pptx, etc.)
        and ingested web pages / documents via ChromaDB vector store fallback.
        """
        doc1 = self.get_document(doc_id_1)
        doc2 = self.get_document(doc_id_2)
        if not doc1 or not doc2:
            raise ValueError("One or both documents not found for comparison.")

        def get_doc_text(doc_id: str) -> str:
            path = self.get_document_file_path(doc_id)
            if path and path.exists():
                try:
                    pages = DocumentExtractor.extract_from_file(path)
                    if pages:
                        return "\n".join([f"[Page {p['page']}]: {p['text']}" for p in pages[:15]])[:12000]
                except Exception as e:
                    logger.warning(f"File extraction fallback for {doc_id}: {e}")

            # Fallback to indexed ChromaDB chunks
            try:
                chroma_res = vector_store.collection.get(where={"document_id": doc_id})
                docs = chroma_res.get("documents", [])
                if docs:
                    return "\n\n".join(docs[:25])[:12000]
            except Exception as e:
                logger.error(f"Chroma chunk fetch failed for {doc_id}: {e}")

            return ""

        text1 = get_doc_text(doc_id_1)
        text2 = get_doc_text(doc_id_2)

        if not text1 or not text2:
            raise ValueError("Could not retrieve sufficient text content for comparison.")

        prompt = f"""
You are a senior document intelligence, legal, and compliance comparison specialist.
Perform a rigorous, structured comparative analysis between Document A and Document B.
Carefully examine changes in obligations, legal liabilities, warranties, deadlines, financial terms, or operating rules.

DOCUMENT A ({doc1.filename}):
{text1}

DOCUMENT B ({doc2.filename}):
{text2}

Return a valid JSON object matching this schema:
{{
  "doc_a_name": "{doc1.filename}",
  "doc_b_name": "{doc2.filename}",
  "executive_summary": "Clear, executive-level summary of how the two documents differ and what strategic, legal, or procedural changes occurred.",
  "comparison_matrix": [
    {{"dimension": "Purpose & Scope", "doc_a": "Summary in Doc A", "doc_b": "Summary in Doc B", "difference": "Key difference"}},
    {{"dimension": "Key Terms & Governance Rules", "doc_a": "...", "doc_b": "...", "difference": "..."}},
    {{"dimension": "Liabilities, Indemnities & Penalties", "doc_a": "...", "doc_b": "...", "difference": "..."}},
    {{"dimension": "Financial, Fee, or Payment Terms", "doc_a": "...", "doc_b": "...", "difference": "..."}},
    {{"dimension": "Compliance, Termination & Dispute Resolution", "doc_a": "...", "doc_b": "...", "difference": "..."}}
  ],
  "added_clauses": [
    "Specific new clause or rule introduced in Document B that did not exist in Document A"
  ],
  "removed_clauses": [
    "Specific clause or rule deleted from Document A that no longer exists in Document B"
  ],
  "conflicts_or_changes": [
    {{
      "clause": "Name of clause / rule modified",
      "doc_a_version": "Exact or summarized rule in Document A",
      "doc_b_version": "Exact or summarized rule in Document B",
      "impact": "High / Medium / Low: Precise explanation of how legal liability, operational risk, or responsibility shifted"
    }}
  ],
  "risk_assessment": "Comprehensive assessment of operational, legal, and financial risks introduced by this revision."
}}
"""
        return gemini_client.generate_json(prompt)

    def _load_metadata(self) -> Dict[str, Any]:
        if not DOC_METADATA_FILE.exists():
            return {}
        try:
            with open(DOC_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_metadata(self, data: Dict[str, Any]) -> None:
        try:
            with open(DOC_METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write document metadata: {e}")

document_service = DocumentService()
