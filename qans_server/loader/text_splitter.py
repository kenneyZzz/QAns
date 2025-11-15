"""
文本分割器模块
基于文件类型对 `Document` 进行分割，支持为不同类型设置不同的分割策略
"""
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

try:
    # 新版拆分：独立包
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover - 兼容性兜底
    # 若未安装独立包，退回旧命名空间（如果环境中可用）
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore


class DocumentTextSplitter:
    """按文件类型分割文档的统一分割器"""

    # 每种类型的默认分割配置
    TYPE_CONFIGS: Dict[str, Dict] = {
        # 纯文本更紧凑
        "txt": {"chunk_size": 800, "chunk_overlap": 100},
        # PDF/Word 通常段落较长
        "pdf": {"chunk_size": 1000, "chunk_overlap": 120},
        "docx": {"chunk_size": 1000, "chunk_overlap": 120},
        # Markdown 适配标题/段落优先级分隔
        "md": {
            "chunk_size": 1200,
            "chunk_overlap": 150,
            "separators": [
                "\n### ",
                "\n## ",
                "\n# ",
                "\n\n",
                "\n",
                " ",
                "",
            ],
        },
        "markdown": {
            "chunk_size": 1200,
            "chunk_overlap": 150,
            "separators": [
                "\n### ",
                "\n## ",
                "\n# ",
                "\n\n",
                "\n",
                " ",
                "",
            ],
        },
        # HTML 适配常见段落换行
        "html": {
            "chunk_size": 1100,
            "chunk_overlap": 150,
            "separators": ["</p>", "<br>", "\n\n", "\n", " ", ""],
        },
        "htm": {
            "chunk_size": 1100,
            "chunk_overlap": 150,
            "separators": ["</p>", "<br>", "\n\n", "\n", " ", ""],
        },
        # Excel 元素化提取后文本通常较短，块可略大
        "xlsx": {"chunk_size": 1400, "chunk_overlap": 100},
        "xls": {"chunk_size": 1400, "chunk_overlap": 100},
        # JSON 文本
        "json": {"chunk_size": 1000, "chunk_overlap": 120},
    }

    def __init__(
        self,
        default_chunk_size: int = 1000,
        default_chunk_overlap: int = 200,
    ) -> None:
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap

    def _resolve_config(
        self,
        file_type: Optional[str],
        overrides: Optional[Dict] = None,
    ) -> Dict:
        file_key = (file_type or "").lower()
        base_cfg = self.TYPE_CONFIGS.get(file_key, {})

        config: Dict = {
            "chunk_size": int(base_cfg.get("chunk_size", self.default_chunk_size)),
            "chunk_overlap": int(base_cfg.get("chunk_overlap", self.default_chunk_overlap)),
        }

        if "separators" in base_cfg:
            separators = base_cfg.get("separators")
            config["separators"] = list(separators) if separators is not None else None

        if overrides:
            if overrides.get("chunk_size") is not None:
                config["chunk_size"] = int(overrides["chunk_size"])
            if overrides.get("chunk_overlap") is not None:
                config["chunk_overlap"] = int(overrides["chunk_overlap"])
            if overrides.get("separators") is not None:
                # 允许传入空列表清空分隔符
                config["separators"] = list(overrides["separators"])
            elif overrides.get("separators") is None and "separators" not in config:
                # 如果覆盖为空且原本没有 separators，需要显式保留 None
                config["separators"] = None
        else:
            if "separators" not in config:
                config["separators"] = None

        return config

    def _build_splitter(
        self,
        file_type: Optional[str],
        overrides: Optional[Dict] = None,
    ) -> Tuple[RecursiveCharacterTextSplitter, Dict]:
        config = self._resolve_config(file_type, overrides)
        separators = config.get("separators")

        chunk_size = int(config.get("chunk_size", self.default_chunk_size))
        chunk_overlap = int(config.get("chunk_overlap", self.default_chunk_overlap))

        if separators is not None:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
                add_start_index=True,
            )

        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                add_start_index=True,
            )

        return splitter, config

    def split_documents(
        self,
        documents: List[Document],
        *,
        overrides: Optional[Dict] = None,
    ) -> List[Document]:
        """
        将 `Document` 列表按类型分割为更小的 `Document` 块

        分割后会增强以下元数据字段：
        - chunk_index: 当前块序号
        - total_chunks: 当前源文档被分割后的总块数
        - chunk_size: 使用的分块大小
        - chunk_overlap: 使用的重叠大小
        - splitter: 分割器名称
        """
        if not documents:
            return []

        # 先按来源文档分组，保持每个源文档内的块序
        by_source: Dict[str, List[Document]] = {}
        for doc in documents:
            source_id = doc.metadata.get("source", id(doc))
            by_source.setdefault(str(source_id), []).append(doc)

        all_chunks: List[Document] = []

        for source_id, docs in by_source.items():
            # 每个源文档内，可能包含多个页面/元素，逐个分割再合并
            temp_chunks: List[Tuple[Document, Dict]] = []
            for doc in docs:
                file_type = doc.metadata.get("file_type")
                splitter, config = self._build_splitter(file_type, overrides)
                chunks = splitter.split_documents([doc])
                temp_chunks.extend((chunk, config) for chunk in chunks)

            total = len(temp_chunks)
            for idx, (chunk, config) in enumerate(temp_chunks):
                # 继承并增强元数据
                chunk.metadata = dict(chunk.metadata)
                chunk.metadata["chunk_index"] = idx
                chunk.metadata["total_chunks"] = total
                chunk.metadata["splitter"] = "recursive_character"
                # 记录实际参数，便于调试与追溯
                chunk.metadata["chunk_size"] = int(config.get("chunk_size", self.default_chunk_size))
                chunk.metadata["chunk_overlap"] = int(config.get("chunk_overlap", self.default_chunk_overlap))
                if config.get("separators") is not None:
                    chunk.metadata["separators"] = config.get("separators")

                all_chunks.append(chunk)

        return all_chunks

    def get_type_config(self, file_type: Optional[str]) -> Dict:
        """获取指定类型的默认分割配置。"""
        return self._resolve_config(file_type, overrides=None)

    def get_all_type_configs(self) -> Dict[str, Dict]:
        """返回所有类型的分割配置（已合并默认值）。"""
        configs: Dict[str, Dict] = {}
        for file_type in self.TYPE_CONFIGS.keys():
            configs[file_type] = self.get_type_config(file_type)
        return configs

    def get_default_config(self) -> Dict:
        """返回默认分割配置。"""
        return {
            "chunk_size": self.default_chunk_size,
            "chunk_overlap": self.default_chunk_overlap,
            "separators": None,
        }


