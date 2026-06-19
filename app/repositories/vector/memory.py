"""内存向量仓储实现。"""

from app.repositories.vector.base import RetrievalResult, VectorDocument, VectorSearchFilter


class MemoryVectorRepository:
    """进程内向量仓储。"""

    def __init__(self, dimension: int) -> None:
        """初始化内存向量仓储。

        Args:
            dimension: 向量维度。
        """
        self.dimension = dimension
        self._documents: list[VectorDocument] = []

    def add_documents(self, documents: list[VectorDocument]) -> None:
        """批量写入知识文档到内存。

        Args:
            documents: 待写入向量库的文档列表。
        """
        for document in documents:
            _ensure_dimension(document.vector, self.dimension)
        self._documents.extend(documents)

    def search(
        self,
        vector: list[float],
        top_k: int,
        filters: VectorSearchFilter | None = None,
    ) -> list[RetrievalResult]:
        """在内存中检索最相似的知识文档。

        Args:
            vector: 用于检索或归一化的向量。
            top_k: 向量检索返回的候选数量。
        """
        _ensure_dimension(vector, self.dimension)
        documents = [document for document in self._documents if _matches_filters(document.metadata, filters)]
        scored = [
            RetrievalResult(
                text=document.text,
                score=_cosine_similarity(vector, document.vector),
                metadata=document.metadata,
            )
            for document in documents
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def delete_by_file_id(self, file_id: int) -> None:
        """从内存向量库删除某个知识库文件的所有向量。

        Args:
            file_id: 知识库文件 ID。
        """
        target_file_id = str(file_id)
        self._documents = [
            document for document in self._documents if document.metadata.get("file_id") != target_file_id
        ]

    def delete_by_vector_ids(self, vector_ids: list[str]) -> None:
        """从内存向量库删除指定业务向量 ID。"""
        target_ids = set(vector_ids)
        if not target_ids:
            return
        self._documents = [
            document for document in self._documents if document.metadata.get("vector_id") not in target_ids
        ]


def _matches_filters(metadata: dict[str, str], filters: VectorSearchFilter | None) -> bool:
    if filters is None:
        return True
    if filters.knowledge_base_ids and metadata.get("knowledge_base_id") not in set(filters.knowledge_base_ids):
        return False
    if filters.file_ids and metadata.get("file_id") not in set(filters.file_ids):
        return False
    if filters.file_statuses and metadata.get("file_status") not in set(filters.file_statuses):
        return False
    return True


def _ensure_dimension(vector: list[float], dimension: int) -> None:
    if len(vector) != dimension:
        raise ValueError(f"向量维度不匹配：期望 {dimension}，实际 {len(vector)}")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个已归一化向量的点积相似度。

    Args:
        left: 参与余弦相似度计算的左侧向量。
        right: 参与余弦相似度计算的右侧向量。
    """
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))
