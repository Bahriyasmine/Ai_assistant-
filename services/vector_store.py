"""
services/vector_store.py — manages the OpenAI vector store lifecycle.
All management operations (create, delete, file upload/delete) live here.
"""

import io
from pathlib import Path

from core.config import settings, yaml_config
from core.client import get_client
from core.exceptions import AssistantError, NoDataFilesError
from core.logging import get_logger

logger = get_logger(__name__)

_assistant = yaml_config["assistant"]


# ── Create / Populate ────────────────────────────────────────────────────────

async def create_and_populate_vector_store() -> str:
    """Creates a vector store (if none configured) and uploads all files from data/.
    Idempotent: existing store → only missing files are uploaded.
    """
    client = await get_client()
    data_dir = Path(settings.data_dir)
    file_paths = sorted(data_dir.glob("*.txt"))
    if not file_paths:
        raise NoDataFilesError(f"No .txt files found in {data_dir}")

    local_filenames = {p.name for p in file_paths}
    vs_id = settings.resolved_vector_store_id

    if vs_id:
        existing = await _list_store_filenames(client, vs_id)
        missing = local_filenames - existing
        if not missing:
            logger.info("vector store already in sync id=%s files=%d", vs_id, len(existing))
            return vs_id
        to_upload = [p for p in file_paths if p.name in missing]
        logger.info("syncing %d missing files to store id=%s", len(missing), vs_id)
    else:
        vs = await client.vector_stores.create(name=_assistant["vector_store_name"])
        vs_id = vs.id
        logger.info("created vector store id=%s", vs_id)
        to_upload = file_paths

    for path in to_upload:
        with open(path, "rb") as f:
            await client.vector_stores.files.upload_and_poll(vector_store_id=vs_id, file=f)
        logger.info("uploaded %s", path.name)

    settings.save_vector_store_id(vs_id)
    return vs_id


# ── Delete ───────────────────────────────────────────────────────────────────

async def delete_vector_store() -> None:
    vs_id = settings.resolved_vector_store_id
    if not vs_id:
        return
    client = await get_client()
    try:
        await client.vector_stores.delete(vs_id)
        logger.info("deleted vector store id=%s", vs_id)
    except Exception as e:
        raise AssistantError(f"Could not delete vector store: {e}") from e
    id_file = Path(__file__).resolve().parent.parent / ".vector_store_id"
    if id_file.exists():
        id_file.unlink()


# ── Status ───────────────────────────────────────────────────────────────────

async def vector_store_status() -> dict:
    vs_id = settings.resolved_vector_store_id
    file_count = 0
    if vs_id:
        client = await get_client()
        files = await client.vector_stores.files.list(vector_store_id=vs_id)
        file_count = len(files.data)
    return {"vector_store_id": vs_id, "file_count": file_count, "ready": bool(vs_id and file_count > 0)}


# ── File listing ─────────────────────────────────────────────────────────────

async def list_store_files_detailed() -> dict:
    vs_id = settings.resolved_vector_store_id
    if not vs_id:
        return {"vector_store_id": None, "files": []}
    client = await get_client()
    vs_files = await client.vector_stores.files.list(vector_store_id=vs_id)
    files = []
    for f in vs_files.data:
        try:
            meta = await client.files.retrieve(f.id)
            files.append({"file_id": f.id, "filename": meta.filename, "created_at": f.created_at, "status": f.status})
        except Exception as e:
            logger.warning("could not retrieve metadata for file_id=%s: %s", f.id, e)
            files.append({"file_id": f.id, "filename": f.id, "created_at": f.created_at, "status": f.status})
    return {"vector_store_id": vs_id, "files": files}


# ── Upload single file ───────────────────────────────────────────────────────

async def upload_file(content: bytes, filename: str) -> dict:
    vs_id = settings.resolved_vector_store_id
    if not vs_id:
        raise AssistantError("No vector store configured. Create one first.")
    client = await get_client()
    uploaded = await client.files.create(file=(filename, io.BytesIO(content), "text/plain"), purpose="assistants")
    vs_file = await client.vector_stores.files.create_and_poll(vector_store_id=vs_id, file_id=uploaded.id)
    logger.info("uploaded and indexed file=%s file_id=%s", filename, uploaded.id)
    return {"file_id": uploaded.id, "filename": filename, "status": vs_file.status}


# ── Delete single file ───────────────────────────────────────────────────────

async def delete_file(file_id: str) -> None:
    vs_id = settings.resolved_vector_store_id
    if not vs_id:
        raise AssistantError("No vector store configured.")
    client = await get_client()
    try:
        await client.vector_stores.files.delete(vector_store_id=vs_id, file_id=file_id)
    except Exception as e:
        raise AssistantError(f"Could not remove file from vector store: {e}") from e
    try:
        await client.files.delete(file_id)
    except Exception as e:
        logger.warning("could not delete file_id=%s from Files API: %s", file_id, e)


# ── Internal ─────────────────────────────────────────────────────────────────

async def _list_store_filenames(client, vs_id: str) -> set[str]:
    filenames: set[str] = set()
    files = await client.vector_stores.files.list(vector_store_id=vs_id)
    for f in files.data:
        try:
            obj = await client.files.retrieve(f.id)
            filenames.add(obj.filename)
        except Exception as e:
            logger.warning("could not retrieve filename for file_id=%s: %s", f.id, e)
    return filenames
