"""日志记录中间件。

该中间件用于记录 FastAPI 接口的请求和响应信息。
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """记录 HTTP 请求和响应的中间件。"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志。

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            FastAPI 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端信息
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # 记录请求信息
        logger.info(
            "请求开始 | {} {} | 客户端IP: {} | 查询参数: {}",
            method,
            path,
            client_ip,
            query_params if query_params else "无",
        )

        # 记录请求体信息（仅记录元数据，不读取实际内容，避免影响请求处理）
        content_type = request.headers.get("content-type", "")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > 0:
                    if "application/json" in content_type.lower():
                        logger.debug("请求体类型: JSON, 长度: {} bytes", length)
                    elif "multipart/form-data" in content_type.lower():
                        logger.debug("请求体类型: 表单数据, 长度: {} bytes", length)
                    else:
                        logger.debug("请求体类型: {}, 长度: {} bytes", content_type, length)
            except (ValueError, TypeError):
                pass

        # 执行请求处理
        try:
            response = await call_next(request)
        except Exception as exc:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录异常
            logger.exception(
                "请求处理异常 | {} {} | 处理时间: {:.3f}s | 异常: {}",
                method,
                path,
                process_time,
                type(exc).__name__,
            )
            raise

        # 计算处理时间
        process_time = time.time() - start_time

        # 获取响应状态码
        status_code = response.status_code

        # 根据状态码选择日志级别
        if status_code >= 500:
            log_func = logger.error
        elif status_code >= 400:
            log_func = logger.warning
        else:
            log_func = logger.info

        # 记录响应信息
        log_func(
            "请求完成 | {} {} | 状态码: {} | 处理时间: {:.3f}s | 客户端IP: {}",
            method,
            path,
            status_code,
            process_time,
            client_ip,
        )

        # 添加响应头，记录处理时间
        response.headers["X-Process-Time"] = str(process_time)

        return response

