from __future__ import annotations

from pathlib import Path
from typing import Any

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.services.kubeneat import load_yaml_documents, run_kubectl_neat

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.neat_yaml_file")
def neat_yaml_file(self, upload_path: str, original_filename: str) -> dict[str, Any]:
    source_path = Path(upload_path)
    raw_yaml = source_path.read_text(encoding="utf-8")
    documents = load_yaml_documents(raw_yaml)

    cleaned_documents: list[str] = []
    total = len(documents)
    for index, document in enumerate(documents, start=1):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": index,
                "total": total,
                "message": f"Cleaning resource {index}/{total}",
            },
        )
        cleaned_documents.append(run_kubectl_neat(document))

    settings = get_settings()
    result_filename = f"{source_path.stem}.neat.yaml"
    result_path = settings.result_dir / result_filename
    result_content = "\n---\n".join(cleaned_documents) + "\n"
    result_path.write_text(result_content, encoding="utf-8")

    return {
        "original_filename": original_filename,
        "original_content": raw_yaml,
        "resource_count": total,
        "result_path": str(result_path),
        "result_filename": result_filename,
        "result_content": result_content,
        "message": "Cleanup completed",
    }


def _delete_directory_files(directory: Path) -> dict[str, int]:
    deleted = 0
    failed = 0
    if not directory.is_dir():
        return {"deleted": deleted, "failed": failed}

    for path in directory.iterdir():
        if not path.is_file() or path.is_symlink():
            continue
        try:
            path.unlink()
            deleted += 1
        except OSError:
            logger.exception("Failed to delete %s", path)
            failed += 1
    return {"deleted": deleted, "failed": failed}


@celery_app.task(name="app.workers.tasks.cleanup_runtime_files")
def cleanup_runtime_files() -> dict[str, Any]:
    settings = get_settings()
    uploads = _delete_directory_files(settings.upload_dir)
    results = _delete_directory_files(settings.result_dir)
    summary = {
        "uploads_deleted": uploads["deleted"],
        "uploads_failed": uploads["failed"],
        "results_deleted": results["deleted"],
        "results_failed": results["failed"],
    }
    logger.info("Deleted runtime files: %s", summary)
    return summary
