import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectThread,
    ThreadCreate,
    ThreadMessage,
    CitationInfo
)
from backend.app.rag.pipeline import rag_pipeline

PROJECTS_FILE = settings.DATA_DIR / "projects.json"

class ProjectService:
    """
    Manages Workspace Projects / Collections:
    - Dedicated, isolated workspaces ensuring searches in one collection never mix with another.
    - Multi-turn conversational threading with full context memory.
    """

    def __init__(self):
        self._ensure_storage()

    def _ensure_storage(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROJECTS_FILE.exists():
            initial_data = {
                "projects": {
                    "proj_legal": {
                        "id": "proj_legal",
                        "name": "Legal Contracts & Compliance",
                        "description": "Contracts, NDAs, service terms, and liability agreements.",
                        "color": "indigo",
                        "icon": "shield",
                        "document_ids": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    },
                    "proj_academic": {
                        "id": "proj_academic",
                        "name": "College Admissions & Rules",
                        "description": "Student handbooks, code of conduct, leave policies, and syllabus.",
                        "color": "emerald",
                        "icon": "graduation-cap",
                        "document_ids": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    },
                    "proj_market": {
                        "id": "proj_market",
                        "name": "Market & Financial Research",
                        "description": "Financial reports, industry trends, and business data.",
                        "color": "amber",
                        "icon": "trending-up",
                        "document_ids": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                "threads": {}
            }
            self._save_raw(initial_data)

    def _load_raw(self) -> Dict[str, Any]:
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load projects.json: {e}")
            return {"projects": {}, "threads": {}}

    def _save_raw(self, data: Dict[str, Any]):
        try:
            with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save projects.json: {e}")

    # ==========================================
    # Project Operations (User Scoped)
    # ==========================================

    def list_projects(self, user_id: Optional[str] = None) -> List[Project]:
        data = self._load_raw()
        projects_dict = data.get("projects", {})
        threads_dict = data.get("threads", {})

        result = []

        if user_id:
            # 1. Authenticated User: Strictly return ONLY their projects
            user_projects = [
                pdata for pdata in projects_dict.values()
                if pdata.get("user_id") == user_id
            ]

            # If user has no workspace yet, auto-provision a starter project
            if not user_projects:
                new_p = self.create_project(
                    ProjectCreate(
                        name="My Research Workspace",
                        description="Personal research workspace & conversational threads",
                        color="indigo",
                        icon="folder"
                    ),
                    user_id=user_id
                )
                return [new_p]

            for pdata in user_projects:
                pid = pdata["id"]
                t_count = sum(1 for t in threads_dict.values() if t.get("project_id") == pid)
                doc_ids = pdata.get("document_ids", [])
                result.append(
                    Project(
                        id=pid,
                        name=pdata["name"],
                        description=pdata.get("description", ""),
                        color=pdata.get("color", "indigo"),
                        icon=pdata.get("icon", "folder"),
                        document_ids=doc_ids,
                        created_at=pdata.get("created_at", ""),
                        updated_at=pdata.get("updated_at", ""),
                        thread_count=t_count,
                        document_count=len(doc_ids),
                        user_id=user_id
                    )
                )
        else:
            # 2. Guest User: Provide isolated temporary scratchpad
            guest_pid = "proj_guest_scratchpad"
            guest_proj = projects_dict.get(guest_pid)
            if not guest_proj:
                now = datetime.now(timezone.utc).isoformat()
                guest_proj = {
                    "id": guest_pid,
                    "name": "Temporary Guest Scratchpad",
                    "description": "Temporary session for exploration. Chats exist only for this visit.",
                    "color": "amber",
                    "icon": "sparkles",
                    "document_ids": [],
                    "created_at": now,
                    "updated_at": now,
                    "user_id": None,
                    "is_guest": True
                }
                projects_dict[guest_pid] = guest_proj
                data["projects"] = projects_dict
                self._save_raw(data)

            t_count = sum(1 for t in threads_dict.values() if t.get("project_id") == guest_pid)
            doc_ids = guest_proj.get("document_ids", [])
            result.append(
                Project(
                    id=guest_pid,
                    name=guest_proj["name"],
                    description=guest_proj.get("description", ""),
                    color=guest_proj.get("color", "amber"),
                    icon=guest_proj.get("icon", "sparkles"),
                    document_ids=doc_ids,
                    created_at=guest_proj.get("created_at", ""),
                    updated_at=guest_proj.get("updated_at", ""),
                    thread_count=t_count,
                    document_count=len(doc_ids),
                    user_id=None
                )
            )

        result.sort(key=lambda x: x.created_at)
        return result

    def get_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Project]:
        projects = self.list_projects(user_id=user_id)
        for p in projects:
            if p.id == project_id:
                return p
        return None

    def create_project(self, payload: ProjectCreate, user_id: Optional[str] = None) -> Project:
        data = self._load_raw()
        pid = f"proj_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        effective_user_id = user_id or payload.user_id

        proj_record = {
            "id": pid,
            "name": payload.name,
            "description": payload.description or "",
            "color": payload.color or "indigo",
            "icon": payload.icon or "folder",
            "document_ids": payload.document_ids or [],
            "created_at": now,
            "updated_at": now,
            "user_id": effective_user_id
        }
        data.setdefault("projects", {})[pid] = proj_record
        self._save_raw(data)
        logger.info(f"Created new Workspace Project: {payload.name} ({pid}) for user {effective_user_id}")

        return Project(
            id=pid,
            name=proj_record["name"],
            description=proj_record["description"],
            color=proj_record["color"],
            icon=proj_record["icon"],
            document_ids=proj_record["document_ids"],
            created_at=now,
            updated_at=now,
            thread_count=0,
            document_count=len(proj_record["document_ids"]),
            user_id=effective_user_id
        )

    def update_project(self, project_id: str, payload: ProjectUpdate, user_id: Optional[str] = None) -> Optional[Project]:
        # Verify ownership
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return None

        data = self._load_raw()
        p = data.get("projects", {}).get(project_id)
        if not p:
            return None

        if payload.name is not None:
            p["name"] = payload.name
        if payload.description is not None:
            p["description"] = payload.description
        if payload.color is not None:
            p["color"] = payload.color
        if payload.icon is not None:
            p["icon"] = payload.icon
        if payload.document_ids is not None:
            p["document_ids"] = payload.document_ids

        p["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_raw(data)
        return self.get_project(project_id, user_id=user_id)

    def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        # Verify ownership
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return False

        data = self._load_raw()
        projects = data.get("projects", {})
        if project_id not in projects:
            return False

        del projects[project_id]

        # Clean associated threads
        threads = data.get("threads", {})
        data["threads"] = {tid: t for tid, t in threads.items() if t.get("project_id") != project_id}

        self._save_raw(data)
        logger.info(f"Deleted Workspace Project: {project_id} by user {user_id}")
        return True

    def assign_document_to_project(self, project_id: str, document_id: str, user_id: Optional[str] = None) -> bool:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return False

        data = self._load_raw()
        projects = data.get("projects", {})
        if project_id not in projects:
            return False

        doc_ids = projects[project_id].setdefault("document_ids", [])
        if document_id not in doc_ids:
            doc_ids.append(document_id)
            projects[project_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_raw(data)
            logger.info(f"Assigned doc {document_id} to project {project_id}")
        return True

    def remove_document_from_project(self, project_id: str, document_id: str, user_id: Optional[str] = None) -> bool:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return False

        data = self._load_raw()
        projects = data.get("projects", {})
        if project_id not in projects:
            return False

        doc_ids = projects[project_id].get("document_ids", [])
        if document_id in doc_ids:
            doc_ids.remove(document_id)
            projects[project_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_raw(data)
            logger.info(f"Removed doc {document_id} from project {project_id}")
        return True

    # ==========================================
    # Conversational Thread Operations (User Scoped Memory)
    # ==========================================

    def list_threads(self, project_id: str, user_id: Optional[str] = None) -> List[ProjectThread]:
        # Enforce that project belongs to this user
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return []

        data = self._load_raw()
        threads_dict = data.get("threads", {})
        threads = [
            ProjectThread(**t)
            for t in threads_dict.values()
            if t.get("project_id") == project_id
        ]
        threads.sort(key=lambda x: x.updated_at, reverse=True)
        return threads

    def get_thread(self, project_id: str, thread_id: str, user_id: Optional[str] = None) -> Optional[ProjectThread]:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return None

        data = self._load_raw()
        threads_dict = data.get("threads", {})
        t = threads_dict.get(thread_id)
        if t and t.get("project_id") == project_id:
            return ProjectThread(**t)
        return None

    def create_thread(self, project_id: str, title: str, user_id: Optional[str] = None) -> ProjectThread:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            raise ValueError(f"Project '{project_id}' not found or access denied.")

        data = self._load_raw()
        tid = f"thread_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "id": tid,
            "project_id": project_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "user_id": user_id
        }
        data.setdefault("threads", {})[tid] = record
        self._save_raw(data)
        logger.info(f"Created conversation thread: '{title}' ({tid}) in project {project_id} (user {user_id})")
        return ProjectThread(**record)

    def delete_thread(self, project_id: str, thread_id: str, user_id: Optional[str] = None) -> bool:
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            return False

        data = self._load_raw()
        threads = data.get("threads", {})
        if thread_id in threads and threads[thread_id].get("project_id") == project_id:
            del threads[thread_id]
            self._save_raw(data)
            logger.info(f"Deleted thread {thread_id} from project {project_id}")
            return True
        return False

    def clear_guest_data(self) -> int:
        """
        Wipes temporary guest scratchpad and temporary threads when a guest session ends.
        """
        data = self._load_raw()
        threads = data.get("threads", {})
        to_delete = [
            tid for tid, t in threads.items()
            if t.get("project_id") == "proj_guest_scratchpad" or t.get("user_id") is None
        ]
        for tid in to_delete:
            del threads[tid]

        # Reset guest project document list
        if "proj_guest_scratchpad" in data.get("projects", {}):
            data["projects"]["proj_guest_scratchpad"]["document_ids"] = []

        self._save_raw(data)
        logger.info(f"Cleaned up {len(to_delete)} temporary guest thread(s).")
        return len(to_delete)

    def send_thread_message(
        self,
        project_id: str,
        thread_id: str,
        user_message: str,
        enable_web_search: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-turn follow-up question answering with project document isolation.
        Searches ONLY across documents assigned to this project and accessible to this user!
        """
        proj = self.get_project(project_id, user_id=user_id)
        if not proj:
            raise ValueError(f"Project '{project_id}' not found or access denied.")

        data = self._load_raw()
        threads = data.get("threads", {})
        if thread_id not in threads or threads[thread_id].get("project_id") != project_id:
            raise ValueError(f"Thread '{thread_id}' not found in project '{project_id}'.")

        thread = threads[thread_id]

        # 1. Project Document Isolation: If project has documents, strictly scope retrieval to them!
        isolated_doc_ids = proj.document_ids
        if not isolated_doc_ids:
            isolated_doc_ids = None

        # 2. Extract multi-turn history memory from thread
        history = []
        for msg in thread.get("messages", []):
            history.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })

        # 3. Create User Message Record
        user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        user_msg = {
            "id": user_msg_id,
            "role": "user",
            "content": user_message,
            "timestamp": now,
            "citations": None,
            "is_grounded": None,
            "chart_data": None
        }
        thread.setdefault("messages", []).append(user_msg)

        # 4. If thread is titled "New Thread" or default, name it from the question
        if thread.get("title") in ["New Thread", "New Inquiry", "Untitled Thread"]:
            words = user_message.split()[:6]
            thread["title"] = " ".join(words).capitalize()

        # 5. Call RAG Pipeline with Document Scoping & Conversation History
        rag_response = rag_pipeline.answer_question(
            question=user_message,
            document_ids=isolated_doc_ids,
            enable_web_search=enable_web_search,
            history=history
        )

        # 6. Create Assistant Message Record with Citations & Chart
        asst_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
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
            "id": asst_msg_id,
            "role": "assistant",
            "content": rag_response.answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "citations": citations_list,
            "is_grounded": rag_response.is_grounded,
            "chart_data": rag_response.chart_data
        }
        thread["messages"].append(asst_msg)
        thread["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_raw(data)

        return {
            "thread": ProjectThread(**thread),
            "user_message": ThreadMessage(**user_msg),
            "assistant_message": ThreadMessage(**asst_msg),
            "rag_response": rag_response
        }

project_service = ProjectService()

