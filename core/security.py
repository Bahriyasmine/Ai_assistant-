from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from core.config import settings

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str = Security(_header)) -> None:
    """Dependency applied to all routers.
    If API_KEY is empty in .env → open access (dev/demo mode).
    If API_KEY is set → every request must carry X-API-Key: <key>.
    """
    if not settings.api_key:
        return
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it as X-API-Key header.",
        )
