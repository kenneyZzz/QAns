from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Index, JSON, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship
from sqlalchemy import types
import json
from qans_server.db.mysql import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chat_message import ChatMessage


class JSONType(TypeDecorator):
    """JSON类型装饰器，用于存储JSON数据"""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class ChatSession(Base):
    """聊天会话模型"""
    __tablename__ = "t_chat_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    title: Mapped[str] = mapped_column(String(200), nullable=True, comment="会话标题")
    knowledge_base_ids: Mapped[list] = mapped_column(
        JSONType, nullable=True, comment="选中的知识库ID列表（JSON格式）"
    )
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="消息数量")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    __table_args__ = (
        Index("idx_create_time", "create_time"),
    )

    def __repr__(self) -> str:
        return (
            f"ChatSession(id={self.id!r}, title={self.title!r}, "
            f"knowledge_base_ids={self.knowledge_base_ids!r}, message_count={self.message_count!r})"
        )

    @staticmethod
    def create_instance(knowledge_base_ids: list[int], title: str = None) -> "ChatSession":
        """创建会话实例"""
        return ChatSession(
            title=title,
            knowledge_base_ids=knowledge_base_ids if knowledge_base_ids else [],
            message_count=0,
            create_time=datetime.now(),
            update_time=datetime.now()
        )


# CRUD操作函数
def create_chat_session(
    session: Session,
    knowledge_base_ids: list[int],
    title: str = None
) -> ChatSession:
    """创建聊天会话"""
    chat_session = ChatSession.create_instance(
        knowledge_base_ids=knowledge_base_ids,
        title=title
    )
    session.add(chat_session)
    session.flush()
    return chat_session


def get_chat_session_by_id(session: Session, session_id: int) -> ChatSession | None:
    """根据ID查询会话"""
    return session.get(ChatSession, session_id)


def list_chat_sessions(
    session: Session,
    limit: int = 100,
    offset: int = 0
) -> list[ChatSession]:
    """查询会话列表，按更新时间倒序"""
    return (
        session.query(ChatSession)
        .order_by(ChatSession.update_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_chat_session_title(session: Session, session_id: int, title: str) -> ChatSession | None:
    """更新会话标题"""
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        return None
    
    chat_session.title = title
    chat_session.update_time = datetime.now()
    session.flush()
    return chat_session


def update_chat_session_kbs(
    session: Session,
    session_id: int,
    knowledge_base_ids: list[int]
) -> ChatSession | None:
    """更新知识库列表"""
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        return None
    
    chat_session.knowledge_base_ids = knowledge_base_ids if knowledge_base_ids else []
    chat_session.update_time = datetime.now()
    session.flush()
    return chat_session


def increment_message_count(session: Session, session_id: int, count: int = 1) -> None:
    """增加消息数量"""
    chat_session = session.get(ChatSession, session_id)
    if chat_session:
        chat_session.message_count += count
        chat_session.update_time = datetime.now()
        session.flush()


def delete_chat_session(session: Session, session_id: int) -> bool:
    """删除会话（级联删除消息）"""
    chat_session = session.get(ChatSession, session_id)
    if chat_session:
        session.delete(chat_session)
        return True
    return False

