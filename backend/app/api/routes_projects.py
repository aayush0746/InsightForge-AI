from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.app.api.routes_auth import get_effective_owner_id
from backend.app.core.logger import logger
from backend.app.core.security import sanitize_text_input
from backend.app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectThread,
    ThreadCreate,
    ThreadMessageRequest
)
from backend.app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Workspace Projects & Threads"])


class AssignDocRequest(BaseModel):
    document_id: str


@router.get("", response_model=List[Project])
async def list_projects(owner_id: str = Depends(get_effective_owner_id)):
    return await run_in_threadpool(project_service.list_projects, owner_id)


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    owner_id: str = Depends(get_effective_owner_id)
):
    payload.name = sanitize_text_input(payload.name)
    return await run_in_threadpool(project_service.create_project, payload, owner_id)


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    p = await run_in_threadpool(project_service.get_project, project_id, owner_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    return p


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    owner_id: str = Depends(get_effective_owner_id)
):
    p = await run_in_threadpool(project_service.update_project, project_id, payload, owner_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return p


@router.delete("/guest/clear")
async def clear_guest_data(owner_id: str = Depends(get_effective_owner_id)):
    if not owner_id.startswith("guest_"):
        return {"success": True, "message": "No guest session active."}
    count = await run_in_threadpool(project_service.clear_guest_data, owner_id)
    return {"success": True, "message": f"Cleared {count} temporary guest thread(s)."}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    success = await run_in_threadpool(project_service.delete_project, project_id, owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return {"success": True, "message": f"Project '{project_id}' deleted."}


@router.post("/{project_id}/documents")
async def assign_document(
    project_id: str,
    payload: AssignDocRequest,
    owner_id: str = Depends(get_effective_owner_id)
):
    success = await run_in_threadpool(
        project_service.assign_document_to_project,
        project_id,
        payload.document_id,
        owner_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project or document not found or access denied.")
    return {"success": True, "message": f"Document assigned to project {project_id}."}


@router.delete("/{project_id}/documents/{document_id}")
async def remove_document(
    project_id: str,
    document_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    success = await run_in_threadpool(
        project_service.remove_document_from_project,
        project_id,
        document_id,
        owner_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")
    return {"success": True, "message": f"Document removed from project {project_id}."}


@router.get("/{project_id}/threads", response_model=List[ProjectThread])
async def list_threads(
    project_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    return await run_in_threadpool(project_service.list_threads, project_id, owner_id)


@router.post("/{project_id}/threads", response_model=ProjectThread, status_code=status.HTTP_201_CREATED)
async def create_thread(
    project_id: str,
    payload: ThreadCreate,
    owner_id: str = Depends(get_effective_owner_id)
):
    clean_title = sanitize_text_input(payload.title)
    try:
        return await run_in_threadpool(project_service.create_thread, project_id, clean_title, owner_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/threads/{thread_id}", response_model=ProjectThread)
async def get_thread(
    project_id: str,
    thread_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    thread = await run_in_threadpool(project_service.get_thread, project_id, thread_id, owner_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied.")
    return thread


@router.delete("/{project_id}/threads/{thread_id}")
async def delete_thread(
    project_id: str,
    thread_id: str,
    owner_id: str = Depends(get_effective_owner_id)
):
    success = await run_in_threadpool(project_service.delete_thread, project_id, thread_id, owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found or access denied.")
    return {"success": True, "message": "Thread deleted."}


@router.post("/{project_id}/threads/{thread_id}/messages")
async def send_thread_message(
    project_id: str,
    thread_id: str,
    payload: ThreadMessageRequest,
    owner_id: str = Depends(get_effective_owner_id)
):
    clean_msg = sanitize_text_input(payload.message)
    try:
        result = await run_in_threadpool(
            project_service.send_thread_message,
            project_id=project_id,
            thread_id=thread_id,
            user_message=clean_msg,
            enable_web_search=payload.enable_web_search,
            user_id=owner_id
        )
        return {
            "success": True,
            "thread": result["thread"],
            "user_message": result["user_message"],
            "assistant_message": result["assistant_message"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process thread message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
