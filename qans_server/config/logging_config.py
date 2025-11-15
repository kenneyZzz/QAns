"""日志配置模块。

该模块负责配置 loguru 日志系统，适用于生产环境。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    *,
    log_level: str = "INFO",
    log_dir: Path | str | None = None,
    enable_console: bool = True,
    enable_file: bool = True,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip",
    serialize: bool = False,
) -> None:
    """配置 loguru 日志系统。

    Args:
        log_level: 日志级别，可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_dir: 日志文件目录，如果为 None 则使用 logs 目录
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        rotation: 日志文件轮转条件，例如 "100 MB", "1 day", "12:00"
        retention: 日志文件保留时间，例如 "30 days", "10 weeks"
        compression: 日志文件压缩格式，例如 "zip", "gz", "bz2"
        serialize: 是否使用 JSON 格式输出（适用于日志收集系统）
    """
    # 移除默认的处理器
    logger.remove()

    # 日志格式
    if serialize:
        # JSON 格式，适用于日志收集系统（如 ELK、Loki）
        log_format = (
            '{{"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"}}'
        )
    else:
        # 人类可读格式
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 控制台输出（开发/调试环境）
    if enable_console:
        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # 文件输出（生产环境）
    if enable_file:
        # 确定日志目录
        if log_dir is None:
            log_dir = Path("../logs")
        else:
            log_dir = Path(log_dir)

        log_dir.mkdir(parents=True, exist_ok=True)

        # 所有日志输出到 app.log
        logger.add(
            log_dir / "app.log",
            format=log_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True,  # 异步写入，提高性能
        )

        # 错误日志单独输出到 error.log
        logger.add(
            log_dir / "error.log",
            format=log_format,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

        # 警告日志单独输出到 warning.log
        logger.add(
            log_dir / "warning.log",
            format=log_format,
            level="WARNING",
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    # 记录日志系统初始化信息
    logger.info("日志系统已初始化，日志级别: {}", log_level)

