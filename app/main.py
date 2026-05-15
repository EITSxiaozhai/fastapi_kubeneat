from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.database.db import SessionLocal, init_db
from app.services.security import ensure_initial_admin


settings = get_settings()
app = FastAPI(title="fastapi-kubeneat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    with SessionLocal() as db:
        ensure_initial_admin(db)
