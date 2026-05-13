from __future__ import annotations

import shlex
import subprocess
from typing import Any

import yaml

from app.core.config import get_settings


def load_yaml_documents(raw_yaml: str) -> list[Any]:
    try:
        documents = [doc for doc in yaml.safe_load_all(raw_yaml) if doc is not None]
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 解析失败: {exc}") from exc

    if not documents:
        raise ValueError("上传文件中没有找到有效的 YAML 资源")
    return documents


def run_kubectl_neat(document: Any) -> str:
    settings = get_settings()
    source = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
    command = shlex.split(settings.kubectl_neat_bin)

    try:
        completed = subprocess.run(
            command,
            input=source,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"未找到 kubectl-neat 命令，请安装后设置 KUBECTL_NEAT_BIN。当前值: {settings.kubectl_neat_bin}"
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
