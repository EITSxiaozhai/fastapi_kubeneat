from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.models import TaskRecord
from app.schemas.schemas import TaskCreate


def record_task_submission(db: Session, payload: TaskCreate) -> None:
    db.merge(
        TaskRecord(
            task_id=payload.task_id,
            user_id=payload.user_id,
            original_filename=payload.original_filename,
            submission_type=payload.submission_type,
        )
    )
    db.commit()


def _build_task_response(record: TaskRecord) -> dict[str, Any]:
    task_result = AsyncResult(record.task_id, app=celery_app)
    response: dict[str, Any] = {
        "task_id": record.task_id,
        "status": task_result.state,
        "original_filename": record.original_filename,
        "created_at": record.created_at.isoformat(),
        "submission_type": record.submission_type,
    }

    if task_result.state == "PROGRESS":
        response["progress"] = task_result.info
    elif task_result.successful():
        result = task_result.result
        response["result"] = {
            "original_filename": result["original_filename"],
            "original_content": result.get("original_content", ""),
            "resource_count": result["resource_count"],
            "result_filename": result["result_filename"],
            "result_content": result.get("result_content", ""),
            "download_url": f"/api/neat/tasks/{record.task_id}/download",
            "message": result["message"],
        }
    elif task_result.failed():
        response["error"] = str(task_result.result)

    return response


def get_task_detail(db: Session, task_id: str, user_id: str) -> dict[str, Any]:
    record = db.scalar(select(TaskRecord).where(TaskRecord.task_id == task_id, TaskRecord.user_id == user_id))
    if not record:
        return {
            "task_id": task_id,
            "status": "NOT_FOUND",
            "original_filename": "",
            "created_at": "",
            "submission_type": "",
            "error": "Task record does not exist.",
        }
    return _build_task_response(record)


def list_task_records(db: Session, user_id: str) -> list[TaskRecord]:
    return list(
        db.scalars(
            select(TaskRecord)
            .where(TaskRecord.user_id == user_id)
            .order_by(TaskRecord.created_at.desc())
        )
    )


def list_task_details(db: Session, user_id: str) -> list[dict[str, Any]]:
    return [_build_task_response(record) for record in list_task_records(db, user_id)]
