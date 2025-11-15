"""知识库业务逻辑。"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from qans_server.db.mysql.models.document import Document
from qans_server.db.mysql.models.document import (
    delete_document,
    list_documents,
)
from qans_server.db.mysql.models.knowledge_base import (
    KnowledgeBase,
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base_by_id,
    list_knowledge_bases,
    update_knowledge_base,
)
from qans_server.db.vector.collections.doc_chunk import VectorDocChunk


class KnowledgeBaseService:
    """知识库服务。"""

    def __init__(self, vector_repo: VectorDocChunk | None = None) -> None:
        self._vector_repo = vector_repo or VectorDocChunk()

    # ------------------------------------------------------------------
    # 基础操作
    # ------------------------------------------------------------------
    def create(self, session: Session, name: str, description: str | None = None) -> KnowledgeBase:
        return create_knowledge_base(session, name=name, description=description)

    def update(
        self,
        session: Session,
        kb_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> KnowledgeBase | None:
        return update_knowledge_base(session, kb_id=kb_id, name=name, description=description)

    def get(self, session: Session, kb_id: int) -> KnowledgeBase | None:
        return get_knowledge_base_by_id(session, kb_id)

    def list(
        self,
        session: Session,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
    ) -> List[KnowledgeBase]:
        return list_knowledge_bases(session, limit=limit, offset=offset, search=search)

    # ------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------
    def get_statistics(self, session: Session, kb_id: int) -> dict:
        """获取知识库统计信息。"""

        # 文档数量
        doc_count = session.execute(
            select(func.count()).select_from(
                select(Document.id)
                .where(Document.knowledge_base_id == kb_id)
                .subquery()
            )
        ).scalar_one()

        # 文档总大小
        total_size = session.execute(
            select(func.coalesce(func.sum(Document.file_size), 0)).where(
                Document.knowledge_base_id == kb_id
            )
        ).scalar_one()

        # 向量分块数量
        chunk_count = self._vector_repo.count_by_knowledge_base_id(kb_id)

        return {
            "knowledge_base_id": kb_id,
            "document_count": doc_count,
            "total_size": total_size,
            "chunk_count": chunk_count,
        }

    # ------------------------------------------------------------------
    # 删除逻辑
    # ------------------------------------------------------------------
    def delete(self, session: Session, kb_id: int) -> dict:
        """删除知识库，返回已删除文档的文件路径列表供上层清理。"""

        # 查询待删除的文档路径
        documents = list_documents(session, knowledge_base_id=kb_id, limit=10_000)
        file_paths = [doc.file_path for doc in documents]

        # 删除向量数据
        self._vector_repo.delete_documents_by_knowledge_base_id(kb_id)

        # 删除文档记录（依赖外键级联也可以）
        for doc in documents:
            delete_document(session, doc.id)

        # 删除知识库记录
        delete_knowledge_base(session, kb_id)

        return {"deleted_file_paths": file_paths, "deleted_count": len(documents)}


