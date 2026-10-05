from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.changes import router as changes_router
from app.api.competitors import router as competitors_router
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.ai import router as ai_router
from app.api.chat import router as chat_router
from app.api.observations import router as observations_router
from app.api.plans import router as plans_router
from app.api.promotions import router as promotions_router

app = FastAPI(title="Boost Competitive Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    detail = exc.detail
    payload = {
        "error": {
            "code": code,
            "message": detail if isinstance(detail, str) else "An error occurred.",
            "details": detail if isinstance(detail, dict) else None,
        }
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


app.include_router(health_router)
app.include_router(ai_router)
app.include_router(chat_router)
app.include_router(observations_router)
app.include_router(competitors_router)
app.include_router(plans_router)
app.include_router(devices_router)
app.include_router(promotions_router)
app.include_router(changes_router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_assets = frontend_dist / "assets"

if frontend_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_file = frontend_dist / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=503, detail="Frontend build is not available.")
    return FileResponse(index_file)
