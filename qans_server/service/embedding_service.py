"""向量化服务。"""

from __future__ import annotations

from typing import Iterable, List

from langchain_core.documents import Document

from qans_server.llm.vector_model import EmbeddingLLMClient


class EmbeddingService:
    """封装向量化相关能力。"""

    def __init__(self, client: EmbeddingLLMClient | None = None) -> None:
        self._client = client or EmbeddingLLMClient()

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """为文档列表生成向量。"""

        return self._client.embed_documents(documents)

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        """批量向量化文本。"""

        text_list = list(texts)
        if not text_list:
            return []
        return self._client.embed_texts(text_list)

    def embed_query(self, text: str) -> List[float]:
        """向量化查询语句。"""

        return self._client.embed_query(text)


