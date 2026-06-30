"""
services/openai_service.py — wraps the OpenAI Responses API with file_search RAG.

  chat()        → full JSON response (non-streaming)
  stream_chat() → async generator yielding SSE lines (streaming)

Both support conversation chaining via previous_response_id.
Citations are extracted from file_search annotations, not parsed from prose.
"""

import json
from pathlib import Path

from core.config import settings, yaml_config
from core.client import get_client
from core.logging import get_logger
from core.exceptions import VectorStoreNotConfiguredError

logger = get_logger(__name__)

_assistant = yaml_config["assistant"]


# ── Non-streaming ────────────────────────────────────────────────────────────

async def chat(question: str, previous_response_id: str | None = None) -> dict:
    vs_id = _require_vector_store()
    client = await get_client()
    params = _build_params(question, vs_id, previous_response_id)

    response = await client.responses.create(**params)
    citations = _extract_citations(response)
    logger.info("answer done citations=%s", [c["id"] for c in citations])

    return {
        "question": question,
        "answer": response.output_text,
        "citations": citations,
        "model": settings.openai_model,
        "response_id": response.id,
    }


# ── Streaming ────────────────────────────────────────────────────────────────

async def stream_chat(question: str, previous_response_id: str | None = None):
    """Async generator yielding SSE lines.

    Events:
      data: {"type": "delta",  "text": "..."}
      data: {"type": "done",   "response_id": "...", "citations": [...]}
      data: {"type": "error",  "message": "..."}
    """
    vs_id = _require_vector_store()
    client = await get_client()
    params = _build_params(question, vs_id, previous_response_id)

    try:
        async with client.responses.stream(**params) as stream:
            async for event in stream:
                if getattr(event, "type", None) == "response.output_text.delta":
                    yield f"data: {json.dumps({'type': 'delta', 'text': event.delta})}\n\n"

            final = await stream.get_final_response()
            citations = _extract_citations(final)
            logger.info("stream done response_id=%s citations=%s", final.id, [c["id"] for c in citations])
            yield f"data: {json.dumps({'type': 'done', 'response_id': final.id, 'citations': citations})}\n\n"

    except Exception as e:
        logger.error("streaming error: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


# ── Board Brief ──────────────────────────────────────────────────────────────

async def board_brief(topic: str | None = None, previous_response_id: str | None = None) -> dict:
    """Generate a structured executive board brief from the knowledge base."""
    vs_id = _require_vector_store()
    client = await get_client()

    question = f"Prepare an executive board brief" + (f" focused on: {topic}" if topic else "")
    params = {
        "model":             settings.openai_model,
        "instructions":      _assistant["board_brief_instructions"],
        "input":             question,
        "temperature":       0.1,
        "max_output_tokens": 2048,
        "tools": [{"type": "file_search", "vector_store_ids": [vs_id]}],
    }
    if previous_response_id:
        params["previous_response_id"] = previous_response_id

    response = await client.responses.create(**params)
    citations = _extract_citations(response)
    logger.info("board brief done citations=%s", [c["id"] for c in citations])

    return {
        "brief": response.output_text,
        "citations": citations,
        "response_id": response.id,
    }


# ── Daily Digest ─────────────────────────────────────────────────────────────

async def summarize(previous_response_id: str | None = None) -> dict:
    """Generate a structured daily intelligence digest from all documents."""
    vs_id = _require_vector_store()
    client = await get_client()

    params = {
        "model":             settings.openai_model,
        "instructions":      _assistant["summarize_instructions"],
        "input":             "Generate today's intelligence digest covering all 6 categories.",
        "temperature":       0.1,
        "max_output_tokens": 2048,
        "tools": [{"type": "file_search", "vector_store_ids": [vs_id]}],
    }
    if previous_response_id:
        params["previous_response_id"] = previous_response_id

    response = await client.responses.create(**params)
    citations = _extract_citations(response)
    logger.info("digest done citations=%s", [c["id"] for c in citations])

    return {
        "digest": response.output_text,
        "citations": citations,
        "response_id": response.id,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_vector_store() -> str:
    vs_id = settings.resolved_vector_store_id
    if not vs_id:
        raise VectorStoreNotConfiguredError(
            "No vector store configured. Call POST /vector-store first."
        )
    return vs_id


def _build_params(question: str, vector_store_id: str, previous_response_id: str | None) -> dict:
    params: dict = {
        "model":             settings.openai_model,
        "instructions":      _assistant["instructions"],
        "input":             question,
        "temperature":       0.2,
        "max_output_tokens": 2048,
        "tools": [{"type": "file_search", "vector_store_ids": [vector_store_id]}],
    }
    if previous_response_id:
        params["previous_response_id"] = previous_response_id
        logger.info("continuing conversation prev_response=%s", previous_response_id)
    else:
        logger.info("new conversation model=%s vs=%s", settings.openai_model, vector_store_id)
    return params


def _extract_citations(response) -> list[dict]:
    """Extracts file-level citations from file_search annotations.

    OpenAI's file_citation only identifies which FILE was matched (file_id,
    filename), not which section within it. Since the knowledge base is one
    combined file, we can't claim to know the specific document ID, category,
    or title that was actually used — doing so would be a fabricated guess.
    We report the source file honestly instead.
    """
    seen: dict[str, dict] = {}
    for item in response.output:
        if getattr(item, "type", None) != "message":
            continue
        for part in item.content:
            if getattr(part, "type", None) != "output_text":
                continue
            for ann in part.annotations:
                if getattr(ann, "type", None) != "file_citation":
                    continue
                file_id = ann.file_id
                if file_id in seen:
                    continue
                doc_id = Path(ann.filename).stem if ann.filename else file_id
                seen[file_id] = {
                    "id": doc_id,
                    "category": None,
                    "title": "CSO Intelligence Knowledge Base",
                    "file_id": file_id,
                }
    return list(seen.values())
