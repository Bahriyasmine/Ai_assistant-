"""
main.py — FastAPI entrypoint.

Run from the assistant_v2/ directory:
    uvicorn main:app --reload --port 8000

Then open http://localhost:8000 to use the chat UI.
API docs: http://localhost:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from core.logging import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Personal AI Assistant",
    description=(
        "Secure strategic intelligence layer for a Chief Strategy Officer, "
        "built on the OpenAI Responses API with file_search (managed RAG)."
    ),
    version="1.0.0",
)

app.include_router(router)

# Serve static assets (CSS, JS if split out later)
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the chat UI."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
