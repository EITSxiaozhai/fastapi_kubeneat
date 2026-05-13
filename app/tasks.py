from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from app.celery_app import celery_app
from app.config import get_settings


def _load_yaml_documents(raw_yaml: str) -> list[Any]:
    try:
        documents = [doc for doc in yaml.safe_load_all(raw_yaml) if doc is not None]
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 解析失败: {exc}") from exc

    if not documents:
        raise ValueError("上传文件中没有找到有效的 YAML 资源")
    return documents


def _run_kubectl_neat(document: Any) -> str:
    settings = get_settings()
    source = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)

    try:
        completed = subprocess.run(
            [settings.kubectl_neat_bin],
            input=source,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"未找到 kubectl-neat 可执行文件，请安装后设置 KUBECTL_NEAT_BIN。当前值: {settings.kubectl_neat_bin}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("kubectl-neat 执行超时") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"kubectl-neat 执行失败: {stderr}")

    output = completed.stdout.strip()
    if not output:
        raise RuntimeError("kubectl-neat 没有返回内容")
    return output


@celery_app.task(bind=True, name="app.tasks.neat_yaml_file")
def neat_yaml_file(self, upload_path: str, original_filename: str) -> dict[str, Any]:
    source_path = Path(upload_path)
    raw_yaml = source_path.read_text(encoding="utf-8")
    documents = _load_yaml_documents(raw_yaml)

    cleaned_documents: list[str] = []
    total = len(documents)
    for index, document in enumerate(documents, start=1):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": index,
                "total": total,
                "message": f"正在精简第 {index}/{total} 个资源",
            },
        )
        cleaned_documents.append(_run_kubectl_neat(document))

    settings = get_settings()
    result_filename = f"{source_path.stem}.neat.yaml"
    result_path = settings.result_dir / result_filename
    result_path.write_text("\n---\n".join(cleaned_documents) + "\n", encoding="utf-8")

    return {
        "original_filename": original_filename,
        "resource_count": total,
        "result_path": str(result_path),
        "result_filename": result_filename,
        "message": "精简完成",
    }
