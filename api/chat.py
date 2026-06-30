"""Chat endpoints.

Routes
------
POST /chat              — ask a question (JSON response)
POST /chat/stream       — ask a question (SSE streaming)
POST /chat/board-brief  — structured executive board brief
POST /chat/summarize    — daily intelligence digest
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.exceptions import AssistantError, MissingAPIKeyError, VectorStoreNotConfiguredError
from core.logging import get_logger
from core.security import require_api_key
from models.schemas import (
    BoardBriefRequest,
    BoardBriefResponse,
    ChatRequest,
    ChatResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from services import openai_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Ask a question and receive a complete JSON response.
    Pass `previous_response_id` to continue a conversation.
    """
    try:
        return await openai_service.chat(request.question, request.previous_response_id)
    except VectorStoreNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except MissingAPIKeyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Ask a question and receive the answer as Server-Sent Events.

    Events:
    - {"type": "delta",  "text": "..."}
    - {"type": "done",   "response_id": "...", "citations": [...]}
    - {"type": "error",  "message": "..."}
    """
    try:
        generator = openai_service.stream_chat(request.question, request.previous_response_id)
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )
    except VectorStoreNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except MissingAPIKeyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/board-brief", response_model=BoardBriefResponse)
async def board_brief(request: BoardBriefRequest):
    """Generate a structured executive board brief.

    Returns a formatted markdown document with Executive Summary, Key Developments,
    Strategic Implications, and Recommended Actions — all sourced from the knowledge base.
    """
    try:
        return await openai_service.board_brief(request.topic, request.previous_response_id)
    except VectorStoreNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    """Generate the daily intelligence digest across all 6 categories.

    Covers: Market Signals, Competitor Moves, Regulatory Shifts,
    Internal Documents, Performance Alerts, Risk Indicators.
    """
    try:
        return await openai_service.summarize(request.previous_response_id)
    except VectorStoreNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=500, detail=str(e))
