"""FastAPI 应用入口。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qans_server.api import api_router
from qans_server.setting_config import get_settings
from qans_server.config.logging_config import setup_logging
from qans_server.config.logging_middleware import LoggingMiddleware

def create_app() -> FastAPI:
    settings = get_settings()

    # 初始化日志系统
    setup_logging(
        log_level=settings.log_level,
        log_dir=settings.log_dir,
        enable_console=settings.enable_console_log,
        enable_file=settings.enable_file_log,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        serialize=settings.log_serialize,
    )

    app = FastAPI(
        title="智能文档系统 API",
        description="基于 RAG 的智能文档问答系统",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加日志记录中间件（应该在 CORS 之后添加，以便记录完整的请求信息）
    app.add_middleware(LoggingMiddleware)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/ping", tags=["健康检查"])  # pragma: no cover - trivial route
    async def ping() -> dict:
        return {"status": "ok"}

    return app


app = create_app()


