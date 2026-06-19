"""知识库导入服务。"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.rag.embedding import HashEmbedding
from app.rag.ingestion import parse_file_chunks
from app.repositories.vector import VectorDocument, VectorRepository


@dataclass
class IngestResult:
    """知识库文件导入完成后的服务层结果。"""

    file_name: str  # 用户上传的原始文件名。
    document_id: str  # 本次导入生成的文档唯一 ID。
    chunk_count: int  # 写入向量库的 chunk 数量。


@dataclass
class ChunkPreviewResult:
    """知识库文档切块预览结果。"""

    file_name: str  # 用户上传的原始文件名。
    chunks: list[str]  # 文档解析后的文本切块列表。


@dataclass
class VectorPreviewResult:
    """知识库文档切块和向量预览结果。"""

    file_name: str  # 用户上传的原始文件名。
    chunks: list[str]  # 文档解析后的文本切块列表。
    vectors: list[list[float]]  # 与 chunks 一一对应的 embedding 向量列表。
    embedding_dimension: int  # 当前 embedding 模型输出向量维度。


@dataclass
class DetailedIngestResult(VectorPreviewResult):
    """知识库文件导入并返回切块和向量明细的结果。"""

    document_id: str  # 本次导入生成的文档唯一 ID。


class KnowledgeService:
    """负责文档解析、切块、向量化和写入向量库的知识库服务。"""

    def __init__(
        self,
        embedding: HashEmbedding,
        repository: VectorRepository,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """初始化知识库导入依赖和切块参数。

        Args:
            embedding: 文本向量化服务实例。
            repository: 当前服务使用的数据仓储实例。
            chunk_size: 单个文本切块的最大字符数。
            chunk_overlap: 相邻文本切块之间的重叠字符数。
        """
        self.embedding = embedding
        self.repository = repository
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def ingest_file(self, path: Path, original_name: str) -> IngestResult:
        """导入单个上传文件，并返回导入统计信息。

        Args:
            path: 目标文件路径或请求路径。
            original_name: 用户上传文件的原始文件名。
        """
        chunks = self._parse_chunks(path)
        document_id = uuid4().hex
        vectors = self.embedding.embed_many(chunks)
        # 每个 chunk 和对应向量一一写入，metadata 用于后续引用来源追踪。
        self._save_vectors(original_name, document_id, chunks, vectors)
        return IngestResult(file_name=original_name, document_id=document_id, chunk_count=len(chunks))

    async def preview_chunks(self, path: Path, original_name: str) -> ChunkPreviewResult:
        """解析上传文件并直接返回文本切块，不写入向量库。

        Args:
            path: 已保存到本地的上传文件路径。
            original_name: 用户上传时的原始文件名。

        Returns:
            包含原始文件名和文本切块列表的预览结果。
        """
        chunks = self._parse_chunks(path)
        return ChunkPreviewResult(file_name=original_name, chunks=chunks)

    async def preview_vectors(self, path: Path, original_name: str) -> VectorPreviewResult:
        """解析上传文件并直接返回文本切块和向量，不写入向量库。

        Args:
            path: 已保存到本地的上传文件路径。
            original_name: 用户上传时的原始文件名。

        Returns:
            包含切块文本、向量值和向量维度的预览结果。
        """
        chunks = self._parse_chunks(path)
        vectors = self.embedding.embed_many(chunks)
        return VectorPreviewResult(
            file_name=original_name,
            chunks=chunks,
            vectors=vectors,
            embedding_dimension=self.embedding.dimension,
        )

    async def ingest_file_with_vectors(self, path: Path, original_name: str) -> DetailedIngestResult:
        """导入上传文件，并返回写入向量库的切块和向量明细。

        Args:
            path: 已保存到本地的上传文件路径。
            original_name: 用户上传时的原始文件名。

        Returns:
            包含文档 ID、切块、向量值和向量维度的导入明细。
        """
        chunks = self._parse_chunks(path)
        document_id = uuid4().hex
        vectors = self.embedding.embed_many(chunks)
        self._save_vectors(original_name, document_id, chunks, vectors)
        return DetailedIngestResult(
            file_name=original_name,
            chunks=chunks,
            vectors=vectors,
            embedding_dimension=self.embedding.dimension,
            document_id=document_id,
        )

    def _parse_chunks(self, path: Path) -> list[str]:
        """解析文档并按当前配置切块。

        Args:
            path: 已保存到本地的上传文件路径。

        Returns:
            非空文本切块列表。

        Raises:
            ValueError: 文档没有可导入内容时抛出。
        """
        return parse_file_chunks(path, self.chunk_size, self.chunk_overlap)

    def _save_vectors(self, original_name: str, document_id: str, chunks: list[str], vectors: list[list[float]]) -> None:
        """将切块和向量写入向量库。

        Args:
            original_name: 用户上传时的原始文件名，用于后续展示引用来源。
            document_id: 本次导入生成的文档唯一 ID。
            chunks: 文档切块文本列表。
            vectors: 与 chunks 一一对应的 embedding 向量列表。
        """
        self.repository.add_documents(
            [
                VectorDocument(
                    text=chunk,
                    vector=vector,
                    metadata={"document_id": document_id, "file_name": original_name},
                )
                for chunk, vector in zip(chunks, vectors)
            ],
        )
