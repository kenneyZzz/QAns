from typing import List, Optional
from langchain_core.documents import Document
from pymilvus import AnnSearchRequest, Function, FunctionType

from qans_server.db.vector.base import db_client


class VectorDocChunk:
    """向量文档分块操作类"""

    def __init__(self):
        self.db_client = db_client
        self.collection_name = "t_doc_chunk"

    def insert_documents(
        self,
        documents: List[Document],
        vectors: List[List[float]],
        doc_id: int,
        knowledge_base_id: int
    ) -> int:
        """
        将分块后的 `Document` 列表写入向量库。
        
        Args:
            documents: 文档分块列表
            vectors: 对应的向量列表
            doc_id: 文档ID
            knowledge_base_id: 知识库ID
            
        Returns:
            插入的向量数量
        """
        if not documents or not vectors:
            return 0

        if len(documents) != len(vectors):
            raise ValueError("documents和vectors的长度必须一致")

        rows = []
        for i, doc in enumerate(documents):
            meta = dict(doc.metadata or {})
            embeddings = vectors[i]
            
            if len(embeddings) == 0:
                continue

            # 生成字段
            chunk_id = meta.get("chunk_index", i)
            text = doc.page_content or ""

            rows.append(
                {
                    "vector": embeddings,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "knowledge_base_id": knowledge_base_id,
                    "text": text,
                    "meta": meta,
                }
            )

        if not rows:
            return 0

        # 插入数据（行式）
        self.db_client.insert(collection_name=self.collection_name, data=rows)
        return len(rows)

    def search_similar_chunks(
        self,
        query: str,
        query_vector: List[float],
        knowledge_base_ids: List[int],
        top_k: int = 5,
    ) -> List[dict]:
        """
        混合检索。

        Args:
            query_vector: 查询向量
            knowledge_base_ids: 知识库ID列表（用于过滤）
            top_k: 返回Top-K*2结果

        Returns:
            检索结果列表，每个结果包含：
            - doc_id: 文档ID
            - chunk_id: 分块索引
            - knowledge_base_id: 知识库ID
            - text: 文本内容
            - meta: 元数据
        """
        if not query_vector:
            return []
        
        if not knowledge_base_ids:
            return []

        # 构建过滤表达式：knowledge_base_id in [1,2,3]
        # MilvusClient使用in表达式格式
        if len(knowledge_base_ids) == 1:
            expr = f"knowledge_base_id == {knowledge_base_ids[0]}"
        else:
            kb_ids_str = ",".join(str(kb_id) for kb_id in knowledge_base_ids)
            expr = f"knowledge_base_id in [{kb_ids_str}]"

        """ milvus 混合检索 """
        # text semantic search (dense)
        search_param_1 = {
            "data": [query_vector],
            "anns_field": "vector",
            "param": {"nprobe": 32},
            "limit": top_k,
            "expr": expr
        }
        request_1 = AnnSearchRequest(**search_param_1)

        # full-text search (sparse)
        search_param_2 = {
            "data": [query],
            "anns_field": "sparse_vector",
            "param": {"drop_ratio_search": 0.2},
            "limit": top_k,
            "expr": expr
        }
        request_2 = AnnSearchRequest(**search_param_2)

        reqs = [request_1, request_2]

        ranker = Function(
            name="rrf",
            input_field_names=[],  # Must be an empty list
            function_type=FunctionType.RERANK,
            params={
                "reranker": "rrf",
                "k": top_k * 2
            }
        )

        results = self.db_client.hybrid_search(
            collection_name=self.collection_name,
            reqs=reqs,
            ranker=ranker,
            filter=expr,
            limit=top_k*2,
            output_fields=["doc_id", "chunk_id", "knowledge_base_id", "text", "meta"]
        )
        return [hit.fields for hits in results for hit in hits]


    def delete_documents_by_doc_id(self, doc_id: int) -> int:
        """
        删除指定文档的所有向量数据。
        
        Args:
            doc_id: 文档ID
            
        Returns:
            删除的向量数量
        """
        expr = f"doc_id == {doc_id}"
        result = self.db_client.delete(
            collection_name=self.collection_name,
            filter=expr
        )
        return result.get("delete_count", 0) if isinstance(result, dict) else 0

    def delete_documents_by_knowledge_base_id(self, knowledge_base_id: int) -> int:
        """
        删除指定知识库的所有向量数据。
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            删除的向量数量
        """
        expr = f"knowledge_base_id == {knowledge_base_id}"
        # MilvusClient的delete方法使用filter参数
        result = self.db_client.delete(
            collection_name=self.collection_name,
            filter=expr
        )
        return result.get("delete_count", 0) if isinstance(result, dict) else 0

    def count_by_knowledge_base_id(self, knowledge_base_id: int) -> int:
        """
        统计知识库的向量数量。
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            向量数量
        """
        expr = f"knowledge_base_id == {knowledge_base_id}"
        # 使用query获取所有匹配的记录（不限制limit），然后计算长度
        # 注意：对于大数据量，这可能效率较低，建议使用Milvus的count功能（如果支持）
        result = self.db_client.query(
            collection_name=self.collection_name,
            filter=expr,
            output_fields=["doc_id"]
        )
        return len(result) if result else 0
