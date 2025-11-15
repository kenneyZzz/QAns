"""文件相关工具函数。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile


def ensure_directory(path: Path) -> Path:
    """确保目录存在。"""

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（不包含点）。"""

    return Path(filename).suffix.lower().lstrip(".")


def validate_file_type(filename: str, allowed_types: Iterable[str]) -> None:
    """验证文件类型是否在允许列表中。"""

    ext = get_file_extension(filename)
    allowed = {typ.lower().lstrip(".") for typ in allowed_types}
    if allowed and ext not in allowed:
        raise ValueError(f"文件类型不支持: {ext}，支持类型: {', '.join(sorted(allowed))}")


def validate_file_size(file_size: int, max_size: int) -> None:
    """验证文件大小是否超出限制。"""

    if max_size and file_size > max_size:
        raise ValueError(f"文件大小超过限制: {file_size} > {max_size}")


def save_upload_file(upload_dir: Path, file: UploadFile) -> Path:
    """保存上传文件到指定目录，返回保存后的路径。"""

    ensure_directory(upload_dir)
    filename = Path(file.filename or "").name
    if not filename:
        raise ValueError("上传文件缺少文件名")

    destination = upload_dir / filename

    # 如果文件存在，添加数字后缀避免覆盖
    if destination.exists():
        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while True:
            candidate = upload_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                destination = candidate
                break
            counter += 1

    file.file.seek(0)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return destination


def delete_file(path: Path | str) -> None:
    """删除文件，忽略不存在的情况。"""

    file_path = Path(path)
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        # 记录日志由调用方向上层处理，这里静默失败
        pass


def get_file_size(path: Path | str) -> int:
    """获取文件大小（字节）。"""

    return os.path.getsize(path)


