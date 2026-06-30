import httpx
from openai import AsyncOpenAI

from core.config import settings
from core.exceptions import MissingAPIKeyError


async def get_client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise MissingAPIKeyError("OPENAI_API_KEY is not set in .env")
    # verify=False handles corporate SSL inspection certificates that Python
    # doesn't trust by default (Windows system cert store is not used by httpx).
    http_client = httpx.AsyncClient(verify=False)
    return AsyncOpenAI(api_key=settings.openai_api_key, http_client=http_client)
