"""
models/schemas.py — request/response contracts for the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Citation(BaseModel):
    id: str = Field(..., description="Source document ID, e.g. MKT-002")
    category: Optional[str] = Field(None, description="Intelligence category")
    title: Optional[str] = Field(None, description="Document title")
    file_id: Optional[str] = Field(None, description="OpenAI file ID in the vector store")


class ChatRequest(BaseModel):
    question: str = Field(..., description="Free-form executive question")
    previous_response_id: Optional[str] = Field(
        None,
        description="Response ID from a prior /chat call to continue the conversation. "
        "OpenAI maintains message history server-side.",
    )


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = Field(
        default_factory=list,
        description="Source documents retrieved by file_search",
    )
    model: str
    response_id: str = Field(
        ..., description="Pass back as previous_response_id to continue the conversation"
    )


# ── Executive feature schemas ────────────────────────────────────────────────

class BoardBriefRequest(BaseModel):
    topic: Optional[str] = Field(
        None,
        description="Optional focus topic for the brief, e.g. 'fintech regulation Q3'",
    )
    previous_response_id: Optional[str] = Field(None)


class BoardBriefResponse(BaseModel):
    brief: str
    citations: list[Citation] = Field(default_factory=list)
    response_id: str


class SummarizeRequest(BaseModel):
    previous_response_id: Optional[str] = Field(None)


class SummarizeResponse(BaseModel):
    digest: str
    citations: list[Citation] = Field(default_factory=list)
    response_id: str


# ── Vector Store schemas ────────────────────────────────────────────────────

class VectorStoreStatus(BaseModel):
    vector_store_id: Optional[str]
    file_count: int
    ready: bool


class FileInfo(BaseModel):
    file_id: str
    filename: str
    created_at: int
    status: str


class FileListResponse(BaseModel):
    vector_store_id: Optional[str]
    files: list[FileInfo]


class UploadFileResponse(BaseModel):
    file_id: str
    filename: str
    status: str


# backwards-compat alias
SetupStatusResponse = VectorStoreStatus
