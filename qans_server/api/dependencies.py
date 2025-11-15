"""FastAPI 依赖项。"""

from __future__ import annotations

from functools import lru_cache
from typing import Generator
from qans_server.setting_config import Settings, get_settings
from qans_server.db.mysql.base import get_session
from qans_server.service.chat_service import ChatService
from qans_server.service.document_service import DocumentService
from qans_server.service.embedding_service import EmbeddingService
from qans_server.service.knowledge_base_service import KnowledgeBaseService


def get_db_session() -> Generator:
    """获取数据库会话。"""

    with get_session() as session:
        yield session


@lru_cache()
def _get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache()
def _get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


@lru_cache()
def _get_document_service() -> DocumentService:
    settings = get_settings()
    return DocumentService(settings=settings, embedding_service=_get_embedding_service())


@lru_cache()
def _get_chat_service() -> ChatService:
    return ChatService(embedding_service=_get_embedding_service())


def get_settings_dep() -> Settings:
    return get_settings()


def get_kb_service_dep() -> KnowledgeBaseService:
    return _get_kb_service()


def get_document_service_dep() -> DocumentService:
    return _get_document_service()


def get_chat_service_dep() -> ChatService:
    return _get_chat_service()


