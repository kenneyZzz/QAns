from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, Session
from qans_server.db.mysql import Base


class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "t_knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="知识库名称")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="知识库描述")
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="文档数量")
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="总大小（字节）")
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (
        Index("idx_name", "name"),
        Index("idx_create_time", "create_time"),
    )

    def __repr__(self) -> str:
        return (
            f"KnowledgeBase(id={self.id!r}, name={self.name!r}, "
            f"document_count={self.document_count!r}, total_size={self.total_size!r})"
        )

    @staticmethod
    def create_instance(name: str, description: str = None) -> "KnowledgeBase":
        """创建知识库实例"""
        return KnowledgeBase(
            name=name,
            description=description,
            document_count=0,
            total_size=0,
            create_time=datetime.now(),
            update_time=datetime.now()
        )


# CRUD操作函数
def create_knowledge_base(session: Session, name: str, description: str = None) -> KnowledgeBase:
    """创建知识库"""
    kb = KnowledgeBase.create_instance(name=name, description=description)
    session.add(kb)
    session.flush()
    return kb


def get_knowledge_base_by_id(session: Session, kb_id: int) -> KnowledgeBase | None:
    """根据ID查询知识库"""
    return session.get(KnowledgeBase, kb_id)


def list_knowledge_bases(
    session: Session, 
    limit: int = 100, 
    offset: int = 0, 
    search: str = None
) -> list[KnowledgeBase]:
    """查询知识库列表，支持搜索"""
    query = session.query(KnowledgeBase)
    
    if search:
        query = query.filter(KnowledgeBase.name.like(f"%{search}%"))
    
    return (
        query
        .order_by(KnowledgeBase.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_knowledge_base(
    session: Session, 
    kb_id: int, 
    name: str = None, 
    description: str = None
) -> KnowledgeBase | None:
    """更新知识库"""
    kb = session.get(KnowledgeBase, kb_id)
    if not kb:
        return None
    
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    
    kb.update_time = datetime.now()
    session.flush()
    return kb


def delete_knowledge_base(session: Session, kb_id: int) -> bool:
    """删除知识库（级联删除文档）"""
    kb = session.get(KnowledgeBase, kb_id)
    if kb:
        session.delete(kb)
        return True
    return False


def increment_document_count(session: Session, kb_id: int, count: int = 1) -> None:
    """增加文档数量"""
    kb = session.get(KnowledgeBase, kb_id)
    if kb:
        kb.document_count += count
        kb.update_time = datetime.now()
        session.flush()


def update_total_size(session: Session, kb_id: int, size_delta: int) -> None:
    """更新总大小（增加或减少）"""
    kb = session.get(KnowledgeBase, kb_id)
    if kb:
        kb.total_size += size_delta
        if kb.total_size < 0:
            kb.total_size = 0
        kb.update_time = datetime.now()
        session.flush()

