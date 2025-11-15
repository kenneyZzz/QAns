"""应用配置模块。

该模块负责从环境变量中加载运行所需配置，并提供统一的配置访问入口。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from loguru import logger


@dataclass
class Settings:
    """应用配置。

    Attributes:
        mysql_dsn: MySQL 连接字符串（必填）。
        vector_url: Milvus 服务地址。
        vector_db: Milvus 数据库名称。
        base_url: llm 服务地址。
        api_key: llm api key
        chat_model: 文本模型
        embedding_url: 向量模型服务地址
        embedding_api_key: 向量模型api key
        embedding_model: 向量化模型。
        embedding_dim: 向量维度
        rerank_url: 重排模型url
        rerank_api_key: 重排模型api key
        rerank_model: 重排模型
        upload_dir: 文档上传目录。
        max_file_size: 允许上传的最大文件大小（字节）。
        api_prefix: 后端 API 前缀。
        cors_origins: 允许跨域的来源列表。
        log_level: 日志级别，可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL。
        log_dir: 日志文件目录。
        enable_console_log: 是否启用控制台日志输出。
        enable_file_log: 是否启用文件日志输出。
        log_rotation: 日志文件轮转条件，例如 "100 MB", "1 day"。
        log_retention: 日志文件保留时间，例如 "30 days"。
        log_serialize: 是否使用 JSON 格式输出日志。
    """

    mysql_dsn: str
    vector_url: str
    vector_db: str
    base_url: str
    api_key: str | None
    chat_model: str
    embedding_url: str
    embedding_api_key: str | None
    embedding_model: str
    embedding_dim: int
    rerank_url: str | None
    rerank_api_key: str | None
    rerank_model: str | None
    upload_dir: Path = field(default_factory=lambda: Path("uploads"))
    max_file_size: int = 100 * 1024 * 1024  # 100 MB
    api_prefix: str = "/api"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    enable_console_log: bool = True
    enable_file_log: bool = True
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"
    log_serialize: bool = False

    def ensure_directories(self) -> None:
        """确保关键目录存在。"""

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_origins(value: str | None) -> List[str]:
    if not value:
        return ["*"]
    parts = [origin.strip() for origin in value.split(",") if origin.strip()]
    return parts or ["*"]


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（使用缓存避免重复解析）。"""

    # 获取项目根目录的 .env 文件路径
    # __file__ 是 qans_server/setting_config.py，parent.parent 是项目根目录
    project_root = Path(__file__).parent.parent
    env_path = project_root / "qans_server/.env"
    logger.info(env_path)
    load_dotenv(dotenv_path=env_path)

    mysql_dsn = os.getenv("MYSQL_DSN")
    vector_url = os.getenv("VECTOR_URL")
    vector_db = os.getenv("VECTOR_DB", "default")

    # 文本模型
    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    chat_model = os.getenv("LLM_CHAT_MODEL")
    # 向量模型
    embedding_url = os.getenv("LLM_EMBEDDING_URL")
    embedding_api_key = os.getenv("LLM_EMBEDDING_API_KEY")
    embedding_model = os.getenv("LLM_EMBEDDING_MODEL")
    embedding_dim = os.getenv("EMBEDDING_DIM")
    # 重排模型
    rerank_url = os.getenv("LLM_RERANK_URL")
    rerank_api_key = os.getenv("LLM_RERANK_API_KEY")
    rerank_model = os.getenv("LLM_RERANK_MODEL")

    if not mysql_dsn:
        raise RuntimeError("环境变量 MYSQL_DSN 未配置")
    if not vector_url:
        raise RuntimeError("环境变量 VECTOR_URL 未配置")
    if not base_url:
        raise RuntimeError("环境变量 LLM_BASE_URL 未配置")
    if not chat_model:
        raise RuntimeError("环境变量 LLM_CHAT_MODEL 未配置")
    if not embedding_url:
        raise RuntimeError("环境变量 LLM_EMBEDDING_URL 未配置")
    if not embedding_model:
        raise RuntimeError("环境变量 LLM_EMBEDDING_MODEL 未配置")
    if not embedding_dim:
        raise RuntimeError("环境变量 EMBEDDING_DIM 未配置")

    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    max_file_size = _parse_int(os.getenv("MAX_FILE_SIZE"), 100 * 1024 * 1024)
    api_prefix = os.getenv("API_PREFIX", "/api")
    cors_origins = _parse_origins(os.getenv("CORS_ORIGINS"))

    # 日志配置
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    enable_console_log = os.getenv("ENABLE_CONSOLE_LOG", "true").lower() == "true"
    enable_file_log = os.getenv("ENABLE_FILE_LOG", "true").lower() == "true"
    log_rotation = os.getenv("LOG_ROTATION", "100 MB")
    log_retention = os.getenv("LOG_RETENTION", "30 days")
    log_serialize = os.getenv("LOG_SERIALIZE", "false").lower() == "true"

    settings = Settings(
        mysql_dsn=mysql_dsn,
        vector_url=vector_url,
        vector_db=vector_db,
        base_url=base_url,
        api_key=api_key,
        chat_model=chat_model,
        embedding_url=embedding_url,
        embedding_api_key=embedding_api_key,
        embedding_model=embedding_model,
        embedding_dim=int(embedding_dim),
        rerank_url=rerank_url,
        rerank_api_key=rerank_api_key,
        rerank_model=rerank_model,
        upload_dir=upload_dir,
        max_file_size=max_file_size,
        api_prefix=api_prefix,
        cors_origins=cors_origins,
        log_level=log_level,
        log_dir=log_dir,
        enable_console_log=enable_console_log,
        enable_file_log=enable_file_log,
        log_rotation=log_rotation,
        log_retention=log_retention,
        log_serialize=log_serialize,
    )

    settings.ensure_directories()
    return settings


# 便捷实例
settings = get_settings()

