"""API 路由聚合。"""

from fastapi import APIRouter

from qans_server.api import chat, document, knowledge_base

api_router = APIRouter()
api_router.include_router(knowledge_base.router)
api_router.include_router(document.router)
api_router.include_router(chat.router)


__all__ = ["api_router"]


