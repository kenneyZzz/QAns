from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from qans_server.db.mysql import Base


class DocumentChunk(Base):
    """文档分块表"""

    __tablename__ = "t_document_chunk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("t_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID",
    )
    knowledge_base_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="知识库ID")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="分块序号")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="分块内容")
    metadata_json: Mapped[str] = mapped_column(
        "metadata",
        Text,
        nullable=True,
        comment="原始元数据(JSON)",
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    document = relationship("Document", back_populates="chunks")


@dataclass(slots=True)
class DocumentChunkCreate:
    knowledge_base_id: int
    chunk_index: int
    content: str
    metadata_json: str | None


def replace_document_chunks(
    session: Session,
    document_id: int,
    chunks: Iterable[DocumentChunkCreate],
) -> int:
    """替换指定文档的分块记录。"""
    session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

    items: List[DocumentChunk] = []
    for chunk in chunks:
        items.append(
            DocumentChunk(
                document_id=document_id,
                knowledge_base_id=chunk.knowledge_base_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata_json=chunk.metadata_json,
            )
        )

    if items:
        session.add_all(items)
    session.flush()
    return len(items)


def list_document_chunks(session: Session, document_id: int) -> list[DocumentChunk]:
    """获取文档的分块记录。"""
    return (
        session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

