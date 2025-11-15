"""知识库相关 API。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from qans_server.api.dependencies import (
    get_db_session,
    get_kb_service_dep,
)
from qans_server.db.mysql.models.knowledge_base import KnowledgeBase
from qans_server.service.knowledge_base_service import KnowledgeBaseService
from qans_server.util.file_util import delete_file


router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(
        ...,
        max_length=200,
        description="知识库名称，最长 200 个字符。",
    )
    description: Optional[str] = Field(
        None,
        description="知识库简介或用途说明。",
    )


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        max_length=200,
        description="新的知识库名称，未提供则保持不变。",
    )
    description: Optional[str] = Field(
        None,
        description="新的知识库描述，未提供则保持不变。",
    )


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    document_count: int
    total_size: int
    create_time: str
    update_time: str

    @classmethod
    def from_orm(cls, kb: KnowledgeBase) -> "KnowledgeBaseOut":  # pragma: no cover - simple mapping
        return cls(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=kb.document_count,
            total_size=kb.total_size,
            create_time=kb.create_time.isoformat(),
            update_time=kb.update_time.isoformat(),
        )


class PaginatedKnowledgeBase(BaseModel):
    total: int
    items: List[KnowledgeBaseOut]


@router.post(
    "",
    response_model=KnowledgeBaseOut,
    summary="创建知识库",
    description="新增一个知识库，可设置名称和描述信息。",
)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """创建新的知识库。

    参数:
        payload: 知识库创建请求体。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    kb = service.create(session, name=payload.name, description=payload.description)
    return KnowledgeBaseOut.from_orm(kb)


@router.get(
    "",
    response_model=PaginatedKnowledgeBase,
    summary="分页查询知识库",
    description="按页返回知识库列表，支持名称模糊搜索。",
)
def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(10, ge=1, le=100, description="每页返回的知识库数量，默认 10，最大 100。"),
    search: Optional[str] = Query(None, description="按名称模糊查询的关键字。"),
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """分页获取知识库列表。

    参数:
        page: 页码，从 1 开始。
        page_size: 每页返回的数量。
        search: 按名称模糊匹配的关键字。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    offset = (page - 1) * page_size
    items = service.list(session, limit=page_size, offset=offset, search=search)
    total_query = session.query(KnowledgeBase)
    if search:
        total_query = total_query.filter(KnowledgeBase.name.like(f"%{search}%"))
    total = total_query.count()
    return PaginatedKnowledgeBase(
        total=total,
        items=[KnowledgeBaseOut.from_orm(kb) for kb in items],
    )


@router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseOut,
    summary="获取知识库详情",
    description="根据知识库 ID 查询其详细信息。",
)
def get_knowledge_base_detail(
    kb_id: int = Path(..., description="目标知识库 ID。"),
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """获取指定知识库的详细信息。

    参数:
        kb_id: 目标知识库 ID。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    kb = service.get(session, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return KnowledgeBaseOut.from_orm(kb)


@router.put(
    "/{kb_id}",
    response_model=KnowledgeBaseOut,
    summary="更新知识库信息",
    description="根据知识库 ID 修改名称或描述。",
)
def update_knowledge_base(
    payload: KnowledgeBaseUpdate,
    kb_id: int = Path(..., description="需要更新的知识库 ID。"),
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """更新知识库的名称或描述。

    参数:
        kb_id: 目标知识库 ID。
        payload: 更新请求体。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    kb = service.update(session, kb_id, payload.name, payload.description)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return KnowledgeBaseOut.from_orm(kb)


@router.delete(
    "/{kb_id}",
    summary="删除知识库",
    description="删除指定知识库，并清理其关联文档及文件。",
)
def delete_knowledge_base(
    kb_id: int = Path(..., description="需要删除的知识库 ID。"),
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """删除指定知识库及其相关资源。

    参数:
        kb_id: 目标知识库 ID。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    kb = service.get(session, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    result = service.delete(session, kb_id)
    for path in result.get("deleted_file_paths", []):
        delete_file(path)

    return {"deleted": True, "deleted_documents": result.get("deleted_count", 0)}


@router.get(
    "/{kb_id}/stats",
    summary="获取知识库统计信息",
    description="返回指定知识库的文档数量、向量数量等统计指标。",
)
def get_knowledge_base_stats(
    kb_id: int = Path(..., description="目标知识库 ID。"),
    session: Session = Depends(get_db_session),
    service: KnowledgeBaseService = Depends(get_kb_service_dep),
):
    """查询指定知识库的统计信息。

    参数:
        kb_id: 目标知识库 ID。
        session: 数据库会话依赖。
        service: 知识库服务依赖。
    """
    kb = service.get(session, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return service.get_statistics(session, kb_id)


