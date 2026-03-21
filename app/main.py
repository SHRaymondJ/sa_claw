from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.api.crm import router as crm_router
from app.config import get_app_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="导购工作台", lifespan=lifespan)
app.include_router(crm_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/crm")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _get_frontend_file(path: str) -> Path:
    dist_dir = get_app_settings().frontend_dist
    target = (dist_dir / path).resolve()
    if not str(target).startswith(str(dist_dir.resolve())):
        raise HTTPException(status_code=404, detail="not found")
    return target


@app.get("/crm", response_class=FileResponse, include_in_schema=False)
def crm_index() -> FileResponse:
    index_path = _get_frontend_file("index.html")
    if not index_path.exists():
        raise HTTPException(status_code=503, detail="frontend build not found")
    return FileResponse(index_path)


@app.get("/crm/{path:path}", response_class=FileResponse, include_in_schema=False)
def crm_assets(path: str) -> FileResponse:
    target = _get_frontend_file(path)
    if target.exists() and target.is_file():
        return FileResponse(target)

    index_path = _get_frontend_file("index.html")
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=503, detail="frontend build not found")
