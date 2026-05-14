from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database.db import SessionLocal, init_db
from app.services.security import ensure_initial_admin


app = FastAPI(title="fastapi-kubeneat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
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
