"""多知识库管理服务。"""

import logging
from pathlib import Path
from uuid import uuid4

from app.rag.embedding import HashEmbedding
from app.rag.ingestion import parse_file_chunks
from app.repositories.mysql.records import KnowledgeBaseRecord, KnowledgeChunkRecord, KnowledgeFileRecord
from app.repositories.mysql_repository import MySQLRepository
from app.repositories.vector import VectorDocument, VectorRepository


logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """负责知识库、文件、切块和向量写入删除的简单业务编排。"""

    def __init__(
        self,
        mysql_repository: MySQLRepository,
        vector_repository: VectorRepository,
        embedding: HashEmbedding,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """初始化知识库管理服务依赖。

        Args:
            mysql_repository: MySQL 数据仓储。
            vector_repository: 向量仓储，支持 Milvus 或内存模式。
            embedding: embedding 生成器。
            chunk_size: 文本切块最大字符数。
            chunk_overlap: 长文本切块重叠字符数。
        """
        self.mysql_repository = mysql_repository
        self.vector_repository = vector_repository
        self.embedding = embedding
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_base(self, name: str, description: str | None) -> KnowledgeBaseRecord:
        """创建一个知识库。

        Args:
            name: 知识库名称。
            description: 知识库描述，可为空。
        """
        return self.mysql_repository.create_knowledge_base(name.strip(), description.strip() if description else None)

    def list_bases(self) -> list[KnowledgeBaseRecord]:
        """查询全部知识库。"""
        return self.mysql_repository.list_knowledge_bases()

    def upload_file(
        self,
        knowledge_base_id: int,
        saved_path: Path,
        original_name: str,
    ) -> tuple[KnowledgeFileRecord, int]:
        """上传文件到指定知识库，并创建待处理文件记录。

        Args:
            knowledge_base_id: 目标知识库 ID。
            saved_path: 上传文件保存后的本地路径。
            original_name: 用户上传时的原始文件名。
        """
        self._require_base(knowledge_base_id)
        file_record = self.mysql_repository.create_knowledge_file(
            knowledge_base_id,
            original_name,
            str(saved_path),
            "processing",
        )
        self.mysql_repository.commit()
        return file_record, 0

    def process_uploaded_file(
        self,
        knowledge_base_id: int,
        file_id: int,
        original_name: str,
        saved_path: Path,
    ) -> None:
        """后台解析上传文件并生成向量，完成后更新文件状态。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 待处理的知识库文件 ID。
            original_name: 用户上传时的原始文件名。
            saved_path: 上传文件保存后的本地路径。
        """
        had_existing_chunks = bool(self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id))
        try:
            self._replace_file_vectors(knowledge_base_id, file_id, original_name, saved_path)
        except Exception:
            logger.exception("知识库文件后台处理失败：knowledge_base_id=%s file_id=%s path=%s", knowledge_base_id, file_id, saved_path)
            self.mysql_repository.rollback()
            if not had_existing_chunks:
                self._mark_file_failed(knowledge_base_id, file_id, original_name, str(saved_path))
            return
        self._mark_file_active(knowledge_base_id, file_id, original_name, str(saved_path))

    def list_files(self, knowledge_base_id: int) -> list[tuple[KnowledgeFileRecord, int]]:
        """查询知识库文件列表，并附带每个文件的切块数量。

        Args:
            knowledge_base_id: 要查询的知识库 ID。
        """
        self._require_base(knowledge_base_id)
        files = self.mysql_repository.list_knowledge_files(knowledge_base_id)
        chunk_counts = self.mysql_repository.count_knowledge_chunks_by_file_ids(
            knowledge_base_id,
            [file_record.id for file_record in files],
        )
        return [(file_record, chunk_counts.get(file_record.id, 0)) for file_record in files]

    def list_chunks(self, knowledge_base_id: int, file_id: int) -> list[KnowledgeChunkRecord]:
        """查询某个知识库文件下的全部切块。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要查询切块的文件 ID。
        """
        self._require_file(knowledge_base_id, file_id)
        return self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id)

    def delete_file(self, knowledge_base_id: int, file_id: int) -> None:
        """删除知识库文件、对应 MySQL chunk 和向量库向量。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要删除的文件 ID。
        """
        file_record = self._require_file(knowledge_base_id, file_id)
        self._delete_file_vectors(knowledge_base_id, file_id)
        self.mysql_repository.mark_knowledge_file_deleted(knowledge_base_id, file_id)
        self._delete_local_file(file_record.file_path)

    def reupload_file(
        self,
        knowledge_base_id: int,
        file_id: int,
        saved_path: Path,
        original_name: str,
    ) -> tuple[KnowledgeFileRecord, int]:
        """重新上传知识库文件，后台成功处理新文件后再替换旧数据。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要替换的文件 ID。
            saved_path: 新上传文件保存后的本地路径。
            original_name: 新上传文件的原始文件名。
        """
        file_record = self._require_file(knowledge_base_id, file_id)
        chunk_count = len(self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id))
        return file_record, chunk_count

    def reparse_file(self, knowledge_base_id: int, file_id: int) -> int:
        """重新解析已保存的原始文件，并重建 chunk 和向量。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要重新解析的文件 ID。
        """
        file_record = self._require_file(knowledge_base_id, file_id)
        saved_path = Path(file_record.file_path)
        if not saved_path.exists():
            raise ValueError("原始文件不存在，请重新上传文件")

        chunks = parse_file_chunks(saved_path, self.chunk_size, self.chunk_overlap)

        return self._write_chunks_or_mark_failed(
            knowledge_base_id,
            file_id,
            file_record.filename,
            file_record.file_path,
            chunks,
        )

    def reembed_file(self, knowledge_base_id: int, file_id: int) -> int:
        """基于现有 MySQL chunk 文本重新生成 embedding 并替换向量。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要重新生成向量的文件 ID。
        """
        file_record = self._require_file(knowledge_base_id, file_id)
        current_chunks = self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id)
        if not current_chunks:
            raise ValueError("当前文件没有可重新 embedding 的 chunk，请先重新解析或重新上传")

        chunks = [item.content for item in current_chunks]
        return self._write_chunks_or_mark_failed(
            knowledge_base_id,
            file_id,
            file_record.filename,
            file_record.file_path,
            chunks,
        )

    def _replace_file_vectors(self, knowledge_base_id: int, file_id: int, original_name: str, saved_path: Path) -> int:
        """解析文件并重新写入该文件的全部 chunk 和向量。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要替换向量的文件 ID。
            original_name: 文件原始名称，用于向量元数据。
            saved_path: 待解析文件的本地路径。
        """
        chunks = parse_file_chunks(saved_path, self.chunk_size, self.chunk_overlap)
        return self._write_chunks_and_vectors(knowledge_base_id, file_id, original_name, chunks)

    def _write_chunks_or_mark_failed(
        self,
        knowledge_base_id: int,
        file_id: int,
        filename: str,
        file_path: str,
        chunks: list[str],
    ) -> int:
        """写入 chunk 和向量，失败时标记文件状态。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要写入切块和向量的文件 ID。
            filename: 文件名，用于状态更新和向量元数据。
            file_path: 文件本地路径，用于失败状态更新。
            chunks: 已解析或已读取的文本切块列表。
        """
        had_existing_chunks = bool(self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id))
        try:
            return self._write_chunks_and_vectors(knowledge_base_id, file_id, filename, chunks)
        except Exception:
            logger.exception("重建知识库向量失败：knowledge_base_id=%s file_id=%s", knowledge_base_id, file_id)
            self.mysql_repository.rollback()
            if not had_existing_chunks:
                self._mark_file_failed(knowledge_base_id, file_id, filename, file_path)
            raise

    def _write_chunks_and_vectors(
        self,
        knowledge_base_id: int,
        file_id: int,
        original_name: str,
        chunks: list[str],
    ) -> int:
        """将已切好的文本块写入向量库和 MySQL chunk 表。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要写入切块和向量的文件 ID。
            original_name: 文件原始名称，用于向量元数据。
            chunks: 待写入的文本切块列表。
        """
        old_vector_ids = [chunk.vector_id for chunk in self.mysql_repository.list_knowledge_chunks(knowledge_base_id, file_id)]
        vectors = self.embedding.embed_many(chunks)
        chunk_rows, vector_documents = self._build_chunk_payloads(
            knowledge_base_id,
            file_id,
            original_name,
            chunks,
            vectors,
        )
        new_vector_ids = [document.metadata["vector_id"] for document in vector_documents]

        self.vector_repository.add_documents(vector_documents)
        try:
            self.mysql_repository.delete_knowledge_chunks(knowledge_base_id, file_id)
            self.mysql_repository.add_knowledge_chunks(knowledge_base_id, file_id, chunk_rows)
            self.mysql_repository.commit()
        except Exception:
            try:
                self.vector_repository.delete_by_vector_ids(new_vector_ids)
            except Exception:
                logger.exception("清理新写入向量失败：file_id=%s", file_id)
            raise

        if old_vector_ids:
            try:
                self.vector_repository.delete_by_vector_ids(old_vector_ids)
            except Exception:
                logger.exception("清理旧向量失败：file_id=%s", file_id)
        return len(chunks)

    def _build_chunk_payloads(
        self,
        knowledge_base_id: int,
        file_id: int,
        original_name: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> tuple[list[tuple[int, str, str]], list[VectorDocument]]:
        """构建 MySQL chunk 行和向量库文档载荷。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 当前切块所属文件 ID。
            original_name: 文件原始名称，用于向量元数据。
            chunks: 文本切块列表。
            vectors: 与文本切块一一对应的 embedding 向量列表。
        """
        document_id = uuid4().hex
        chunk_rows: list[tuple[int, str, str]] = []
        vector_documents: list[VectorDocument] = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
            vector_id = uuid4().hex
            chunk_rows.append((index, chunk, vector_id))
            vector_documents.append(
                VectorDocument(
                    text=chunk,
                    vector=vector,
                    metadata={
                        "document_id": document_id,
                        "file_name": original_name,
                        "knowledge_base_id": str(knowledge_base_id),
                        "file_id": str(file_id),
                        "file_status": "active",
                        "vector_id": vector_id,
                    },
                )
            )
        return chunk_rows, vector_documents

    def _mark_file_failed(self, knowledge_base_id: int, file_id: int, filename: str, file_path: str) -> None:
        """将知识库文件状态标记为失败。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要更新状态的文件 ID。
            filename: 文件名，用于保留文件记录信息。
            file_path: 文件本地路径，用于保留文件记录信息。
        """
        self.mysql_repository.update_knowledge_file(
            knowledge_base_id,
            file_id,
            filename,
            file_path,
            "failed",
        )

    def _mark_file_active(self, knowledge_base_id: int, file_id: int, filename: str, file_path: str) -> None:
        """将知识库文件状态标记为可用。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要更新状态的文件 ID。
            filename: 文件名，用于保留文件记录信息。
            file_path: 文件本地路径，用于保留文件记录信息。
        """
        self.mysql_repository.update_knowledge_file(
            knowledge_base_id,
            file_id,
            filename,
            file_path,
            "active",
        )

    def _delete_file_vectors(self, knowledge_base_id: int, file_id: int) -> None:
        """删除某个文件的向量库向量和 MySQL chunk。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要删除向量和切块的文件 ID。
        """
        self.vector_repository.delete_by_file_id(file_id)
        self.mysql_repository.delete_knowledge_chunks(knowledge_base_id, file_id)

    def _require_base(self, knowledge_base_id: int) -> KnowledgeBaseRecord:
        """获取知识库，不存在时抛出业务错误。

        Args:
            knowledge_base_id: 要校验并获取的知识库 ID。
        """
        knowledge_base = self.mysql_repository.get_knowledge_base(knowledge_base_id)
        if not knowledge_base:
            raise ValueError("知识库不存在")
        return knowledge_base

    def _require_file(self, knowledge_base_id: int, file_id: int) -> KnowledgeFileRecord:
        """获取知识库文件，不存在时抛出业务错误。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 要校验并获取的文件 ID。
        """
        self._require_base(knowledge_base_id)
        file_record = self.mysql_repository.get_knowledge_file(knowledge_base_id, file_id)
        if not file_record:
            raise ValueError("文件不存在")
        return file_record

    def _delete_local_file(self, file_path: str) -> None:
        """删除本地文件，文件不存在或删除失败时不影响主流程。

        Args:
            file_path: 要删除的本地文件路径。
        """
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("删除本地上传文件失败：path=%s", file_path, exc_info=True)
