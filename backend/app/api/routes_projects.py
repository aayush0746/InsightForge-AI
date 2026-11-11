from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from backend.app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectThread,
    ThreadCreate,
    ThreadMessageRequest
)
from backend.app.services.project_service import project_service
from backend.app.api.routes_auth import get_current_user_optional
from backend.app.schemas.auth import User
from backend.app.core.security import sanitize_text_input
from backend.app.core.logger import logger

router = APIRouter(prefix="/projects", tags=["Workspace Projects & Threads"])

class AssignDocRequest(BaseModel):
    document_id: str

@router.get("", response_model=List[Project])
async def list_projects(current_user: Optional[User] = Depends(get_current_user_optional)):
    """
    List all workspace project collections.
    """
    user_id = current_user.id if current_user else None
    return project_service.list_projects(user_id=user_id)

@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Create a new isolated workspace collection (e.g., Legal Contracts, Market Research).
    """
    clean_name = sanitize_text_input(payload.name)
    payload.name = clean_name
    user_id = current_user.id if current_user else None
    return project_service.create_project(payload, user_id=user_id)

@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get project details and metadata.
    """
    user_id = current_user.id if current_user else None
    p = project_service.get_project(project_id, user_id=user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    return p

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Update project attributes.
    """
    user_id = current_user.id if current_user else None
    p = project_service.update_project(project_id, payload, user_id=user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return p

@router.delete("/guest/clear")
async def clear_guest_data():
    """
    Purges temporary guest scratchpad data and threads.
    """
    count = project_service.clear_guest_data()
    return {"success": True, "message": f"Cleared {count} temporary guest thread(s)."}

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Delete a workspace project collection and its threads.
    """
    user_id = current_user.id if current_user else None
    success = project_service.delete_project(project_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return {"success": True, "message": f"Project '{project_id}' deleted."}

@router.post("/{project_id}/documents")
async def assign_document(
    project_id: str,
    payload: AssignDocRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Assign a document into this project's isolated collection.
    """
    user_id = current_user.id if current_user else None
    success = project_service.assign_document_to_project(project_id, payload.document_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return {"success": True, "message": f"Document assigned to project {project_id}."}

@router.delete("/{project_id}/documents/{document_id}")
async def remove_document(
    project_id: str,
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Remove a document from this project's collection.
    """
    user_id = current_user.id if current_user else None
    success = project_service.remove_document_from_project(project_id, document_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return {"success": True, "message": f"Document removed from project {project_id}."}

# ==========================================
# Threads & Multi-Turn Conversational Memory (User Scoped)
# ==========================================

@router.get("/{project_id}/threads", response_model=List[ProjectThread])
async def list_threads(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List conversational threads belonging to this workspace project.
    """
    user_id = current_user.id if current_user else None
    return project_service.list_threads(project_id, user_id=user_id)

@router.post("/{project_id}/threads", response_model=ProjectThread, status_code=status.HTTP_201_CREATED)
async def create_thread(
    project_id: str,
    payload: ThreadCreate,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Create a new conversational thread in this project.
    """
    user_id = current_user.id if current_user else None
    clean_title = sanitize_text_input(payload.title)
    return project_service.create_thread(project_id, clean_title, user_id=user_id)

@router.get("/{project_id}/threads/{thread_id}", response_model=ProjectThread)
async def get_thread(
    project_id: str,
    thread_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get full thread messages and citations.
    """
    user_id = current_user.id if current_user else None
    thread = project_service.get_thread(project_id, thread_id, user_id=user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied.")
    return thread

@router.delete("/{project_id}/threads/{thread_id}")
async def delete_thread(
    project_id: str,
    thread_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Delete a conversational thread.
    """
    user_id = current_user.id if current_user else None
    success = project_service.delete_thread(project_id, thread_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found or access denied.")
    return {"success": True, "message": "Thread deleted."}

@router.post("/{project_id}/threads/{thread_id}/messages")
async def send_thread_message(
    project_id: str,
    thread_id: str,
    payload: ThreadMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Send a message (including follow-up requests like 'Elaborate on point 2')
    with full conversation memory and isolated document scoping.
    """
    user_id = current_user.id if current_user else None
    clean_msg = sanitize_text_input(payload.message)
    try:
        result = project_service.send_thread_message(
            project_id=project_id,
            thread_id=thread_id,
            user_message=clean_msg,
            enable_web_search=payload.enable_web_search,
            user_id=user_id
        )
        return {
            "success": True,
            "thread": result["thread"],
            "user_message": result["user_message"],
            "assistant_message": result["assistant_message"]
        }
    except Exception as e:
        logger.error(f"Failed to process thread message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

