from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship
from qans_server.db.mysql import Base


class Document(Base):
    """文档模型"""
    __tablename__ = "t_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("t_knowledge_base.id", ondelete="CASCADE"), 
        nullable=False, 
        comment="所属知识库ID"
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小（字节）")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="文件类型（扩展名）")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分块数量")
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        comment="状态：uploaded/processing/chunked/completed/failed"
    )
    error_message: Mapped[str] = mapped_column(String(1000), nullable=True, comment="错误信息")
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 关系定义（可选，用于ORM查询）
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", backref="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_kb_id", "knowledge_base_id"),
        Index("idx_status", "status"),
        Index("idx_create_time", "create_time"),
    )

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id!r}, knowledge_base_id={self.knowledge_base_id!r}, "
            f"file_name={self.file_name!r}, status={self.status!r}, chunk_count={self.chunk_count!r})"
        )

    @staticmethod
    def create_instance(
        knowledge_base_id: int,
        file_name: str,
        file_path: str,
        file_size: int,
        file_type: str
    ) -> "Document":
        """创建文档实例"""
        return Document(
            knowledge_base_id=knowledge_base_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            chunk_count=0,
            status="uploaded",
            error_message=None,
            create_time=datetime.now(),
            update_time=datetime.now()
        )


# 状态常量
DOCUMENT_STATUS_UPLOADED = "uploaded"
DOCUMENT_STATUS_PROCESSING = "processing"
DOCUMENT_STATUS_CHUNKED = "chunked"
DOCUMENT_STATUS_COMPLETED = "completed"
DOCUMENT_STATUS_FAILED = "failed"


# CRUD操作函数
def create_document(
    session: Session,
    knowledge_base_id: int,
    file_name: str,
    file_path: str,
    file_size: int,
    file_type: str
) -> Document:
    """创建文档记录"""
    doc = Document.create_instance(
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type
    )
    session.add(doc)
    session.flush()
    return doc


def get_document_by_id(session: Session, doc_id: int) -> Document | None:
    """根据ID查询文档"""
    return session.get(Document, doc_id)


def list_documents(
    session: Session,
    knowledge_base_id: int = None,
    limit: int = 100,
    offset: int = 0,
    status: str = None
) -> list[Document]:
    """查询文档列表，支持知识库过滤和状态过滤"""
    query = session.query(Document)
    
    if knowledge_base_id is not None:
        query = query.filter(Document.knowledge_base_id == knowledge_base_id)
    
    if status:
        query = query.filter(Document.status == status)
    
    return (
        query
        .order_by(Document.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_document_status(
    session: Session,
    doc_id: int,
    status: str,
    error_message: str = None
) -> Document | None:
    """更新文档处理状态"""
    doc = session.get(Document, doc_id)
    if not doc:
        return None
    
    doc.status = status
    if error_message is not None:
        doc.error_message = error_message
    doc.update_time = datetime.now()
    session.flush()
    return doc


def update_document_chunk_count(session: Session, doc_id: int, chunk_count: int) -> Document | None:
    """更新文档分块数量"""
    doc = session.get(Document, doc_id)
    if not doc:
        return None
    
    doc.chunk_count = chunk_count
    doc.update_time = datetime.now()
    session.flush()
    return doc


def delete_document(session: Session, doc_id: int) -> bool:
    """删除文档记录"""
    doc = session.get(Document, doc_id)
    if doc:
        session.delete(doc)
        return True
    return False

