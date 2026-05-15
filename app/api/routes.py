from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.database.db import get_db
from app.api.deps import get_bearer_token, get_current_user, get_optional_current_user
from app.models.models import TaskRecord, User
from app.schemas.schemas import CurrentUserResponse, LoginRequest, LoginResponse, RevokeTokenRequest, TaskCreate
from app.services.security import create_access_token, revoke_jwt_id, revoke_jwt_token, verify_password, verify_turnstile_token
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


@router.get("/currentUser", response_model=CurrentUserResponse)
def current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        data={
            "name": current_user.display_name,
            "avatar": "",
            "userid": current_user.id,
            "email": current_user.email,
            "access": current_user.access,
        }
    )


@router.post("/login/account", response_model=LoginResponse)
async def login_account(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    turnstile_valid = await verify_turnstile_token(payload.turnstile_token, request.client.host if request.client else None)
    if not turnstile_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cloudflare Turnstile verification failed.")

    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    token, expires_at, jti = create_access_token(user)
    return LoginResponse(status="ok", currentAuthority=user.access, token=token, expiresAt=expires_at, jti=jti)


@router.post("/login/outLogin")
def logout(
    token: str | None = Depends(get_bearer_token),
) -> dict[str, object]:
    revoke_jwt_token(token)
    return {"success": True}


@router.post("/login/revoke")
def revoke_token(
    payload: RevokeTokenRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.access != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return {"success": revoke_jwt_id(payload.jti)}


@router.post("/neat/upload")
async def upload_yaml(
    file: UploadFile | None = File(default=None),
    content: str | None = Form(default=None),
    filename: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
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
    record_task_submission(
        db,
        TaskCreate(
            task_id=task.id,
            original_filename=original_filename,
            submission_type=submission_type,
            user_id=current_user.id if current_user else None,
        ),
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/neat/tasks")
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, object]:
    tasks = list_task_details(db, current_user.id)
    return {"total": len(tasks), "items": tasks}


@router.get("/neat/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> dict[str, object]:
    return get_task_detail(db, task_id, current_user.id if current_user else None)


@router.get("/neat/tasks/{task_id}/download")
def download_result(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> FileResponse:
    user_id = current_user.id if current_user else None
    record = db.scalar(select(TaskRecord).where(TaskRecord.task_id == task_id, TaskRecord.user_id == user_id))
    if not record:
        raise HTTPException(status_code=404, detail="Task record does not exist.")

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
