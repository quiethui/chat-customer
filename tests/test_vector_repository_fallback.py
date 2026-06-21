"""测试向量仓储依赖注入的降级逻辑。"""

from unittest.mock import patch

from app.dependencies import get_vector_repository
from app.repositories.vector.memory import MemoryVectorRepository


def test_get_vector_repository_falls_back_to_memory_on_error() -> None:
    """向量数据库连接失败时降级到内存空实现。"""
    # 模拟 create_vector_repository 抛出连接异常
    with patch("app.dependencies.create_vector_repository") as mock_create:
        mock_create.side_effect = RuntimeError("Milvus 连接失败")

        # 清理缓存，确保测试独立
        get_vector_repository.cache_clear()

        repository = get_vector_repository()

        # 应该降级到内存实现
        assert isinstance(repository, MemoryVectorRepository)
        # 内存实现查询空数据时返回空列表（使用实际的向量维度 384）
        results = repository.search([0.0] * 384, top_k=5)
        assert results == []
