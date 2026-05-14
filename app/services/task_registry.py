from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.core.config import get_settings


def record_task_submission(task_id: str, original_filename: str, submission_type: str) -> None:
    settings = get_settings()
    payload = {
        "task_id": task_id,
        "original_filename": original_filename,
        "submission_type": submission_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with settings.task_registry_path.open("a", encoding="utf-8") as registry:
        registry.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _build_task_response(
    task_id: str,
    original_filename: str,
    created_at: str,
    submission_type: str,
) -> dict[str, Any]:
    task_result = AsyncResult(task_id, app=celery_app)
    response: dict[str, Any] = {
        "task_id": task_id,
        "status": task_result.state,
        "original_filename": original_filename,
        "created_at": created_at,
        "submission_type": submission_type,
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
            "download_url": f"/api/neat/tasks/{task_id}/download",
            "message": result["message"],
        }
    elif task_result.failed():
        response["error"] = str(task_result.result)

    return response


def get_task_detail(task_id: str) -> dict[str, Any]:
    records = list_task_records()
    record = next((item for item in records if item["task_id"] == task_id), None)
    original_filename = record["original_filename"] if record else ""
    created_at = record["created_at"] if record else ""
    submission_type = record["submission_type"] if record else ""
    return _build_task_response(task_id, original_filename, created_at, submission_type)


def list_task_records() -> list[dict[str, str]]:
    settings = get_settings()
    entries: list[dict[str, str]] = []

    with settings.task_registry_path.open("r", encoding="utf-8") as registry:
        for line in registry:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            task_id = str(raw.get("task_id", "")).strip()
            if not task_id:
                continue

            entries.append(
                {
                    "task_id": task_id,
                    "original_filename": str(raw.get("original_filename", "")).strip(),
                    "created_at": str(raw.get("created_at", "")).strip(),
                    "submission_type": str(raw.get("submission_type", "")).strip(),
                }
            )

    deduped: dict[str, dict[str, str]] = {}
    for entry in entries:
        deduped[entry["task_id"]] = entry

    return sorted(deduped.values(), key=lambda item: item["created_at"], reverse=True)


def list_task_details() -> list[dict[str, Any]]:
    return [
        _build_task_response(
            entry["task_id"],
            entry["original_filename"],
            entry["created_at"],
            entry["submission_type"],
        )
        for entry in list_task_records()
    ]
