"""聊天相关 API。"""

from __future__ import annotations

import json
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from qans_server.api.dependencies import (
    get_chat_service_dep,
    get_db_session,
)
from qans_server.db.mysql.models.chat_message import ChatMessage
from qans_server.db.mysql.models.chat_session import ChatSession
from qans_server.service.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["聊天"])


class ChatSessionCreate(BaseModel):
    knowledge_base_ids: List[int] = Field(
        ...,
        min_items=1,
        description="关联的知识库 ID 列表，至少包含一个知识库。",
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="会话标题，若不填写则由系统自动生成。",
    )


class ChatSessionUpdate(BaseModel):
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="更新后的知识库 ID 列表，不传则保持原值。",
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="更新后的会话标题，不传则保持原值。",
    )


class ChatSessionOut(BaseModel):
    id: int
    title: Optional[str]
    knowledge_base_ids: List[int]
    message_count: int
    create_time: str
    update_time: str

    @classmethod
    def from_orm(cls, session: ChatSession) -> "ChatSessionOut":
        return cls(
            id=session.id,
            title=session.title,
            knowledge_base_ids=session.knowledge_base_ids or [],
            message_count=session.message_count,
            create_time=session.create_time.isoformat(),
            update_time=session.update_time.isoformat(),
        )


class PaginatedChatSessions(BaseModel):
    total: int
    items: List[ChatSessionOut]


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list]
    create_time: str

    @classmethod
    def from_orm(cls, message: ChatMessage) -> "ChatMessageOut":
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=message.sources,
            create_time=message.create_time.isoformat(),
        )


class ChatMessageRequest(BaseModel):
    session_id: int = Field(..., description="目标聊天会话 ID。")
    query: str = Field(..., description="用户输入的问题或消息内容。")
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="临时指定的知识库 ID 列表，未提供时沿用会话默认配置。",
    )
    top_k: int = Field(
        5,
        ge=1,
        description="召回知识片段的数量上限，默认 5。",
    )
    score_threshold: float = Field(
        0.7,
        ge=0,
        le=1,
        description="相似度阈值，低于该阈值的片段将被过滤，默认 0.7。",
    )


@router.post(
    "/sessions",
    response_model=ChatSessionOut,
    summary="创建新的聊天会话",
    description="根据指定的知识库创建一个新的聊天会话，可选地设置会话标题。",
)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """创建一个新的聊天会话。

    参数:
        payload: 会话创建请求体，包含知识库 ID 列表及可选的标题。
        db: 数据库会话依赖，用于持久化操作。
        service: 聊天服务依赖，负责业务逻辑。
    """
    chat_session = service.create_session(
        db,
        knowledge_base_ids=payload.knowledge_base_ids,
        title=payload.title,
    )
    return ChatSessionOut.from_orm(chat_session)


@router.get(
    "/sessions",
    response_model=PaginatedChatSessions,
    summary="分页查询聊天会话",
    description="按页返回当前用户创建的聊天会话列表，可指定分页大小。",
)
def list_sessions(
    page: int = Query(1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数，默认 10，最大 100。"),
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """分页查询聊天会话列表。

    参数:
        page: 页码，从 1 开始。
        page_size: 每页返回的会话条数。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
    """
    offset = (page - 1) * page_size
    sessions = service.list_sessions(db, limit=page_size, offset=offset)
    total = db.query(ChatSession).count()
    return PaginatedChatSessions(
        total=total,
        items=[ChatSessionOut.from_orm(item) for item in sessions],
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionOut,
    summary="获取聊天会话详情",
    description="根据会话 ID 返回会话的基础信息及统计数据。",
)
def get_session_detail(
    session_id: int = Path(..., description="聊天会话的唯一标识。"),
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """获取指定聊天会话的详细信息。

    参数:
        session_id: 目标聊天会话的 ID。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
    """
    chat_session = service.get_session(db, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatSessionOut.from_orm(chat_session)


@router.put(
    "/sessions/{session_id}",
    response_model=ChatSessionOut,
    summary="更新聊天会话信息",
    description="根据会话 ID 修改会话标题或关联的知识库集合。",
)
def update_session(
    payload: ChatSessionUpdate,
    session_id: int = Path(..., description="需要更新的聊天会话 ID。"),
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """更新聊天会话的标题或关联知识库。

    参数:
        session_id: 目标聊天会话的 ID。
        payload: 包含更新内容的请求体。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
    """
    chat_session = service.get_session(db, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if payload.title is not None:
        chat_session = service.update_session_title(db, session_id, payload.title)
    if payload.knowledge_base_ids is not None:
        chat_session = service.update_session_knowledge_bases(db, session_id, payload.knowledge_base_ids)

    return ChatSessionOut.from_orm(chat_session)


@router.delete(
    "/sessions/{session_id}",
    summary="删除聊天会话",
    description="根据会话 ID 删除指定的聊天会话及其关联的消息。",
)
def delete_session(
    session_id: int = Path(..., description="需要删除的聊天会话 ID。"),
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """删除指定的聊天会话。

    参数:
        session_id: 目标聊天会话的 ID。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
    """
    chat_session = service.get_session(db, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在")
    service.delete_session(db, session_id)
    return {"deleted": True}


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageOut],
    summary="列出会话消息记录",
    description="获取指定会话下的历史消息记录，可限制返回数量。",
)
def list_session_messages(
    session_id: int = Path(..., description="目标聊天会话 ID。"),
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=200,
        description="限制返回的消息数量，未提供则返回全部消息。",
    ),
):
    """查询指定会话的消息列表。

    参数:
        session_id: 目标聊天会话的 ID。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
        limit: 限制返回的消息数量。
    """
    chat_session = service.get_session(db, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = service.list_messages(db, session_id, limit=limit)
    return [ChatMessageOut.from_orm(msg) for msg in messages]

@router.post(
    "/messages/stream",
    summary="发送消息并流式获取回复",
    description="以流式 SSE 的形式返回模型回复，可用于前端实时展示生成内容。",
)
def stream_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db_session),
    service: ChatService = Depends(get_chat_service_dep),
):
    """发送消息并以流式形式返回回复内容。
    参数:
        payload: 消息请求体，包含会话 ID、问题内容及召回参数。
        db: 数据库会话依赖。
        service: 聊天服务依赖。
    """
    generator, sources = service.stream_message(
        db,
        session_id=payload.session_id,
        query=payload.query,
        knowledge_base_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
    )

    def event_stream() -> Generator[str, None, None]:
        for chunk in generator:
            if chunk:
                data = {"type": "chunk", "content": chunk}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        data = {"type": "done", "sources": sources}
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


