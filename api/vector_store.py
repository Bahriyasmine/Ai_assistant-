"""Vector store management endpoints.

Routes
------
GET    /vector-store/status          — current status and file count
POST   /vector-store                 — create store and index all data/ files
DELETE /vector-store                 — delete the configured store
GET    /vector-store/files           — list files with metadata
POST   /vector-store/files           — upload a single file
DELETE /vector-store/files/{file_id} — remove a file
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from core.exceptions import AssistantError, MissingAPIKeyError, NoDataFilesError
from core.logging import get_logger
from core.security import require_api_key
from models.schemas import (
    VectorStoreStatus,
    FileListResponse,
    UploadFileResponse,
)
from services import vector_store as vs

logger = get_logger(__name__)

router = APIRouter(
    prefix="/vector-store",
    tags=["vector-store"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/status", response_model=VectorStoreStatus)
async def get_status():
    """Current vector store configuration and indexed file count."""
    try:
        return await vs.vector_store_status()
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store/status failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=VectorStoreStatus, status_code=201)
async def create_vector_store():
    """Create the vector store and upload all documents from data/.
    Idempotent: if a store already exists, only missing files are synced.
    """
    try:
        await vs.create_and_populate_vector_store()
    except NoDataFilesError as e:
        logger.error("vector-store create failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store create failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return await vs.vector_store_status()


@router.delete("", status_code=204)
async def delete_vector_store():
    """Delete the configured vector store and clear its stored ID.
    Safe to call when no store is configured (returns 204 with no action).
    """
    try:
        await vs.delete_vector_store()
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store delete failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=FileListResponse)
async def list_files():
    """List all files currently indexed in the vector store."""
    try:
        return await vs.list_store_files_detailed()
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store/files list failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files", response_model=UploadFileResponse, status_code=201)
async def upload_file(file: UploadFile = File(...)):
    """Upload a single document to the vector store and index it.
    Accepts any text file. The file is immediately available for file_search.
    """
    try:
        content = await file.read()
        return await vs.upload_file(content, file.filename)
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store/files upload failed file=%s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(file_id: str):
    """Remove a file from the vector store and the Files API by its OpenAI file ID."""
    try:
        await vs.delete_file(file_id)
    except (MissingAPIKeyError, AssistantError) as e:
        logger.error("vector-store/files delete failed file_id=%s: %s", file_id, e)
        raise HTTPException(status_code=500, detail=str(e))
