from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import UserPublic

router = APIRouter()


@router.get("/tools/health")
def tools_health() -> dict:
    return {"status": "ok", "tools": "placeholder"}


@router.post("/draft")
def draft(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "draft", "message": "Drafting endpoint not implemented yet."}


@router.post("/comms/email")
def comms_email(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "communication", "message": "Communication endpoint not implemented yet."}


@router.post("/review/contract")
def review_contract(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "review", "message": "Review endpoint not implemented yet."}


@router.post("/transcribe")
def transcribe(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "transcribe", "message": "Transcription endpoint not implemented yet."}


@router.post("/transcribe/summary")
def transcribe_summary(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "transcribe_summary", "message": "Transcription summary not implemented yet."}


@router.post("/compliance/check")
def compliance_check(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "compliance", "message": "Compliance check not implemented yet."}


@router.get("/tasks")
def list_tasks(_: UserPublic = Depends(get_current_user)) -> Dict[str, List[Any]]:
    return {"status": "placeholder", "tool": "tasks", "tasks": []}


@router.post("/tasks")
def create_task(_: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "tasks", "task": {"id": "task-1", "message": "Tasks not implemented yet."}}


@router.put("/tasks/{task_id}")
def update_task(task_id: str, _: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return {"status": "placeholder", "tool": "tasks", "task": {"id": task_id, "message": "Tasks not implemented yet."}}


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, _: UserPublic = Depends(get_current_user)) -> None:
    return None
