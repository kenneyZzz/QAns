"""文档业务逻辑。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from langchain_core.documents import Document as LangDocument
from loguru import logger
from sqlalchemy.orm import Session

from qans_server.setting_config import Settings, get_settings
from qans_server.db.mysql.models.document import (
    DOCUMENT_STATUS_CHUNKED,
    DOCUMENT_STATUS_PROCESSING,
    DOCUMENT_STATUS_COMPLETED,
    DOCUMENT_STATUS_UPLOADED,
    DOCUMENT_STATUS_FAILED,
    create_document,
    delete_document,
    get_document_by_id,
    list_documents,
    update_document_chunk_count,
    update_document_status,
    Document,
)
from qans_server.db.mysql.models.document_chunk import (
    DocumentChunkCreate,
    list_document_chunks,
    replace_document_chunks,
)
from qans_server.db.mysql.models.knowledge_base import (
    increment_document_count,
    update_total_size,
)
from qans_server.db.vector.collections.doc_chunk import VectorDocChunk
from qans_server.loader.document_loader import DocumentLoader
from qans_server.loader.text_splitter import DocumentTextSplitter
from qans_server.service.embedding_service import EmbeddingService
from qans_server.util.file_util import (
    delete_file,
    get_file_extension,
    get_file_size,
    save_upload_file,
    validate_file_size,
    validate_file_type,
)


class DocumentService:
    """处理文档上传、解析、向量化等业务。"""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        vector_repo: VectorDocChunk | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_repo = vector_repo or VectorDocChunk()
        self.loader = DocumentLoader()
        self.splitter = DocumentTextSplitter()

        self.allowed_types = {
            ext.lstrip(".")
            for ext in self.loader.get_supported_formats()
        }

    # ------------------------------------------------------------------
    # 文档上传与处理
    # ------------------------------------------------------------------
    def upload_document(self, session: Session, knowledge_base_id: int, file: UploadFile) -> int:
        """上传文档，仅保存文件记录，返回文档 ID。"""

        validate_file_type(file.filename or "", self.allowed_types)

        temp_path = save_upload_file(self._resolve_upload_dir(knowledge_base_id), file)
        file_size = get_file_size(temp_path)
        try:
            validate_file_size(file_size, self.settings.max_file_size)
        except Exception:
            delete_file(temp_path)
            raise

        document = create_document(
            session,
            knowledge_base_id=knowledge_base_id,
            file_name=temp_path.name,
            file_path=str(temp_path),
            file_size=file_size,
            file_type=get_file_extension(temp_path.name),
        )

        increment_document_count(session, knowledge_base_id, 1)
        update_total_size(session, knowledge_base_id, file_size)
        update_document_status(session, document.id, DOCUMENT_STATUS_UPLOADED)

        return document.id

    def chunk_document(
        self,
        session: Session,
        document_id: int,
        chunk_options: Optional[dict] = None,
    ) -> int:
        """执行文档分块，并将结果写入分块表。"""

        document = get_document_by_id(session, document_id)
        if not document:
            raise ValueError("文档不存在")

        file_path = Path(document.file_path)
        if not file_path.exists():
            update_document_status(session, document_id, DOCUMENT_STATUS_FAILED, "文件不存在")
            raise FileNotFoundError(f"文档文件不存在: {file_path}")

        update_document_status(session, document_id, DOCUMENT_STATUS_PROCESSING)

        try:
            raw_documents = self.loader.load_document(str(file_path))
            split_docs = self.splitter.split_documents(
                raw_documents,
                overrides=chunk_options,
            )
        except Exception as exc:  # noqa: BLE001
            update_document_status(session, document_id, DOCUMENT_STATUS_FAILED, str(exc))
            raise

        chunks_to_save: list[DocumentChunkCreate] = []
        for idx, chunk in enumerate(split_docs):
            metadata = dict(chunk.metadata or {})
            metadata["doc_id"] = document.id
            metadata["knowledge_base_id"] = document.knowledge_base_id

            chunks_to_save.append(
                DocumentChunkCreate(
                    knowledge_base_id=document.knowledge_base_id,
                    chunk_index=metadata.get("chunk_index", idx),
                    content=chunk.page_content or "",
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
            )

        replace_document_chunks(session, document_id, chunks_to_save)
        update_document_chunk_count(session, document_id, len(split_docs))
        update_document_status(session, document_id, DOCUMENT_STATUS_CHUNKED)

        return len(split_docs)

    def get_document_chunks(self, session: Session, document_id: int):
        """获取文档分块详情。"""
        return list_document_chunks(session, document_id)

    def vectorize_document(self, session: Session, document_id: int) -> int:
        """根据已保存的分块执行向量化，并写入向量库。"""

        document = get_document_by_id(session, document_id)
        if not document:
            raise ValueError("文档不存在")

        chunks = list_document_chunks(session, document_id)
        if not chunks:
            raise ValueError("未找到分块记录，请先执行分块")

        update_document_status(session, document_id, DOCUMENT_STATUS_PROCESSING)

        try:
            langchain_docs: list[LangDocument] = []
            for chunk in chunks:
                metadata = {}
                if chunk.metadata_json:
                    try:
                        metadata = json.loads(chunk.metadata_json)
                    except json.JSONDecodeError:
                        metadata = {"raw": chunk.metadata_json}

                metadata.setdefault("doc_id", document.id)
                metadata.setdefault("knowledge_base_id", document.knowledge_base_id)
                metadata.setdefault("chunk_index", chunk.chunk_index)

                langchain_docs.append(
                    LangDocument(
                        page_content=chunk.content,
                        metadata=metadata,
                    )
                )

            vectors = self.embedding_service.embed_documents(langchain_docs)

            # 重新向量化前先清理旧向量
            self.vector_repo.delete_documents_by_doc_id(document_id)
            inserted = self.vector_repo.insert_documents(
                documents=langchain_docs,
                vectors=vectors,
                doc_id=document.id,
                knowledge_base_id=document.knowledge_base_id,
            )

            update_document_status(session, document_id, DOCUMENT_STATUS_COMPLETED)
            return inserted
        except Exception as exc:  # noqa: BLE001
            logger.error(exc)
            update_document_status(session, document_id, DOCUMENT_STATUS_FAILED, str(exc))
            raise

    # ------------------------------------------------------------------
    # 查询与删除
    # ------------------------------------------------------------------
    def list_documents(
        self,
        session: Session,
        *,
        knowledge_base_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ):
        return list_documents(
            session,
            knowledge_base_id=knowledge_base_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    def delete_document(self, session: Session, document_id: int) -> bool:
        """删除文档及其向量数据，并回收统计信息。"""

        doc = get_document_by_id(session, document_id)
        if not doc:
            return False

        knowledge_base_id = doc.knowledge_base_id
        file_path = Path(doc.file_path)
        file_size = doc.file_size

        self.vector_repo.delete_documents_by_doc_id(document_id)
        delete_document(session, document_id)

        increment_document_count(session, knowledge_base_id, -1)
        update_total_size(session, knowledge_base_id, -file_size)

        delete_file(file_path)
        return True

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def get_chunk_type_configs(self) -> dict:
        """返回所有类型的分块默认配置。"""
        return self.splitter.get_all_type_configs()

    def get_default_chunk_config(self) -> dict:
        """返回默认的分块配置。"""
        return self.splitter.get_default_config()

    def _resolve_upload_dir(self, knowledge_base_id: int) -> Path:
        return self.settings.upload_dir / str(knowledge_base_id)


