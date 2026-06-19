"""演示 KnowledgeBaseService 调用 vector_repository 的创建和执行原理。

运行方式：
    python demo_vector_repository_call.py

这个 demo 用一个单文件复刻项目里的调用链：
配置 -> 工厂函数 -> 依赖函数 -> Service 构造注入 -> Service 方法调用仓储方法。
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


class VectorRepository(Protocol):
    """向量仓储协议：Service 只要求依赖对象有这些方法。"""

    def delete_by_file_id(self, file_id: int) -> None:
        """按文件 ID 删除向量。"""
        ...


class MemoryVectorRepository:
    """内存版向量仓储，对应项目里的 MemoryVectorRepository。"""

    def delete_by_file_id(self, file_id: int) -> None:
        """模拟从内存中删除某个文件的向量。"""
        print(f"MemoryVectorRepository.delete_by_file_id 被执行，file_id={file_id}")


class MilvusVectorRepository:
    """Milvus 版向量仓储，对应项目里的 MilvusVectorRepository。"""

    def delete_by_file_id(self, file_id: int) -> None:
        """模拟从 Milvus 中删除某个文件的向量。"""
        print(f"MilvusVectorRepository.delete_by_file_id 被执行，file_id={file_id}")


@dataclass(frozen=True)
class Settings:
    """应用配置：真实项目里来自 .env 或环境变量。"""

    vector_backend: str


class KnowledgeBaseService:
    """业务服务：不自己创建仓储，只接收外部传进来的仓储。"""

    def __init__(self, vector_repository: VectorRepository) -> None:
        """把仓储对象保存到 self 上，后续业务方法直接调用它。"""
        self.vector_repository = vector_repository

    def delete_file_vectors(self, file_id: int) -> None:
        """模拟项目中的 _delete_file_vectors 方法。"""
        print("KnowledgeBaseService.delete_file_vectors 开始执行")
        self.vector_repository.delete_by_file_id(file_id)
        print("KnowledgeBaseService.delete_file_vectors 执行结束")


def create_vector_repository(backend: str) -> VectorRepository:
    """工厂函数：根据配置决定创建哪个具体仓储对象。"""
    print(f"create_vector_repository 收到 backend={backend}")
    if backend == "milvus":
        print("创建 MilvusVectorRepository 实例")
        return MilvusVectorRepository()
    print("创建 MemoryVectorRepository 实例")
    return MemoryVectorRepository()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """依赖函数：返回配置对象，并通过 lru_cache 保证只创建一次。"""
    print("get_settings 第一次执行，创建 Settings")
    return Settings(vector_backend="memory")


@lru_cache(maxsize=1)
def get_vector_repository() -> VectorRepository:
    """依赖函数：读取配置，并调用工厂函数创建向量仓储。"""
    print("get_vector_repository 第一次执行，准备创建向量仓储")
    settings = get_settings()
    return create_vector_repository(settings.vector_backend)


def get_knowledge_base_service() -> KnowledgeBaseService:
    """依赖函数：创建业务服务，并把向量仓储注入进去。"""
    print("get_knowledge_base_service 执行，准备创建业务服务")
    return KnowledgeBaseService(get_vector_repository())


def main() -> None:
    """演示完整调用流程。"""
    print("第一次获取 service，并删除 file_id=101 的向量")
    service = get_knowledge_base_service()
    service.delete_file_vectors(101)

    print("\n第二次获取 service，并删除 file_id=202 的向量")
    another_service = get_knowledge_base_service()
    another_service.delete_file_vectors(202)

    print("\n注意：get_vector_repository 第二次没有打印创建日志，因为 lru_cache 复用了同一个仓储实例")


if __name__ == "__main__":
    main()
