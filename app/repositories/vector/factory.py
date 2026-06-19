"""向量仓储工厂。"""

from app.repositories.vector.base import VectorRepository
from app.repositories.vector.memory import MemoryVectorRepository
from app.repositories.vector.milvus import MilvusVectorRepository


def create_vector_repository(
    backend: str,
    dimension: int,
    milvus_uri: str,
    milvus_token: str | None,
    milvus_collection: str,
) -> VectorRepository:
    """根据配置创建向量仓储。

    Args:
        backend: 要使用的后端类型配置值。
        dimension: 向量维度。
        milvus_uri: Milvus 服务地址或本地 Lite 文件地址。
        milvus_token: Milvus 连接令牌配置值。
        milvus_collection: Milvus 集合名称配置值。
    """
    if backend == "milvus":
        return MilvusVectorRepository(milvus_uri, milvus_token, milvus_collection, dimension)
    if backend == "memory":
        return MemoryVectorRepository(dimension)
    raise ValueError(f"不支持的向量存储后端：{backend}")
