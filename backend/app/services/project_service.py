import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from backend.app.core.logger import logger
from backend.app.db.models import ProjectModel, ProjectThreadModel
from backend.app.db.session import SessionLocal, init_db
from backend.app.rag.pipeline import rag_pipeline
from backend.app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectThread,
    ThreadMessage,
)
from backend.app.services.document_service import document_service


class ProjectService:
    """
    SQL-backed Workspace Projects & Conversational Thread Service:
    - Dedicated, strictly user/session-isolated workspaces.
    - Multi-turn conversational threading with full context memory.
    - Enforces document ownership on assignment and zero cross-tenant leakage during RAG queries.
    """

    def __init__(self):
        init_db()

    @staticmethod
    def _to_project_schema(row: ProjectModel, thread_count: int) -> Project:
        try:
            doc_ids = json.loads(row.document_ids_json or "[]")
        except Exception:
            doc_ids = []
        return Project(
            id=row.id,
            name=row.name,
            description=row.description or "",
            color=row.color or "indigo",
            icon=row.icon or "folder",
            document_ids=doc_ids,
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
            thread_count=thread_count,
            document_count=len(doc_ids),
            user_id=row.user_id
        )

    @staticmethod
    def _to_thread_schema(row: ProjectThreadModel) -> ProjectThread:
        try:
            msgs = json.loads(row.messages_json or "[]")
        except Exception:
            msgs = []
        return ProjectThread(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
            messages=[ThreadMessage(**m) for m in msgs]
        )

    def list_projects(self, user_id: Optional[str] = None) -> List[Project]:
        owner = user_id or "guest_anonymous"
        with SessionLocal() as db:
            rows = db.query(ProjectModel).filter(
                ProjectModel.user_id == owner
            ).order_by(ProjectModel.created_at.asc()).all()

            if not rows:
                is_guest = owner.startswith("guest_")
                starter = self.create_project(
                    ProjectCreate(
                        name="Temporary Guest Scratchpad" if is_guest else "My Research Workspace",
                        description=(
                            "Temporary isolated session for exploration. Chats and uploads can be purged anytime."
                            if is_guest
                            else "Personal research workspace & conversational threads"
                        ),
                        color="amber" if is_guest else "indigo",
                        icon="sparkles" if is_guest else "folder"
                    ),
                    user_id=owner
                )
                return [starter]

            result: List[Project] = []
            for r in rows:
                t_count = db.query(ProjectThreadModel).filter(ProjectThreadModel.project_id == r.id).count()
                result.append(self._to_project_schema(r, t_count))
            return result

    def get_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Project]:
        owner = user_id or "guest_anonymous"
        with SessionLocal() as db:
            row = db.query(ProjectModel).filter(
                ProjectModel.id == project_id,
                ProjectModel.user_id == owner
            ).first()
            if not row:
                return None
            t_count = db.query(ProjectThreadModel).filter(ProjectThreadModel.project_id == row.id).count()
            return self._to_project_schema(row, t_count)

    def create_project(self, payload: ProjectCreate, user_id: Optional[str] = None) -> Project:
        # Always bind ownership to caller's authenticated/guest owner_id, ignoring client payload.user_id
        effective_user_id = user_id or "guest_anonymous"
        pid = f"proj_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        allowed_doc_ids = []
        for did in (payload.document_ids or []):
            if document_service.get_document(did, user_id=effective_user_id):
                allowed_doc_ids.append(did)

        with SessionLocal() as db:
            row = ProjectModel(
                id=pid,
                user_id=effective_user_id,
                name=payload.name,
                description=payload.description or "",
                color=payload.color or "indigo",
                icon=payload.icon or "folder",
                document_ids_json=json.dumps(allowed_doc_ids),
                created_at=now,
                updated_at=now
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info(f"Created Workspace Project: {payload.name} ({pid}) for '{effective_user_id}'")
            return self._to_project_schema(row, 0)

    def update_project(self, project_id: str, payload: ProjectUpdate, user_id: Optional[str] = None) -> Optional[Project]:
        owner = user_id or "guest_anonymous"
        with SessionLocal() as db:
            row = db.query(ProjectModel).filter(
                ProjectModel.id == project_id,
                ProjectModel.user_id == owner
            ).first()
            if not row:
                return None

            if payload.name is not None:
                row.name = payload.name
            if payload.description is not None:
                row.description = payload.description
            if payload.color is not None:
                row.color = payload.color
            if payload.icon is not None:
                row.icon = payload.icon
            if payload.document_ids is not None:
                valid_ids = [
                    did for did in payload.document_ids
                    if document_service.get_document(did, user_id=owner)
                ]
                row.document_ids_json = json.dumps(valid_ids)

            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            t_count = db.query(ProjectThreadModel).filter(ProjectThreadModel.project_id == row.id).count()
            return self._to_project_schema(row, t_count)

    def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        owner = user_id or "guest_anonymous"
        with SessionLocal() as db:
            row = db.query(ProjectModel).filter(
                ProjectModel.id == project_id,
                ProjectModel.user_id == owner
            ).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            logger.info(f"Deleted Workspace Project: {project_id} by '{owner}'")
            return True

    def assign_document_to_project(self, project_id: str, document_id: str, user_id: Optional[str] = None) -> bool:
        owner = user_id or "guest_anonymous"
        if not document_service.get_document(document_id, user_id=owner):
            logger.warning(f"Rejected cross-tenant document assignment {document_id} by '{owner}'")
            return False

        with SessionLocal() as db:
            row = db.query(ProjectModel).filter(
                ProjectModel.id == project_id,
                ProjectModel.user_id == owner
            ).first()
            if not row:
                return False
            doc_ids = json.loads(row.document_ids_json or "[]")
            if document_id not in doc_ids:
                doc_ids.append(document_id)
                row.document_ids_json = json.dumps(doc_ids)
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Assigned doc {document_id} to project {project_id}")
            return True

    def remove_document_from_project(self, project_id: str, document_id: str, user_id: Optional[str] = None) -> bool:
        owner = user_id or "guest_anonymous"
        with SessionLocal() as db:
            row = db.query(ProjectModel).filter(
                ProjectModel.id == project_id,
                ProjectModel.user_id == owner
            ).first()
            if not row:
                return False
            doc_ids = json.loads(row.document_ids_json or "[]")
            if document_id in doc_ids:
                doc_ids.remove(document_id)
                row.document_ids_json = json.dumps(doc_ids)
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Removed doc {document_id} from project {project_id}")
            return True

    def list_threads(self, project_id: str, user_id: Optional[str] = None) -> List[ProjectThread]:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return []
        with SessionLocal() as db:
            rows = db.query(ProjectThreadModel).filter(
                ProjectThreadModel.project_id == project_id
            ).order_by(ProjectThreadModel.updated_at.desc()).all()
            return [self._to_thread_schema(r) for r in rows]

    def get_thread(self, project_id: str, thread_id: str, user_id: Optional[str] = None) -> Optional[ProjectThread]:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return None
        with SessionLocal() as db:
            row = db.query(ProjectThreadModel).filter(
                ProjectThreadModel.id == thread_id,
                ProjectThreadModel.project_id == project_id
            ).first()
            return self._to_thread_schema(row) if row else None

    def create_thread(self, project_id: str, title: str, user_id: Optional[str] = None) -> ProjectThread:
        owner = user_id or "guest_anonymous"
        proj = self.get_project(project_id, user_id=owner)
        if not proj:
            raise ValueError(f"Project '{project_id}' not found or access denied.")

        tid = f"thread_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            row = ProjectThreadModel(
                id=tid,
                project_id=project_id,
                user_id=owner,
                title=title,
                messages_json="[]",
                created_at=now,
                updated_at=now
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info(f"Created conversation thread '{title}' ({tid}) in project {project_id}")
            return self._to_thread_schema(row)

    def delete_thread(self, project_id: str, thread_id: str, user_id: Optional[str] = None) -> bool:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return False
        with SessionLocal() as db:
            row = db.query(ProjectThreadModel).filter(
                ProjectThreadModel.id == thread_id,
                ProjectThreadModel.project_id == project_id
            ).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            logger.info(f"Deleted thread {thread_id} from project {project_id}")
            return True

    def clear_guest_data(self, owner_id: Optional[str] = None) -> int:
        """
        Wipes temporary guest projects and threads for a guest session (or all guest sessions).
        """
        with SessionLocal() as db:
            if owner_id:
                if not owner_id.startswith("guest_"):
                    return 0
                projs = db.query(ProjectModel).filter(ProjectModel.user_id == owner_id).all()
            else:
                projs = db.query(ProjectModel).filter(
                    (ProjectModel.user_id.like("guest_%")) | (ProjectModel.user_id.is_(None))
                ).all()

            deleted_threads = 0
            for p in projs:
                deleted_threads += db.query(ProjectThreadModel).filter(ProjectThreadModel.project_id == p.id).count()
                db.delete(p)
            db.commit()
            logger.info(f"Cleaned up {len(projs)} guest project(s) and {deleted_threads} thread(s).")
            return deleted_threads

    def send_thread_message(
        self,
        project_id: str,
        thread_id: str,
        user_message: str,
        enable_web_search: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-turn follow-up Q&A strictly scoped to documents assigned to this project
        and accessible to `user_id`. If the project has 0 documents assigned, never falls back to
        other projects or other users' ChromaDB chunks.
        """
        owner = user_id or "guest_anonymous"
        proj = self.get_project(project_id, user_id=owner)
        if not proj:
            raise ValueError(f"Project '{project_id}' not found or access denied.")

        with SessionLocal() as db:
            row = db.query(ProjectThreadModel).filter(
                ProjectThreadModel.id == thread_id,
                ProjectThreadModel.project_id == project_id
            ).first()
            if not row:
                raise ValueError(f"Thread '{thread_id}' not found in project '{project_id}'.")
            messages = json.loads(row.messages_json or "[]")
            current_title = row.title

        accessible_ids = {d.document_id for d in document_service.list_documents(user_id=owner)}
        isolated_doc_ids = [did for did in proj.document_ids if did in accessible_ids]

        history = [{"role": m.get("role"), "content": m.get("content")} for m in messages]

        now_iso = datetime.now(timezone.utc).isoformat()
        user_msg = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "content": user_message,
            "timestamp": now_iso,
            "citations": None,
            "is_grounded": None,
            "chart_data": None
        }
        messages.append(user_msg)

        new_title = current_title
        if current_title in ["New Thread", "New Inquiry", "Untitled Thread", "General Discussion"] and len(messages) == 1:
            words = user_message.split()[:6]
            if words:
                new_title = " ".join(words).capitalize()

        if not isolated_doc_ids and not enable_web_search:
            from backend.app.schemas.chat import ChatResponse
            rag_response = ChatResponse(
                question=user_message,
                answer=(
                    f"No documents are currently assigned to project '{proj.name}'. "
                    "Switch to the Files tab and click 'Assign Document' (or enable Live Web Search) to query isolated project knowledge."
                ),
                citations=[],
                retrieved_chunks_count=0,
                reranked_chunks_count=0,
                is_grounded=False,
                unanswered_reason="Project has zero assigned documents."
            )
        else:
            rag_response = rag_pipeline.answer_question(
                question=user_message,
                document_ids=isolated_doc_ids,
                enable_web_search=enable_web_search,
                history=history
            )

        citations_list = [
            {
                "source_filename": c.source_filename,
                "page_number": c.page_number,
                "chunk_id": c.chunk_id,
                "snippet": c.snippet,
                "document_id": c.document_id,
                "relevance_score": c.relevance_score
            }
            for c in rag_response.citations
        ]

        asst_msg = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "assistant",
            "content": rag_response.answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "citations": citations_list,
            "is_grounded": rag_response.is_grounded,
            "chart_data": rag_response.chart_data
        }
        messages.append(asst_msg)

        with SessionLocal() as db:
            row = db.query(ProjectThreadModel).filter(
                ProjectThreadModel.id == thread_id,
                ProjectThreadModel.project_id == project_id
            ).first()
            if not row:
                raise ValueError("Thread was deleted while processing.")
            row.title = new_title
            row.messages_json = json.dumps(messages)
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            updated_thread = self._to_thread_schema(row)

        return {
            "thread": updated_thread,
            "user_message": ThreadMessage(**user_msg),
            "assistant_message": ThreadMessage(**asst_msg),
            "rag_response": rag_response
        }


project_service = ProjectService()
