from fastapi import FastAPI

from app import db
from app.routers import qa, search

app = FastAPI(title="LegalScraper API", version="0.0.1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def _startup() -> None:
    db.init_pool()


@app.on_event("shutdown")
def _shutdown() -> None:
    db.close_pool()


app.include_router(search.router)
app.include_router(qa.router)
