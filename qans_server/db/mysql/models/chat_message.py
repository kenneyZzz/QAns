from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Index, JSON, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship
from sqlalchemy import types
import json
from qans_server.db.mysql import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chat_session import ChatSession


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


class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "t_chat_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("t_chat_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话ID"
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色：user/assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    sources: Mapped[list] = mapped_column(
        JSONType, nullable=True, comment="引用来源（JSON格式，仅assistant消息）"
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 关系定义（可选，用于ORM查询）
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("idx_session_id", "session_id"),
        Index("idx_create_time", "create_time"),
    )

    def __repr__(self) -> str:
        return (
            f"ChatMessage(id={self.id!r}, session_id={self.session_id!r}, "
            f"role={self.role!r}, content_length={len(self.content) if self.content else 0})"
        )

    @staticmethod
    def create_instance(
        session_id: int,
        role: str,
        content: str,
        sources: list[dict] = None
    ) -> "ChatMessage":
        """创建消息实例"""
        return ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
            create_time=datetime.now()
        )


# 角色常量
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"


# CRUD操作函数
def create_chat_message(
    session: Session,
    session_id: int,
    role: str,
    content: str,
    sources: list[dict] = None
) -> ChatMessage:
    """创建聊天消息"""
    message = ChatMessage.create_instance(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources
    )
    session.add(message)
    session.flush()
    return message


def get_chat_message_by_id(session: Session, message_id: int) -> ChatMessage | None:
    """根据ID查询消息"""
    return session.get(ChatMessage, message_id)


def list_chat_messages(
    session: Session,
    session_id: int,
    limit: int = None
) -> list[ChatMessage]:
    """获取会话的所有消息，按时间正序"""
    query = session.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.create_time.asc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def delete_chat_message(session: Session, message_id: int) -> bool:
    """删除消息"""
    message = session.get(ChatMessage, message_id)
    if message:
        session.delete(message)
        return True
    return False


def delete_chat_messages_by_session(session: Session, session_id: int) -> int:
    """删除会话的所有消息，返回删除数量"""
    deleted_count = (
        session.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .delete()
    )
    return deleted_count

