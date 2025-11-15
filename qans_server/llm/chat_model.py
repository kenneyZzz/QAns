"""聊天模型封装。"""

from typing import Generator, List
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from qans_server.setting_config import settings

class ChatLLMClient:

    def __init__(
        self,
        *,
        temperature: float = 0.7,
        timeout: int = 60,
        max_tokens: int = 2048
    ) -> None:
        self.chat_model = ChatOpenAI(model=settings.chat_model,
                                     base_url=settings.base_url,
                                     api_key=settings.api_key,
                                     temperature=temperature,
                                     timeout=timeout,
                                     max_tokens=max_tokens)


    def chat(self, messages: List[BaseMessage]) -> str:
        return self.chat_model.invoke(messages).content

    def stream_chat(self, messages: List[BaseMessage]) -> Generator[str, None, None]:
        for chunk in self.chat_model.stream(messages):
            text = str(chunk.content)
            if text:
                yield text

