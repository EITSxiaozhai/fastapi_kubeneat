from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.services.task_registry import get_task_detail, list_task_details, record_task_submission
from app.workers.tasks import neat_yaml_file


router = APIRouter(prefix="/api")


def _persist_yaml_submission(content: bytes, original_filename: str) -> tuple[Path, str]:
    settings = get_settings()
    suffix = Path(original_filename).suffix.lower()
    if suffix not in {".yaml", ".yml"}:
        raise HTTPException(status_code=400, detail="Only .yaml or .yml files are supported.")

    if not content:
        raise HTTPException(status_code=400, detail="YAML content cannot be empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="YAML content exceeds the upload size limit.")

    upload_name = f"{uuid4().hex}{suffix}"
    upload_path = settings.upload_dir / upload_name
    upload_path.write_bytes(content)
    return upload_path, original_filename


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/currentUser")
def current_user() -> dict[str, object]:
    return {
        "success": True,
        "data": {
            "name": "KubeNeat User",
            "avatar": "",
            "userid": "kubeneat",
            "access": "admin",
        },
    }


@router.post("/login/account")
def login_account() -> dict[str, object]:
    return {
        "status": "ok",
        "type": "account",
        "currentAuthority": "admin",
    }


@router.post("/login/outLogin")
def logout() -> dict[str, object]:
    return {"success": True}


@router.post("/neat/upload")
async def upload_yaml(
    file: UploadFile | None = File(default=None),
    content: str | None = Form(default=None),
    filename: str | None = Form(default=None),
) -> dict[str, str]:
    if file is not None:
        source_name = file.filename or "manifest.yaml"
        upload_path, original_filename = _persist_yaml_submission(await file.read(), source_name)
        submission_type = "file"
    elif content is not None:
        source_name = (filename or "manual-input.yaml").strip() or "manual-input.yaml"
        upload_path, original_filename = _persist_yaml_submission(content.encode("utf-8"), source_name)
        submission_type = "manual"
    else:
        raise HTTPException(status_code=400, detail="Provide either a YAML file or YAML text content.")

    task = neat_yaml_file.delay(str(upload_path), original_filename)
    record_task_submission(task.id, original_filename, submission_type)
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/neat/tasks")
def list_tasks() -> dict[str, object]:
    tasks = list_task_details()
    return {"total": len(tasks), "items": tasks}


@router.get("/neat/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    return get_task_detail(task_id)


@router.get("/neat/tasks/{task_id}/download")
def download_result(task_id: str) -> FileResponse:
    task_result = AsyncResult(task_id, app=celery_app)
    if not task_result.successful():
        raise HTTPException(status_code=409, detail="Task is not finished yet.")

    result_path = Path(task_result.result["result_path"])
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file does not exist.")

    return FileResponse(
        path=result_path,
        filename=task_result.result["result_filename"],
        media_type="application/x-yaml",
    )
