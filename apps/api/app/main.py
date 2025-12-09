from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.infrastructure.db import connection as db
from app.infrastructure.db import ingestion_repository, user_repository, refresh_token_repository, research_repository
from app.interfaces.api.routers import auth, qa, research, search, upload, summary, tools


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_pool()
    ingestion_repository.ensure_table()
    user_repository.ensure_table()
    refresh_token_repository.ensure_table()
    research_repository.ensure_table()
    try:
        yield
    finally:
        db.close_pool()


app = FastAPI(title="LegalScraper API", version="0.0.1", lifespan=lifespan)

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(search.router)
app.include_router(qa.router)
app.include_router(research.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(summary.router)
app.include_router(tools.router)
