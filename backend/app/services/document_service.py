import difflib
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend.app.core.config import settings
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.core.security import sanitize_filename, validate_document_content
from backend.app.db.models import UserDocumentModel
from backend.app.db.session import SessionLocal
from backend.app.rag.chunker import TextChunker
from backend.app.rag.extractor import DocumentExtractor
from backend.app.rag.vector_store import vector_store
from backend.app.schemas.document import DocumentMetadata

DOC_METADATA_FILE = settings.DATA_DIR / "documents_metadata.json"
SHARED_USER_ID = "__shared__"


class DocumentService:
    """
    Manages document lifecycle with strict per-user / per-guest-session isolation:
    Validation -> Extraction -> Chunking -> Vector Indexing -> Persistence -> Preview & Comparison.
    """

    def __init__(self):
        self._meta_lock = threading.RLock()

    def ensure_sample_documents_indexed(self) -> None:
        """
        Indexes pre-existing shared sample documents found in `documents/`
        (e.g. college_rules.pdf) under SHARED_USER_ID if not already indexed.
        """
        try:
            with self._meta_lock:
                all_meta = self._load_metadata()
                indexed_filenames = {
                    v.get("filename")
                    for v in all_meta.values()
                    if v.get("user_id") in (SHARED_USER_ID, None)
                }
                # Normalize any legacy sample docs stored with user_id=None to SHARED_USER_ID
                changed = False
                for doc_id, meta in all_meta.items():
                    if meta.get("user_id") is None and not str(meta.get("filename", "")).startswith("doc_"):
                        meta["user_id"] = SHARED_USER_ID
                        changed = True
                if changed:
                    self._save_metadata(all_meta)

            if settings.DOCUMENTS_DIR.exists():
                for ext in settings.ALLOWED_EXTENSIONS:
                    for doc_file in settings.DOCUMENTS_DIR.glob(f"*{ext}"):
                        if doc_file.name not in indexed_filenames and not doc_file.name.startswith("doc_"):
                            logger.info(f"Auto-indexing shared sample document: {doc_file.name}")
                            try:
                                content = doc_file.read_bytes()
                                self._process_and_index_document(
                                    doc_file.name,
                                    content,
                                    user_id=SHARED_USER_ID,
                                    save_copy_to_disk=False,
                                    existing_path=doc_file
                                )
                            except Exception as e:
                                logger.error(f"Failed to auto-index {doc_file.name}: {e}")
        except Exception as e:
            logger.warning(f"Sample document auto-indexing skipped: {e}")

    def upload_document(self, file_bytes: bytes, original_filename: str, user_id: Optional[str] = None) -> DocumentMetadata:
        clean_name = sanitize_filename(original_filename)
        validate_document_content(file_bytes, clean_name)
        effective_uid = user_id or "guest_anonymous"
        return self._process_and_index_document(clean_name, file_bytes, user_id=effective_uid)

    def upload_url(self, url: str, user_id: Optional[str] = None) -> DocumentMetadata:
        pages = DocumentExtractor.extract_from_url(url)
        doc_id = f"doc_url_{uuid.uuid4().hex[:8]}"
        domain_name = re.sub(r"[^\w.\-]", "_", url.split("//")[-1].split("/")[0])
        filename = f"web_{domain_name}_{doc_id[:8]}.txt"
        effective_uid = user_id or "guest_anonymous"

        chunker = TextChunker(
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
        )
        chunks = chunker.chunk_pages(pages, document_id=doc_id, source_name=filename)
        vector_store.add_chunks(chunks)

        doc_meta = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_size_bytes=sum(len(str(p["text"]).encode("utf-8")) for p in pages),
            total_pages=len(pages),
            total_chunks=len(chunks),
            upload_timestamp=datetime.now(timezone.utc),
            status="indexed",
            user_id=effective_uid
        )

        with self._meta_lock:
            all_meta = self._load_metadata()
            all_meta[doc_id] = json.loads(doc_meta.model_dump_json())
            self._save_metadata(all_meta)

        if effective_uid and not effective_uid.startswith("guest_"):
            try:
                with SessionLocal() as db:
                    cloud_doc = UserDocumentModel(
                        id=doc_id,
                        user_id=effective_uid,
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
            except Exception as e:
                logger.error(f"Failed to persist URL document to SQL: {e}")

        logger.info(f"URL '{url}' indexed as '{doc_id}' ({len(chunks)} chunks) for '{effective_uid}'.")
        return doc_meta

    def _process_and_index_document(
        self,
        filename: str,
        content: bytes,
        user_id: Optional[str] = None,
        save_copy_to_disk: bool = True,
        existing_path: Optional[Path] = None
    ) -> DocumentMetadata:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        effective_uid = user_id or "guest_anonymous"

        if save_copy_to_disk:
            saved_path = settings.DOCUMENTS_DIR / f"{doc_id}_{filename}"
            saved_path.write_bytes(content)
        else:
            saved_path = existing_path or (settings.DOCUMENTS_DIR / filename)

        try:
            pages = DocumentExtractor.extract_from_bytes(
                content,
                source_name=filename,
                temp_file_path=str(saved_path)
            )
            total_pages = len(pages)

            chunker = TextChunker(
                chunk_size=settings.DEFAULT_CHUNK_SIZE,
                chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
            )
            chunks = chunker.chunk_pages(pages, document_id=doc_id, source_name=filename)
            total_chunks = len(chunks)

            vector_store.add_chunks(chunks)
        except Exception:
            if save_copy_to_disk and saved_path.exists():
                try:
                    saved_path.unlink()
                except Exception:
                    pass
            raise

        doc_meta = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_size_bytes=len(content),
            total_pages=total_pages,
            total_chunks=total_chunks,
            upload_timestamp=datetime.now(timezone.utc),
            status="indexed",
            user_id=effective_uid
        )

        with self._meta_lock:
            all_meta = self._load_metadata()
            all_meta[doc_id] = json.loads(doc_meta.model_dump_json())
            self._save_metadata(all_meta)

        if effective_uid and not effective_uid.startswith("guest_") and effective_uid != SHARED_USER_ID:
            try:
                with SessionLocal() as db:
                    cloud_doc = UserDocumentModel(
                        id=doc_id,
                        user_id=effective_uid,
                        filename=filename,
                        file_size_bytes=len(content),
                        total_pages=total_pages,
                        total_chunks=total_chunks,
                        status="indexed",
                        file_data=content,
                        source_type="file",
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cloud_doc)
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to persist document to SQL: {e}")

        logger.info(f"Document '{filename}' ({doc_id}) ingested with {total_chunks} chunks for '{effective_uid}'.")
        return doc_meta

    def count_all_documents(self) -> int:
        ids = set()
        with self._meta_lock:
            ids.update(self._load_metadata().keys())
        try:
            with SessionLocal() as db:
                for (row_id,) in db.query(UserDocumentModel.id).all():
                    ids.add(row_id)
        except Exception:
            pass
        return len(ids)

    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentMetadata]:
        """
        Lists documents accessible to `user_id` (authenticated `usr_*` or isolated `guest_*`),
        plus shared sample documents (`SHARED_USER_ID`).
        """
        docs_map: Dict[str, DocumentMetadata] = {}
        is_registered_user = bool(user_id and not user_id.startswith("guest_") and user_id != SHARED_USER_ID)

        if is_registered_user:
            try:
                with SessionLocal() as db:
                    cloud_rows = db.query(UserDocumentModel).filter(
                        UserDocumentModel.user_id == user_id
                    ).all()

                    for r in cloud_rows:
                        if r.file_data:
                            target_path = settings.DOCUMENTS_DIR / f"{r.id}_{r.filename}"
                            if not target_path.exists():
                                try:
                                    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                                    target_path.write_bytes(r.file_data)
                                    chroma_check = vector_store.collection.get(where={"document_id": r.id})
                                    if not chroma_check or not chroma_check.get("ids"):
                                        pages = DocumentExtractor.extract_from_bytes(
                                            r.file_data, source_name=r.filename, temp_file_path=str(target_path)
                                        )
                                        chunker = TextChunker(
                                            chunk_size=settings.DEFAULT_CHUNK_SIZE,
                                            chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
                                        )
                                        chunks = chunker.chunk_pages(pages, document_id=r.id, source_name=r.filename)
                                        vector_store.add_chunks(chunks)
                                except Exception as err:
                                    logger.warning(f"Failed to rehydrate local file from DB: {err}")

                        docs_map[r.id] = DocumentMetadata(
                            document_id=r.id,
                            filename=r.filename,
                            file_size_bytes=r.file_size_bytes,
                            total_pages=r.total_pages,
                            total_chunks=r.total_chunks,
                            upload_timestamp=r.created_at,
                            status=r.status,
                            user_id=r.user_id
                        )
            except Exception as e:
                logger.error(f"Error querying documents from SQL: {e}")

        allowed_owners = {SHARED_USER_ID}
        if user_id:
            allowed_owners.add(user_id)

        with self._meta_lock:
            all_meta = self._load_metadata()
        for v in all_meta.values():
            d = DocumentMetadata(**v)
            if d.user_id in allowed_owners and d.document_id not in docs_map:
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
        is_registered_user = bool(user_id and not user_id.startswith("guest_") and user_id != SHARED_USER_ID)
        if is_registered_user:
            try:
                with SessionLocal() as db:
                    row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                    if row:
                        if row.user_id != user_id:
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
                logger.error(f"Error checking SQL document: {e}")

        with self._meta_lock:
            all_meta = self._load_metadata()
        data = all_meta.get(document_id)
        if not data:
            return None
        doc = DocumentMetadata(**data)
        allowed_owners = {SHARED_USER_ID}
        if user_id:
            allowed_owners.add(user_id)
        if doc.user_id not in allowed_owners:
            return None
        return doc

    def get_document_file_path(self, document_id: str, user_id: Optional[str] = None) -> Optional[Path]:
        doc = self.get_document(document_id, user_id=user_id)
        if not doc:
            return None

        expected_path = settings.DOCUMENTS_DIR / f"{document_id}_{doc.filename}"
        if expected_path.exists():
            return expected_path

        matches = list(settings.DOCUMENTS_DIR.glob(f"{document_id}_*"))
        if matches and matches[0].exists():
            return matches[0]

        if doc.user_id == SHARED_USER_ID:
            plain_path = settings.DOCUMENTS_DIR / doc.filename
            if plain_path.exists():
                return plain_path

        try:
            with SessionLocal() as db:
                row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                if row and row.file_data and row.user_id == user_id:
                    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                    expected_path.write_bytes(row.file_data)
                    return expected_path
        except Exception as e:
            logger.error(f"Error restoring file from SQL: {e}")

        return None

    def get_document_preview(self, document_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Returns structured extracted page/section content for any supported document format or URL.
        """
        doc = self.get_document(document_id, user_id=user_id)
        if not doc:
            return None

        ext = Path(doc.filename).suffix.lower()
        file_path = self.get_document_file_path(document_id, user_id=user_id)
        pages: List[Dict[str, Any]] = []

        if file_path and file_path.exists():
            try:
                pages = DocumentExtractor.extract_from_file(file_path)
            except Exception as e:
                logger.warning(f"Preview extraction from file failed for {document_id}: {e}")

        if not pages:
            try:
                chunks = vector_store.get_all_chunks(document_ids=[document_id])
                by_page: Dict[int, List[str]] = {}
                for ch in chunks:
                    pnum = int(ch.get("page", 1))
                    by_page.setdefault(pnum, []).append(ch.get("text", ""))
                pages = [
                    {"page": pnum, "text": "\n\n".join(texts)}
                    for pnum, texts in sorted(by_page.items())
                ]
            except Exception as e:
                logger.warning(f"Chroma preview fallback failed for {document_id}: {e}")

        return {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "ext": ext,
            "total_pages": len(pages) or doc.total_pages,
            "total_chunks": doc.total_chunks,
            "pages": pages,
        }

    def delete_document(self, document_id: str, user_id: Optional[str] = None) -> bool:
        """
        Deletes document strictly owned by `user_id`. Shared sample docs cannot be deleted by callers.
        """
        if not user_id:
            return False

        # Verify ownership across SQL and metadata
        is_registered_user = bool(user_id and not user_id.startswith("guest_") and user_id != SHARED_USER_ID)
        found = False

        if is_registered_user:
            try:
                with SessionLocal() as db:
                    row = db.query(UserDocumentModel).filter(UserDocumentModel.id == document_id).first()
                    if row:
                        if row.user_id != user_id:
                            logger.warning(f"Unauthorized delete attempt for {document_id} by user {user_id}")
                            return False
                        db.delete(row)
                        db.commit()
                        found = True
            except Exception as e:
                logger.error(f"Failed to delete document from SQL: {e}")

        with self._meta_lock:
            all_meta = self._load_metadata()
            if document_id in all_meta:
                doc_uid = all_meta[document_id].get("user_id")
                if doc_uid == SHARED_USER_ID or doc_uid != user_id:
                    logger.warning(f"Unauthorized delete attempt for {document_id} (owner={doc_uid}) by {user_id}")
                    return False
                del all_meta[document_id]
                self._save_metadata(all_meta)
                found = True

        if not found:
            return False

        try:
            vector_store.delete_document(document_id)
        except Exception as e:
            logger.warning(f"Could not delete ChromaDB chunks for {document_id}: {e}")

        for file in settings.DOCUMENTS_DIR.glob(f"{document_id}_*"):
            try:
                file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete file {file.name}: {e}")

        return True

    def clear_guest_data(self, owner_id: Optional[str] = None) -> int:
        """
        Purges temporary documents uploaded by a guest session (or all guest sessions if owner_id is None),
        while preserving shared sample documents.
        """
        with self._meta_lock:
            all_meta = self._load_metadata()
            target_docs = []
            for doc_id, v in all_meta.items():
                uid = v.get("user_id")
                if uid == SHARED_USER_ID:
                    continue
                if owner_id:
                    if owner_id.startswith("guest_") and uid == owner_id:
                        target_docs.append((doc_id, uid))
                else:
                    if uid is None or str(uid).startswith("guest"):
                        target_docs.append((doc_id, uid))

        purged = 0
        for doc_id, uid in target_docs:
            if uid is None:
                with self._meta_lock:
                    meta_now = self._load_metadata()
                    if doc_id in meta_now:
                        del meta_now[doc_id]
                        self._save_metadata(meta_now)
                try:
                    vector_store.delete_document(doc_id)
                except Exception:
                    pass
                for file in settings.DOCUMENTS_DIR.glob(f"{doc_id}_*"):
                    try:
                        file.unlink()
                    except Exception:
                        pass
                purged += 1
            elif self.delete_document(doc_id, user_id=uid):
                purged += 1
        return purged

    def compare_documents(
        self,
        doc_id_1: str,
        doc_id_2: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        doc1 = self.get_document(doc_id_1, user_id=user_id)
        doc2 = self.get_document(doc_id_2, user_id=user_id)
        if not doc1 or not doc2:
            raise ValueError("One or both documents not found or access denied.")

        def get_doc_text(doc_id: str) -> str:
            path = self.get_document_file_path(doc_id, user_id=user_id)
            if path and path.exists():
                try:
                    pages = DocumentExtractor.extract_from_file(path)
                    if pages:
                        return "\n".join([f"[Page {p['page']}]: {p['text']}" for p in pages[:15]])[:12000]
                except Exception as e:
                    logger.warning(f"File extraction fallback for {doc_id}: {e}")

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

        if gemini_client.is_configured:
            prompt = f"""
You are a senior document intelligence, legal, and compliance comparison specialist.
Perform a rigorous, structured comparative analysis between Document A and Document B.
Carefully examine changes in obligations, legal liabilities, warranties, deadlines, numeric/percentage thresholds, financial terms, or operating rules, highlighting exact numeric deltas in executive_summary and risk_assessment.

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
            try:
                return gemini_client.generate_json(prompt)
            except Exception as e:
                logger.warning(f"Gemini document comparison failed ({e}), falling back to local diff analyzer.")

        return self._local_compare_documents(doc1, doc2, text1, text2)

    @staticmethod
    def _local_compare_documents(
        doc1: DocumentMetadata,
        doc2: DocumentMetadata,
        text1: str,
        text2: str
    ) -> Dict[str, Any]:
        def split_clauses(raw: str) -> List[str]:
            cleaned = re.sub(r"\[Page \d+\]:\s*", "", raw)
            lines = [ln.strip() for ln in re.split(r"\n+|(?<=[.!?])\s+", cleaned) if len(ln.strip()) > 12]
            return lines[:120]

        lines_a = split_clauses(text1)
        lines_b = split_clauses(text2)
        set_a = set(lines_a)
        set_b = set(lines_b)

        added = [ln for ln in lines_b if ln not in set_a][:15]
        removed = [ln for ln in lines_a if ln not in set_b][:15]

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        similarity_pct = round(matcher.ratio() * 100, 1)

        conflicts: List[Dict[str, str]] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace" and len(conflicts) < 8:
                a_seg = " ".join(lines_a[i1:i2])[:280]
                b_seg = " ".join(lines_b[j1:j2])[:280]
                has_risk_terms = any(k in (a_seg + b_seg).lower() for k in ["liability", "penalty", "fee", "terminat", "must", "shall", "limit", "%", "$"])
                impact = (
                    "High: Modifies enforceable obligations, thresholds, or financial/compliance terms."
                    if has_risk_terms
                    else "Medium: Revises section wording or operational specification."
                )
                conflicts.append({
                    "clause": f"Section Modification #{len(conflicts) + 1}",
                    "doc_a_version": a_seg,
                    "doc_b_version": b_seg,
                    "impact": impact
                })

        def snippet_for(lines: List[str], keywords: List[str], fallback: str) -> str:
            hits = [ln for ln in lines if any(k in ln.lower() for k in keywords)]
            if hits:
                return " ".join(hits[:2])[:240]
            return fallback

        matrix = [
            {
                "dimension": "Purpose & Scope",
                "doc_a": " ".join(lines_a[:2])[:240] or doc1.filename,
                "doc_b": " ".join(lines_b[:2])[:240] or doc2.filename,
                "difference": f"Textual similarity is {similarity_pct}%; {len(added)} new statements and {len(removed)} removed statements detected."
            },
            {
                "dimension": "Key Terms & Governance Rules",
                "doc_a": snippet_for(lines_a, ["must", "shall", "rule", "policy", "require"], "Standard clauses present."),
                "doc_b": snippet_for(lines_b, ["must", "shall", "rule", "policy", "require"], "Standard clauses present."),
                "difference": "Compares mandatory governance and procedural rules across versions."
            },
            {
                "dimension": "Liabilities, Indemnities & Penalties",
                "doc_a": snippet_for(lines_a, ["liab", "indemn", "penalt", "breach", "fine"], "No explicit liability terms extracted."),
                "doc_b": snippet_for(lines_b, ["liab", "indemn", "penalt", "breach", "fine"], "No explicit liability terms extracted."),
                "difference": "Highlights shifts in penalty, breach, or indemnity language."
            },
            {
                "dimension": "Financial, Fee, or Payment Terms",
                "doc_a": snippet_for(lines_a, ["$", "fee", "pay", "cost", "salary", "stipend", "price"], "No explicit financial figures extracted."),
                "doc_b": snippet_for(lines_b, ["$", "fee", "pay", "cost", "salary", "stipend", "price"], "No explicit financial figures extracted."),
                "difference": "Identifies numeric or monetary term deltas."
            },
            {
                "dimension": "Compliance, Termination & Dispute Resolution",
                "doc_a": snippet_for(lines_a, ["terminat", "notice", "complian", "audit", "dispute"], "Standard termination/compliance scope."),
                "doc_b": snippet_for(lines_b, ["terminat", "notice", "complian", "audit", "dispute"], "Standard termination/compliance scope."),
                "difference": "Tracks changes to notice periods, auditability, and termination conditions."
            },
        ]

        num_pat = re.compile(
            r"\b\d+(?:\.\d+)?%|\$\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:INR|USD|EUR|days?|months?|minutes?|hours?)\b",
            re.IGNORECASE,
        )
        nums_a = {re.sub(r"\s+", " ", m).strip() for m in num_pat.findall(text1)}
        nums_b = {re.sub(r"\s+", " ", m).strip() for m in num_pat.findall(text2)}
        added_nums = sorted(nums_b - nums_a)[:6]
        removed_nums = sorted(nums_a - nums_b)[:6]
        numeric_delta_note = ""
        if added_nums or removed_nums:
            numeric_delta_note = (
                f" [TOOL-CHECKED NUMERIC DELTAS] New/revised figures in {doc2.filename}: {', '.join(added_nums) or 'none'}; "
                f"superseded figures from {doc1.filename}: {', '.join(removed_nums) or 'none'}."
            )

        return {
            "doc_a_name": doc1.filename,
            "doc_b_name": doc2.filename,
            "executive_summary": (
                f"Local Extractive Diff Analysis (configure GEMINI_API_KEY in .env for deep LLM semantic legal analysis): "
                f"Compared '{doc1.filename}' ({len(lines_a)} segments) against '{doc2.filename}' ({len(lines_b)} segments). "
                f"Structural similarity: {similarity_pct}%. Identified {len(added)} additions, {len(removed)} removals, and {len(conflicts)} modified blocks."
                f"{numeric_delta_note}"
            ),
            "comparison_matrix": matrix,
            "added_clauses": added,
            "removed_clauses": removed,
            "conflicts_or_changes": conflicts,
            "risk_assessment": (
                f"Local Structural Diff Risk Summary: {len(conflicts)} modified block(s) and {len(added)} newly added statement(s) "
                f"should be reviewed manually if they alter compliance deadlines, fees, or liability thresholds."
                f"{numeric_delta_note}"
            ),
        }

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
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DOC_METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write document metadata: {e}")


document_service = DocumentService()
