from typing import Mapping, Optional
import requests
from qans_server.setting_config import settings

class RerankError(Exception):
    """重排序服务请求异常。"""

def rerank_documents(
    query: str,
    documents: list[dict],
    *,
    extra_headers: Mapping[str, str] | None = None,
    top_k: Optional[int] | None = None,
) -> list[dict]:

    if not documents:
        raise ValueError("documents must contain at least one entry")

    headers = {"accept": "application/json", "Content-Type": "application/json"}
    if settings.rerank_api_key:
        headers["Authorization"] = f"Bearer {settings.rerank_api_key}"
    if extra_headers:
        headers.update(extra_headers)

    # 提取文本内容用于重排序
    document_texts = []
    for doc in documents:
        if not isinstance(doc, dict):
            raise ValueError("documents 中的每个元素必须是 dict 类型")
        text = doc.get("text", "")
        if not isinstance(text, str):
            raise ValueError("documents 中的每个 dict 必须包含 'text' 字段且为字符串类型")
        document_texts.append(text)

    payload = {
        "model": settings.rerank_model,
        "query": query,
        "documents": document_texts,
    }

    try:
        response = requests.post(
            settings.rerank_url,
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RerankError("重排序服务请求失败") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RerankError("重排序服务返回了无效的 JSON") from exc

    if not isinstance(data, Mapping):
        raise RerankError("重排序服务返回了意外的响应结构")

    results = data.get("results")
    if not isinstance(results, list):
        raise RerankError("重排序服务返回了无效的 results 字段")

    ranked_documents = []
    for item in results:
        if not isinstance(item, Mapping):
            raise RerankError("重排序结果项格式错误")

        index = item.get("index")
        if not isinstance(index, int) or not (0 <= index < len(documents)):
            raise RerankError("重排序结果 index 越界或类型错误")

        ranked_documents.append(documents[index])

    if top_k is not None:
        ranked_documents = ranked_documents[:top_k]

    return ranked_documents

