"""向量仓储基础类型。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RetrievalResult:
    """向量检索返回的一条候选知识片段。"""

    text: str  # 命中的知识库文本片段。
    score: float  # 向量相似度分数，数值越大表示越相关。
    metadata: dict[str, str]  # 文档 ID、文件名等附加信息。


@dataclass
class VectorDocument:
    """可写入向量库的知识文档。"""

    text: str  # chunk 原文，会在检索命中后放入 Prompt。
    vector: list[float]  # chunk 对应的 embedding 向量。
    metadata: dict[str, str]  # 文档 ID、文件名等来源信息。


@dataclass(frozen=True)
class VectorSearchFilter:
    """向量检索过滤条件。"""

    knowledge_base_ids: list[str] | None = None
    file_ids: list[str] | None = None
    file_statuses: list[str] | None = None


class VectorRepository(Protocol):
    """向量仓储协议。"""

    dimension: int

    def add_documents(self, documents: list[VectorDocument]) -> None:
        """批量写入知识文档。

        Args:
            documents: 待写入向量库的文档列表。
        """
        ...

    def search(
        self,
        vector: list[float],
        top_k: int,
        filters: VectorSearchFilter | None = None,
    ) -> list[RetrievalResult]:
        """按向量相似度检索知识文档。

        Args:
            vector: 用于检索或归一化的向量。
            top_k: 向量检索返回的候选数量。
            filters: 可选的知识库、文件和状态过滤条件。
        """
        ...

    def delete_by_file_id(self, file_id: int) -> None:
        """按知识库文件 ID 删除对应向量。

        Args:
            file_id: 知识库文件 ID。
        """
        ...

    def delete_by_vector_ids(self, vector_ids: list[str]) -> None:
        """按业务向量 ID 批量删除向量。"""
        ...
