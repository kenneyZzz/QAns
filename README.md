# QAns - RAG技术实战项目

## ⚠️ 重要说明

**QAns是一个用于学习RAG（Retrieval-Augmented Generation）技术的实战项目**，包含了完整的RAG流程实现，可以帮助开发者深入理解RAG系统的核心组件和工作原理。

**请注意：本项目功能不完整，仅用于学习和研究目的，不能直接用于生产环境。**

---

## 📚 项目简介

QAns是一个基于RAG技术的智能文档问答系统，完整实现了从文档处理到问答生成的端到端流程。通过本项目，你可以学习到：

- RAG系统的完整架构设计
- 文档加载、分块、向量化的最佳实践
  - 混合检索（Dense + Sparse）的实现
- 重排序（Reranking）技术的应用
- 上下文管理和流式生成

---

## 🎬 视频介绍

你可以直接在线观看项目演示及引导视频：

https://github.com/kenneyZzz/QAns/releases/download/1.0/QAns.mp4

> 💡 提示：点击上方链接即可下载或在线观看视频（如果浏览器支持）

---

## 🏗️ RAG系统架构

### 核心流程

```
文档上传 → 文档加载 → 文本分块 → 向量化 → 向量存储 → 检索 → 重排序 → 上下文构建 → LLM生成
```

### 1. 文档处理流程

#### 1.1 文档加载（Document Loading）

**位置**: `qans_server/loader/document_loader.py`

系统支持多种文档格式的加载：
- **文本文件**: `.txt`, `.json`
- **PDF文档**: `.pdf`
- **Word文档**: `.docx`
- **Markdown**: `.md`, `.markdown`
- **Excel表格**: `.xlsx`, `.xls`
- **HTML网页**: `.html`, `.htm`

**技术要点**:
- 使用LangChain的文档加载器统一接口
- 为每个文档添加元数据（文件路径、文件名、文件类型）
- 支持批量加载和目录递归加载

#### 1.2 文本分块（Text Chunking）

**位置**: `qans_server/loader/text_splitter.py`

文本分块是RAG系统的关键环节，直接影响检索质量：

**分块策略**:
- 使用`RecursiveCharacterTextSplitter`进行递归字符分割
- 根据文件类型采用不同的分块参数：
  - **纯文本**: `chunk_size=800`, `chunk_overlap=100`
  - **PDF/Word**: `chunk_size=1000`, `chunk_overlap=120`
  - **Markdown**: `chunk_size=1200`, `chunk_overlap=150`，优先按标题分割
  - **Excel**: `chunk_size=1400`, `chunk_overlap=100`

**分块原则**:
- **Chunk Size**: 控制每个块的大小，需要平衡检索精度和上下文完整性
- **Chunk Overlap**: 块之间的重叠，避免语义边界被切断
- **Separators**: 针对不同格式使用不同的分隔符优先级

**元数据增强**:
每个分块都会记录：
- `chunk_index`: 块序号
- `total_chunks`: 总块数
- `chunk_size`: 使用的分块大小
- `chunk_overlap`: 使用的重叠大小
- `splitter`: 分割器名称

### 2. 向量化（Embedding）

**位置**: `qans_server/service/embedding_service.py`, `qans_server/llm/vector_model.py`

**向量模型**:
- 支持DashScope（通义千问）向量模型
- 支持OpenAI兼容接口的向量模型
- 通过配置灵活切换不同的向量模型

**向量化流程**:
1. 文档分块后，批量调用向量模型API
2. 将文本转换为固定维度的向量表示
3. 向量维度由`EMBEDDING_DIM`环境变量配置

**技术要点**:
- 区分文档向量化和查询向量化（`embed_documents` vs `embed_query`）
- 批量处理提高效率
- 向量维度需要与向量数据库的schema匹配

### 3. 向量存储（Vector Storage）

**位置**: `qans_server/db/vector/collections/doc_chunk.py`

**向量数据库**: Milvus

**存储结构**:
- **vector**: 密集向量（Dense Vector），用于语义相似度检索
- **sparse_vector**: 稀疏向量（Sparse Vector），用于关键词匹配
- **text**: 原始文本内容
- **doc_id**: 文档ID
- **chunk_id**: 分块索引
- **knowledge_base_id**: 知识库ID
- **meta**: 元数据（JSON格式）

**技术要点**:
- 使用Milvus的混合检索能力
- 支持按知识库过滤
- 向量数据与MySQL元数据分离存储

### 4. 检索（Retrieval）

**位置**: `qans_server/db/vector/collections/doc_chunk.py` - `search_similar_chunks`

**混合检索（Hybrid Search）**:

系统实现了**Dense + Sparse**混合检索策略：

1. **Dense检索（语义检索）**:
   - 使用查询向量在向量空间中搜索相似文档
   - 基于余弦相似度或内积计算
   - 参数：`nprobe=32`（控制搜索精度）

2. **Sparse检索（关键词检索）**:
   - 使用BM25算法进行全文检索
   - 基于关键词匹配，适合精确术语查找
   - 参数：`drop_ratio_search=0.2`（控制稀疏度）

3. **RRF重排（Reciprocal Rank Fusion）**:
   - 将两种检索结果进行融合
   - 使用RRF算法计算最终排序
   - 公式：`RRF_score = 1/(k + rank)`，k为常数

**检索流程**:
```
查询文本 → 向量化 → Dense检索 → Sparse检索 → RRF融合 → Top-K结果
```

**技术优势**:
- **Dense检索**: 捕获语义相似性，适合同义词、概念匹配
- **Sparse检索**: 捕获精确匹配，适合专业术语、实体名称
- **混合检索**: 结合两者优势，提高检索召回率和准确率

### 5. 重排序（Reranking）

**位置**: `qans_server/llm/rerank_model.py`, `qans_server/service/chat_service.py`

**重排序目的**:
- 对初步检索结果进行精细化排序
- 考虑查询与文档的语义相关性
- 提高Top-K结果的准确性

**实现方式**:
- 使用专门的重排序模型API
- 输入：查询文本 + 候选文档列表
- 输出：按相关性得分排序的文档列表

**技术要点**:
- 重排序模型通常基于Cross-Encoder架构
- 计算查询-文档对的交互特征
- 比Bi-Encoder更准确但计算成本更高

### 6. 上下文构建（Context Construction）

**位置**: `qans_server/service/chat_service.py` - `_build_context`, `_build_messages`

**上下文组成**:
1. **系统提示词（System Prompt）**: 定义AI助手的角色和行为
2. **历史对话**: 维护对话上下文（Token限制：4000）
3. **检索到的参考内容**: 包含来源标注的文档片段
4. **当前问题**: 用户查询

**上下文格式**:
```
[系统提示] 你是一个文档问答助手...

[历史对话提示] 请参考这些历史对话内容...
历史对话记录：
用户: ...
助手: ...

[参考内容]
[1] 来源: 文档A.pdf
内容片段1...

[2] 来源: 文档B.docx
内容片段2...

[问题] 用户的问题
```

**技术要点**:
- 使用Token估算控制上下文长度
- 历史消息采用滑动窗口策略
- 引用来源便于追溯和验证

### 7. 生成（Generation）

**位置**: `qans_server/service/chat_service.py` - `stream_message`, `qans_server/llm/chat_model.py`

**生成流程**:
1. 构建完整的消息列表（系统提示 + 历史 + 参考内容 + 问题）
2. 调用LLM API进行流式生成
3. 实时返回生成的文本片段
4. 保存完整的回答到数据库

**流式生成**:
- 使用`stream_chat`方法实现流式输出
- 提高用户体验，减少等待时间
- 支持SSE（Server-Sent Events）推送到前端

**技术要点**:
- 使用LangChain的`ChatOpenAI`统一接口
- 支持OpenAI兼容的API
- 可配置temperature、max_tokens等参数

---

## 🔧 技术栈

### 后端框架
- **FastAPI**: 现代Python Web框架
- **SQLAlchemy**: ORM框架
- **LangChain**: LLM应用开发框架

### 向量数据库
- **Milvus**: 高性能向量数据库，支持混合检索

### 关系数据库
- **MySQL**: 存储元数据（文档、知识库、会话等）

### LLM集成
- **向量模型**: DashScope / OpenAI兼容接口
- **文本模型**: OpenAI兼容接口
- **重排序模型**: 可选的外部API

### 文档处理
- **pypdf**: PDF解析
- **docx2txt**: Word文档解析
- **unstructured**: 结构化文档解析
- **openpyxl/xlrd**: Excel文件处理

---

## 📁 项目结构

```
qans_server/
├── api/                    # API路由
│   ├── chat.py            # 聊天相关API
│   ├── document.py        # 文档管理API
│   └── knowledge_base.py  # 知识库管理API
├── config/                 # 配置模块
│   ├── logging_config.py  # 日志配置
│   └── logging_middleware.py  # 日志中间件
├── db/                     # 数据库层
│   ├── mysql/             # MySQL相关
│   │   ├── models/        # 数据模型
│   │   └── base.py        # 数据库连接
│   └── vector/            # 向量数据库
│       ├── base.py        # Milvus连接
│       └── collections/   # 集合操作
│           └── doc_chunk.py  # 文档分块向量操作
├── init/                   # 初始化脚本
│   ├── init_mysql_db.py   # MySQL初始化
│   └── init_milvus_db.py  # Milvus初始化
├── llm/                    # LLM客户端
│   ├── chat_model.py      # 文本生成模型
│   ├── vector_model.py    # 向量模型
│   └── rerank_model.py    # 重排序模型
├── loader/                 # 文档加载器
│   ├── document_loader.py # 文档加载
│   └── text_splitter.py   # 文本分块
├── service/                # 业务逻辑层
│   ├── chat_service.py    # 聊天服务（RAG核心）
│   ├── document_service.py # 文档服务
│   ├── embedding_service.py # 向量化服务
│   └── knowledge_base_service.py # 知识库服务
├── util/                   # 工具函数
│   └── file_util.py       # 文件操作
├── main.py                 # 应用入口
└── setting_config.py       # 配置管理
```

---

## 🚀 快速开始

详细的安装部署步骤请参考：[部署文档](deploy/QAns安装部署.md)

---

## 📖 RAG核心概念

### 什么是RAG？

RAG（Retrieval-Augmented Generation）是一种结合检索和生成的AI技术：

1. **检索（Retrieval）**: 从知识库中检索与查询相关的文档片段
2. **增强（Augmentation）**: 将检索到的内容作为上下文
3. **生成（Generation）**: 基于上下文生成回答

### RAG的优势

- **知识更新**: 无需重新训练模型即可更新知识
- **可追溯性**: 可以追溯到具体的文档来源
- **减少幻觉**: 基于真实文档生成，减少错误信息
- **领域适应**: 可以快速适配特定领域知识

### RAG的关键挑战

1. **检索质量**: 如何准确找到相关文档
2. **上下文长度**: 如何平衡检索数量和上下文限制
3. **分块策略**: 如何合理分割文档
4. **重排序**: 如何提高Top-K的准确性

---

## 🎯 学习要点

### 1. 文档分块策略

- **固定大小分块**: 简单但可能切断语义
- **递归字符分块**: 按分隔符优先级分割
- **语义分块**: 基于语义边界分割（未实现）
- **重叠策略**: 避免边界信息丢失

### 2. 检索策略

- **Dense检索**: 语义相似度，适合概念匹配
- **Sparse检索**: 关键词匹配，适合精确查找
- **混合检索**: 结合两者优势
- **重排序**: 精细化排序，提高准确率

### 3. 上下文管理

- **Token限制**: 控制上下文长度
- **历史管理**: 滑动窗口策略
- **来源标注**: 便于追溯和验证

### 4. Prompt工程

- **系统提示**: 定义AI角色和行为
- **上下文格式**: 清晰的结构化格式
- **指令设计**: 引导模型正确理解任务

---

## 📄 许可证

本项目仅供学习研究使用。

---

## 🙏 致谢

感谢以下开源项目的支持：
- [LangChain](https://github.com/langchain-ai/langchain)
- [Milvus](https://github.com/milvus-io/milvus)
- [FastAPI](https://github.com/tiangolo/fastapi)
