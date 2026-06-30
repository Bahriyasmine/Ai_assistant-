"""
api/routes.py — combines all endpoint groups into a single router.

Endpoint groups
---------------
/chat           — conversational Q&A and suggested questions   (api/chat.py)
/vector-store   — vector store CRUD and file management        (api/vector_store.py)
"""

from fastapi import APIRouter

from . import chat, vector_store

router = APIRouter()
router.include_router(chat.router)
router.include_router(vector_store.router)
