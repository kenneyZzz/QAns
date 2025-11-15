"""文档相关 API。"""

from __future__ import annotations

import json
from pathlib import Path as PathLib
from typing import Dict, List, Optional

from fastapi import File, APIRouter, Depends, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from qans_server.api.dependencies import get_db_session, get_document_service_dep
from qans_server.db.mysql.models.document import (
    DOCUMENT_STATUS_CHUNKED,
    DOCUMENT_STATUS_COMPLETED,
    Document,
    get_document_by_id,
)
from qans_server.service.document_service import DocumentService


router = APIRouter(prefix="/documents", tags=["文档"])


class DocumentOut(BaseModel):
    id: int
    knowledge_base_id: int
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    chunk_count: int
    status: str
    error_message: Optional[str]
    create_time: str
    update_time: str

    @classmethod
    def from_orm(cls, doc: Document) -> "DocumentOut":
        return cls(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            file_name=doc.file_name,
            file_path=doc.file_path,
            file_size=doc.file_size,
            file_type=doc.file_type,
            chunk_count=doc.chunk_count,
            status=doc.status,
            error_message=doc.error_message,
            create_time=doc.create_time.isoformat(),
            update_time=doc.update_time.isoformat(),
        )


class DocumentChunkOut(BaseModel):
    id: int
    document_id: int
    knowledge_base_id: int
    chunk_index: int
    content: str
    metadata: Optional[dict]
    create_time: str

    @classmethod
    def from_orm(cls, chunk) -> "DocumentChunkOut":
        metadata = None
        if getattr(chunk, "metadata_json", None):
            try:
                metadata = json.loads(chunk.metadata_json)
            except json.JSONDecodeError:
                metadata = {"raw": chunk.metadata_json}

        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            knowledge_base_id=chunk.knowledge_base_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            metadata=metadata,
            create_time=chunk.create_time.isoformat(),
        )


class PaginatedDocument(BaseModel):
    total: int
    items: List[DocumentOut]


class ChunkParameters(BaseModel):
    chunk_size: Optional[int] = Field(
        None,
        ge=1,
        description="切分单元的最大字符数，未传则使用默认配置。",
    )
    chunk_overlap: Optional[int] = Field(
        None,
        ge=0,
        description="相邻切分单元的重叠字符数，未传则使用默认配置。",
    )
    separators: Optional[List[str]] = Field(
        None,
        description="自定义切分分隔符列表，按顺序尝试匹配。",
    )


class ChunkConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int
    separators: Optional[List[str]] = None


class ChunkConfigResponse(BaseModel):
    default: ChunkConfig
    type_configs: Dict[str, ChunkConfig]


@router.post(
    "/upload",
    summary="上传文档到知识库",
    description="上传一个文件到指定知识库，文件将进入后续切分与向量化流程。",
)
def upload_document(
    knowledge_base_id: int = Form(..., ge=1, description="目标知识库 ID。"),
    file: UploadFile = File(..., description="待上传的原始文件。"),
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """上传文档到指定的知识库。

    参数:
        knowledge_base_id: 目标知识库的 ID。
        file: 待上传的文档文件。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    document_id = service.upload_document(session, knowledge_base_id=knowledge_base_id, file=file)
    return {"document_id": document_id, "status": "uploaded"}


@router.post(
    "/{document_id}/chunk",
    summary="触发文档切分",
    description="对指定文档执行文本切分，可自定义切分参数。",
)
def chunk_document_endpoint(
    document_id: int = Path(..., description="需要切分的文档 ID。"),
    params: Optional[ChunkParameters] = None,
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """触发文档切分流程。

    参数:
        document_id: 目标文档 ID。
        params: 可选的切分配置，未传则使用默认值。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    try:
        chunk_options = None
        if params is not None:
            chunk_options = params.dict(exclude_unset=True, exclude_none=True)
            if not chunk_options:
                chunk_options = None
        chunk_count = service.chunk_document(session, document_id, chunk_options=chunk_options)
    except ValueError:
        raise HTTPException(status_code=404, detail="文档不存在")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "document_id": document_id,
        "chunk_count": chunk_count,
        "status": DOCUMENT_STATUS_CHUNKED,
    }


@router.post(
    "/{document_id}/vectorize",
    summary="执行文档向量化",
    description="将已切分的文档转换为向量表示，写入向量存储。",
)
def vectorize_document_endpoint(
    document_id: int = Path(..., description="需要向量化的文档 ID。"),
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """执行文档的向量化流程。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    try:
        vector_count = service.vectorize_document(session, document_id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "文档不存在":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "document_id": document_id,
        "vector_count": vector_count,
        "status": DOCUMENT_STATUS_COMPLETED,
    }


@router.get(
    "",
    response_model=PaginatedDocument,
    summary="分页查询文档列表",
    description="按页返回知识库中的文档，可根据知识库或状态进行过滤。",
)
def list_documents(
    page: int = Query(1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(10, ge=1, le=100, description="每页返回的文档数量，默认 10，最大 100。"),
    knowledge_base_id: Optional[int] = Query(None, ge=1, description="按知识库 ID 过滤文档。"),
    status: Optional[str] = Query(None, description="按文档处理状态过滤。"),
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """分页查询文档列表。

    参数:
        page: 页码，从 1 开始。
        page_size: 每页返回的数量。
        knowledge_base_id: 可选的知识库 ID 过滤条件。
        status: 可选的文档状态过滤条件。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    offset = (page - 1) * page_size
    docs = service.list_documents(
        session,
        knowledge_base_id=knowledge_base_id,
        limit=page_size,
        offset=offset,
        status=status,
    )

    query = session.query(Document)
    if knowledge_base_id is not None:
        query = query.filter(Document.knowledge_base_id == knowledge_base_id)
    if status:
        query = query.filter(Document.status == status)
    total = query.count()

    return PaginatedDocument(
        total=total,
        items=[DocumentOut.from_orm(doc) for doc in docs],
    )


@router.get(
    "/chunk/configs",
    response_model=ChunkConfigResponse,
    summary="获取文档切分配置",
    description="返回默认切分配置及不同文件类型的专属配置。",
)
def get_chunk_configs(
    service: DocumentService = Depends(get_document_service_dep),
):
    """获取文档切分配置详情。

    参数:
        service: 文档服务依赖。
    """
    default_cfg = service.get_default_chunk_config()
    type_cfgs = service.get_chunk_type_configs()
    return ChunkConfigResponse(
        default=ChunkConfig(**default_cfg),
        type_configs={key: ChunkConfig(**cfg) for key, cfg in type_cfgs.items()},
    )


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="获取文档详情",
    description="根据文档 ID 返回文档的基础信息与处理状态。",
)
def get_document_detail(
    document_id: int = Path(..., description="目标文档 ID。"),
    session: Session = Depends(get_db_session),
):
    """获取指定文档的详细信息。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
    """
    doc = get_document_by_id(session, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentOut.from_orm(doc)


@router.delete(
    "/{document_id}",
    summary="删除文档",
    description="删除指定文档及其关联的切分结果与向量数据。",
)
def delete_document_endpoint(
    document_id: int = Path(..., description="需要删除的文档 ID。"),
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """删除指定文档及其资源。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    deleted = service.delete_document(session, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"deleted": True}


@router.get(
    "/{document_id}/status",
    summary="查询文档处理状态",
    description="返回指定文档的处理状态、切分数量及错误信息。",
)
def get_document_status(
    document_id: int = Path(..., description="需要查询的文档 ID。"),
    session: Session = Depends(get_db_session),
):
    """查询文档的处理状态信息。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
    """
    doc = get_document_by_id(session, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error_message": doc.error_message,
    }


@router.get(
    "/{document_id}/chunks",
    response_model=List[DocumentChunkOut],
    summary="获取文档切分结果",
    description="返回指定文档的全部切片内容及元数据。",
)
def list_document_chunks_endpoint(
    document_id: int = Path(..., description="目标文档 ID。"),
    session: Session = Depends(get_db_session),
    service: DocumentService = Depends(get_document_service_dep),
):
    """查询文档切分后的片段列表。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
        service: 文档服务依赖。
    """
    doc = get_document_by_id(session, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunks = service.get_document_chunks(session, document_id)
    return [DocumentChunkOut.from_orm(chunk) for chunk in chunks]


@router.get(
    "/{document_id}/download",
    summary="下载原始文档",
    description="下载指定文档的原始文件内容。",
)
def download_document_endpoint(
    document_id: int = Path(..., description="需要下载的文档 ID。"),
    session: Session = Depends(get_db_session),
):
    """下载原始文档文件。

    参数:
        document_id: 目标文档 ID。
        session: 数据库会话依赖。
    """
    doc = get_document_by_id(session, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = PathLib(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=doc.file_name,
        media_type="application/octet-stream",
    )


