from typing import List

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from qans_server.setting_config import settings

class EmbeddingLLMClient:

    def __init__(self) -> None:
        # 根据 embedding_url 判断使用哪个嵌入模型
        if "dashscope" in settings.embedding_url.lower():
            # 通义千问向量模型调用
            self.embedding_model = DashScopeEmbeddings(model=settings.embedding_model,
                                                        dashscope_api_key=settings.embedding_api_key)
        else:
            # 其他模型使用 OpenAI 兼容接口
            self.embedding_model = OpenAIEmbeddings(model=settings.embedding_model,
                                                    base_url=settings.embedding_url,
                                                    api_key=settings.embedding_api_key)

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        texts = [d.page_content or "" for d in documents]
        if not texts:
            return []
        return self.embedding_model.embed_documents(texts)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.embedding_model.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embedding_model.embed_query(text)

