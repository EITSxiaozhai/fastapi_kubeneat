from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


def parse_csv_env(value: str, default: list[str]) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


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
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://kubeneat:kubeneat@localhost:5432/kubeneat")
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
    max_upload_bytes: int = int(os.getenv("KUBENEAT_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    cors_origins: list[str] = parse_csv_env(
        os.getenv(
            "KUBENEAT_CORS_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000,https://tools.exploit-db.xyz,https://kubeneat.exploit-db.xyz",
        ),
        [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://tools.exploit-db.xyz",
            "https://kubeneat.exploit-db.xyz",
        ],
    )
    jwt_ttl_hours: int = int(os.getenv("KUBENEAT_JWT_TTL_HOURS", os.getenv("KUBENEAT_SESSION_TTL_HOURS", "24")))
    jwt_secret_key: str = os.getenv("KUBENEAT_JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = os.getenv("KUBENEAT_JWT_ISSUER", "fastapi-kubeneat")
    jwt_redis_url: str = os.getenv("KUBENEAT_JWT_REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    jwt_redis_key_prefix: str = os.getenv("KUBENEAT_JWT_REDIS_KEY_PREFIX", "kubeneat:jwt")
    initial_admin_username: str = os.getenv("KUBENEAT_INITIAL_ADMIN_USERNAME", "admin")
    initial_admin_password: str = os.getenv("KUBENEAT_INITIAL_ADMIN_PASSWORD", "ChangeMe123!")
    initial_admin_email: str = os.getenv("KUBENEAT_INITIAL_ADMIN_EMAIL", "")
    initial_admin_display_name: str = os.getenv("KUBENEAT_INITIAL_ADMIN_DISPLAY_NAME", "KubeNeat Admin")
    cloudflare_turnstile_secret_key: str = os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "")
    cloudflare_turnstile_required: bool = os.getenv("CLOUDFLARE_TURNSTILE_REQUIRED", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    cloudflare_turnstile_siteverify_url: str = os.getenv(
        "CLOUDFLARE_TURNSTILE_SITEVERIFY_URL",
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    )

    @property
    def upload_dir(self) -> Path:
        return self.runtime_dir / self.upload_dir_name

    @property
    def result_dir(self) -> Path:
        return self.runtime_dir / self.result_dir_name


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.result_dir.mkdir(parents=True, exist_ok=True)
    return settings
