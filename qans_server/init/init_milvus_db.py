"""
数据库初始化脚本
用于创建MySQL表和Milvus集合
"""
import sys
from pathlib import Path
from pymilvus import (
    FieldSchema,
    CollectionSchema,
    DataType, Function, FunctionType,
)

from qans_server.setting_config import settings

# 添加项目根目录到 Python 路径，以便能够导入 qans_server 模块
# 获取当前文件的目录，然后向上查找项目根目录（包含 qans_server 目录的目录）
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent  # 从 init/init_milvus_db.py 向上3级到项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pymilvus import MilvusClient

def init_milvus_database(db_client: MilvusClient, db_name: str = "qans"):
    """
    初始化Milvus数据库
    
    Args:
        db_name: 数据库名称，默认"qans"
    """
    print(f"开始初始化Milvus数据库（数据库名: {db_name}）...")
    
    try:
        # 获取环境变量中的 Milvus 连接地址
        vector_url = settings.vector_url
        if not vector_url:
            print("  警告：未找到 VECTOR_URL 环境变量，跳过数据库创建")
            return
        
        # 检查数据库是否已存在
        databases = db_client.list_databases()
        
        if db_name in databases:
            print(f"  数据库 {db_name} 已存在，跳过创建")
        else:
            # 创建数据库
            db_client.create_database(db_name=db_name)
            print(f"✓ 数据库 {db_name} 创建成功")
    except Exception as e:
        print(f"✗ Milvus数据库创建失败: {e}")
        print("  提示：请确保Milvus服务已启动，并检查VECTOR_URL环境变量")
        raise


def init_milvus_collection(embedding_dim: int = 1024):
    """
    初始化Milvus集合和索引
    
    Args:
        embedding_dim: 向量维度，默认1024（需要根据实际embedding模型调整）
    """
    print(f"开始初始化Milvus集合（向量维度: {embedding_dim}）...")
    
    collection_name = "t_doc_chunk"
    
    try:
        # 使用MilvusClient检查集合是否存在
        collections = db_client.list_collections()
        
        if collection_name in collections:
            print(f"  集合 {collection_name} 已存在，跳过创建")
            print("  注意：如果集合结构需要更新，请手动删除后重新创建")
            return

        # 定义字段schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="主键ID"
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=embedding_dim,
                description="文档向量"
            ),
            FieldSchema(
                name="sparse_vector",
                dtype=DataType.SPARSE_FLOAT_VECTOR,
                description="文档稀疏向量"
            ),
            FieldSchema(
                name="doc_id",
                dtype=DataType.INT64,
                description="文档ID"
            ),
            FieldSchema(
                name="chunk_id",
                dtype=DataType.INT64,
                description="分块索引"
            ),
            FieldSchema(
                name="knowledge_base_id",
                dtype=DataType.INT64,
                description="知识库ID"
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                enable_analyzer=True,
                max_length=65535,
                description="分块文本"
            ),
            FieldSchema(
                name="meta",
                dtype=DataType.JSON,
                description="元数据"
            ),
        ]
        
        # 创建集合schema
        schema = CollectionSchema(
            fields=fields,
            description="文档分块向量集合"
        )

        # Add function to schema, bm25 全文检索
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["text"],
            output_field_names=["sparse_vector"],
            function_type=FunctionType.BM25,
        )
        schema.add_function(bm25_function)

        print(f"✓ 集合 {collection_name} 创建成功")
        
        # 创建索引
        index_params = db_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE"
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_vector_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={"inverted_index_algo": "DAAT_MAXSCORE"},  # or "DAAT_WAND" or "TAAT_NAIVE"
        )
        
        db_client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)
        print("✓ 集合已加载到内存")
        
    except Exception as e:
        print(f"✗ Milvus集合创建失败: {e}")
        print("  提示：请确保Milvus服务已启动，并检查VECTOR_URL环境变量")
        raise


vector_url = settings.vector_url
vector_db = settings.vector_db
db_client = MilvusClient(vector_url)
# 初始化Milvus数据库
init_milvus_database(db_client, db_name=vector_db)

db_client.use_database(vector_db)

def main():
    """主函数"""
    print("=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)

    # 从环境变量读取向量维度，默认1024
    embedding_dim = int(settings.embedding_dim)
    print(f"向量维度: {embedding_dim}")
    
    # 初始化Milvus集合
    init_milvus_collection(embedding_dim=embedding_dim)
    print()
    
    print("=" * 50)
    print("✓ 数据库初始化完成")
    print("=" * 50)


if __name__ == "__main__":
    main()

