from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv()


class Settings(BaseModel):
    app_name: str = "fastapi-kubeneat"
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    celery_task_always_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in {
        "1",
        "true",
        "yes",
    }
    kubectl_neat_bin: str = os.getenv("KUBECTL_NEAT_BIN", "kubectl-neat")
    runtime_dir: Path = Path(os.getenv("KUBENEAT_RUNTIME_DIR", "runtime_data"))
    upload_dir_name: str = "uploads"
    result_dir_name: str = "results"
    task_registry_name: str = "task_registry.jsonl"
    max_upload_bytes: int = int(os.getenv("KUBENEAT_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

    @property
    def upload_dir(self) -> Path:
        return self.runtime_dir / self.upload_dir_name

    @property
    def result_dir(self) -> Path:
        return self.runtime_dir / self.result_dir_name

    @property
    def task_registry_path(self) -> Path:
        return self.runtime_dir / self.task_registry_name


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.result_dir.mkdir(parents=True, exist_ok=True)
    settings.task_registry_path.touch(exist_ok=True)
    return settings
