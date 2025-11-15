"""聊天业务逻辑。"""

from __future__ import annotations

from typing import Dict, Generator, Iterable, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from qans_server.db.mysql.models.chat_message import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    create_chat_message,
    list_chat_messages,
)
from qans_server.db.mysql.models.chat_session import (
    ChatSession,
    create_chat_session,
    delete_chat_session,
    get_chat_session_by_id,
    increment_message_count,
    list_chat_sessions,
    update_chat_session_kbs,
    update_chat_session_title,
)
from qans_server.db.vector.collections.doc_chunk import VectorDocChunk
from qans_server.llm import rerank_documents
from qans_server.llm.chat_model import ChatLLMClient
from qans_server.service.embedding_service import EmbeddingService
from qans_server.setting_config import settings

SYSTEM_PROMPT = (
    "你是一个文档问答助手，请基于提供的参考内容回答用户问题。"
    "如果参考内容无法回答，请明确说明无法从文档中找到答案。"
)

HISTORY_PROMPT = (
    "请参考这些历史对话内容来理解上下文，并基于参考内容回答当前问题。\n"
    "历史对话记录："
)

class ChatService:
    """聊天服务，包含会话管理与问答流程。"""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        vector_repo: VectorDocChunk | None = None,
        llm_client: ChatLLMClient | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_repo = vector_repo or VectorDocChunk()
        self.llm_client = llm_client or ChatLLMClient()

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------
    def create_session(
        self,
        session: Session,
        knowledge_base_ids: List[int],
        title: Optional[str] = None,
    ) -> ChatSession:
        chat_session = create_chat_session(session, knowledge_base_ids=knowledge_base_ids, title=title)
        return chat_session

    def list_sessions(self, session: Session, *, limit: int = 20, offset: int = 0) -> List[ChatSession]:
        return list_chat_sessions(session, limit=limit, offset=offset)

    def get_session(self, session: Session, session_id: int) -> ChatSession | None:
        return get_chat_session_by_id(session, session_id)

    def update_session_title(self, db: Session, session_id: int, title: str) -> ChatSession | None:
        return update_chat_session_title(db, session_id, title)

    def update_session_knowledge_bases(
        self,
        db: Session,
        session_id: int,
        knowledge_base_ids: List[int],
    ) -> ChatSession | None:
        return update_chat_session_kbs(db, session_id, knowledge_base_ids)

    def delete_session(self, db: Session, session_id: int) -> bool:
        return delete_chat_session(db, session_id)

    def list_messages(self, db: Session, session_id: int, limit: int | None = None):
        return list_chat_messages(db, session_id=session_id, limit=limit)


    def stream_message(
        self,
        db: Session,
        *,
        session_id: int,
        query: str,
        knowledge_base_ids: Optional[List[int]] = None,
        top_k: int = 3,
    ) -> Tuple[Generator[str, None, None], List[dict]]:
        """以流式方式生成回答，返回生成器和引用来源。"""

        if not query.strip():
            raise ValueError("问题不能为空")

        chat_session = self._ensure_session(db, session_id)
        kb_ids = knowledge_base_ids or chat_session.knowledge_base_ids or []
        if not kb_ids:
            raise ValueError("会话未选择知识库，无法执行检索")

        create_chat_message(db, session_id=session_id, role=MESSAGE_ROLE_USER, content=query)
        increment_message_count(db, session_id, 1)

        query_vector = self.embedding_service.embed_query(query)
        # 混合检索
        related_chunks = self.vector_repo.search_similar_chunks(
            query=query,
            query_vector=query_vector,
            knowledge_base_ids=kb_ids,
            top_k=top_k,
        )

        # 重排
        if settings.rerank_model is None:
            rank_chunks = rerank_documents(query, related_chunks, top_k=top_k)
        else:
            rank_chunks = related_chunks

        # 构建引用来源
        context_text, sources = self._build_context(rank_chunks)

        # 构建消息
        messages = self._build_messages(query, context_text, db, session_id)

        def generator() -> Generator[str, None, None]:
            chunks: List[str] = []
            # 大模型调用
            for content in self.llm_client.stream_chat(messages):
                if content:
                    chunks.append(content)
                    yield content

            full_answer = "".join(chunks)
            create_chat_message(
                db,
                session_id=session_id,
                role=MESSAGE_ROLE_ASSISTANT,
                content=full_answer,
                sources=sources,
            )
            increment_message_count(db, session_id, 1)

        return generator(), sources

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def _build_context(self, chunks: List[dict]) -> Tuple[str, List[dict]]:
        if not chunks:
            return "", []

        context_parts: List[str] = []
        sources: List[dict] = []
        seen_doc_ids: set = set()  # 用于跟踪已添加的文档ID，避免重复引用
        
        for idx, item in enumerate(chunks, start=1):
            text = item.get("text", "")
            meta = item.get("meta", {})
            title = meta.get("file_name") or meta.get("source") or f"文档片段{idx}"
            context_parts.append(f"[{idx}] 来源: {title}\n{text}")

            doc_id = item.get("doc_id")
            # 只添加未出现过的文档ID到sources中，避免重复引用
            if doc_id is not None and doc_id not in seen_doc_ids:
                seen_doc_ids.add(doc_id)
                sources.append(
                    {
                        "doc_id": doc_id,
                        "chunk_id": item.get("chunk_id"),
                        "knowledge_base_id": item.get("knowledge_base_id"),
                        "text": text,
                        "meta": meta,
                    }
                )

        return "\n\n".join(context_parts), sources

    def _build_messages(self, query: str, context_text: str, db: Session, session_id: int):
        # 构建完整的消息列表：系统消息 + 历史记录提示词 + 历史消息 + 当前消息
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # 获取历史消息（排除当前刚创建的用户消息）
        history_messages = self._get_history_messages_within_limit(db, session_id)
        # 如果有历史消息，添加历史记录提示词说明
        if history_messages:
            messages.append(HumanMessage(content=HISTORY_PROMPT))
            messages.extend(history_messages)

        messages.append(HumanMessage(content=self._compose_prompt(query, context_text)))
        return messages

    def _compose_prompt(self, question: str, context: str) -> str:
        if context:
            return (
                "以下是与问题相关的参考内容，请基于这些内容回答。\n\n"
                f"参考内容:\n{context}\n\n"
                f"问题: {question}"
            )
        return (
            "当前没有找到相关参考内容，请根据已有知识谨慎回答。\n\n"
            f"问题: {question}"
        )

    def _ensure_session(self, db: Session, session_id: int) -> ChatSession:
        chat_session = get_chat_session_by_id(db, session_id)
        if not chat_session:
            raise ValueError(f"会话不存在: {session_id}")
        return chat_session

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量。
        使用简单的估算方法：中文和英文混合文本，大约1个字符≈1.5个token。
        这是一个近似值，实际token数量可能因模型而异。
        """
        if not text:
            return 0
        # 对于中英文混合文本，使用字符数 * 1.5 作为估算
        # 这是一个保守的估算，确保不超过限制
        return int(len(text) * 1.5)

    def _get_history_messages_within_limit(
        self,
        db: Session,
        session_id: int,
        max_tokens: int = 4000
    ) -> List[HumanMessage | AIMessage]:
        """
        获取会话的历史消息，确保总token数不超过限制。
        
        规则：
        1. 如果聊天记录没有超过4K，则全部带上
        2. 如果聊天记录超过4K，刚好取到没有超过4K之前的聊天记录
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            max_tokens: 最大token数限制，默认4000
            
        Returns:
            符合token限制的历史消息列表（LangChain消息对象）
        """
        # 获取所有历史消息（排除最后一条，因为那是当前刚创建的用户消息）
        all_messages = list_chat_messages(db, session_id=session_id)
        
        # 排除最后一条消息（当前正在发送的用户消息）
        if all_messages:
            all_messages = all_messages[:-1]
        
        if not all_messages:
            return []
        
        # 从最旧的消息开始，累加token数，直到达到限制
        history_messages: List[HumanMessage | AIMessage] = []
        total_tokens = 0
        
        for msg in all_messages:
            # 估算当前消息的token数
            msg_tokens = self._estimate_tokens(msg.content)
            
            # 如果加上这条消息会超过限制，则停止
            if total_tokens + msg_tokens > max_tokens:
                break
            
            # 转换为LangChain消息对象
            if msg.role == MESSAGE_ROLE_USER:
                history_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MESSAGE_ROLE_ASSISTANT:
                history_messages.append(AIMessage(content=msg.content))
            
            total_tokens += msg_tokens
        
        return history_messages


