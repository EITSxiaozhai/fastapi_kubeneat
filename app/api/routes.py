from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.workers.tasks import neat_yaml_file


router = APIRouter(prefix="/api")


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
async def upload_yaml(file: UploadFile = File(...)) -> dict[str, str]:
    settings = get_settings()
    suffix = Path(file.filename or "manifest.yaml").suffix.lower()
    if suffix not in {".yaml", ".yml"}:
        raise HTTPException(status_code=400, detail="只支持 .yaml 或 .yml 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="上传文件超过大小限制")

    upload_name = f"{uuid4().hex}{suffix}"
    upload_path = settings.upload_dir / upload_name
    upload_path.write_bytes(content)

    task = neat_yaml_file.delay(str(upload_path), file.filename or upload_name)
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/neat/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    task_result = AsyncResult(task_id, app=celery_app)
    response: dict[str, object] = {"task_id": task_id, "status": task_result.state}

    if task_result.state == "PROGRESS":
        response["progress"] = task_result.info
    elif task_result.successful():
        result = task_result.result
        response["result"] = {
            "original_filename": result["original_filename"],
            "resource_count": result["resource_count"],
            "result_filename": result["result_filename"],
            "download_url": f"/api/neat/tasks/{task_id}/download",
            "message": result["message"],
        }
    elif task_result.failed():
        response["error"] = str(task_result.result)

    return response


@router.get("/neat/tasks/{task_id}/download")
def download_result(task_id: str) -> FileResponse:
    task_result = AsyncResult(task_id, app=celery_app)
    if not task_result.successful():
        raise HTTPException(status_code=409, detail="任务尚未完成")

    result_path = Path(task_result.result["result_path"])
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        path=result_path,
        filename=task_result.result["result_filename"],
        media_type="application/x-yaml",
    )
