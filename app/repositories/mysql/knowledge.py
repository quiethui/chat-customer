"""知识库 ORM 数据访问方法。"""

from sqlalchemy import delete, func, select, update

from app.models import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_knowledge_base, map_knowledge_chunk, map_knowledge_file
from app.repositories.mysql.records import KnowledgeBaseRecord, KnowledgeChunkRecord, KnowledgeFileRecord


class KnowledgeMySQLMixin(BaseMySQLMixin):
    """封装知识库、文件和切块相关 MySQL 操作。"""

    def create_knowledge_base(self, name: str, description: str | None = None) -> KnowledgeBaseRecord:
        """创建知识库。

        Args:
            name: 知识库名称。
            description: 知识库描述。
        """
        knowledge_base = KnowledgeBase(name=name, description=description)
        self._add(knowledge_base)
        self._flush()
        self._refresh(knowledge_base)
        return map_knowledge_base(knowledge_base)

    def list_knowledge_bases(self) -> list[KnowledgeBaseRecord]:
        """查询全部知识库。"""
        rows = self._scalars(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc(), KnowledgeBase.id.desc())
        )
        return [map_knowledge_base(row) for row in rows]

    def get_knowledge_base(self, knowledge_base_id: int) -> KnowledgeBaseRecord | None:
        """按 ID 查询知识库。

        Args:
            knowledge_base_id: 知识库 ID。
        """
        knowledge_base = self._scalar_one_or_none(
            select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id).limit(1)
        )
        return map_knowledge_base(knowledge_base) if knowledge_base else None

    def create_knowledge_file(
        self,
        knowledge_base_id: int,
        filename: str,
        file_path: str,
        status: str = "active",
    ) -> KnowledgeFileRecord:
        """创建知识库文件记录。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            filename: 用户上传的原始文件名。
            file_path: 文件保存路径。
            status: 文件处理状态。
        """
        file_record = KnowledgeFile(
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            file_path=file_path,
            status=status,
        )
        self._add(file_record)
        self._flush()
        self._refresh(file_record)
        return map_knowledge_file(file_record)

    def get_knowledge_file(self, knowledge_base_id: int, file_id: int) -> KnowledgeFileRecord | None:
        """按知识库 ID 和文件 ID 查询未删除文件。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 知识库文件 ID。
        """
        file_record = self._scalar_one_or_none(
            select(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.knowledge_base_id == knowledge_base_id,
                KnowledgeFile.status != "deleted",
            )
            .limit(1)
        )
        return map_knowledge_file(file_record) if file_record else None

    def list_knowledge_files(self, knowledge_base_id: int) -> list[KnowledgeFileRecord]:
        """查询某个知识库下所有未删除文件。

        Args:
            knowledge_base_id: 知识库 ID。
        """
        rows = self._scalars(
            select(KnowledgeFile)
            .where(KnowledgeFile.knowledge_base_id == knowledge_base_id, KnowledgeFile.status != "deleted")
            .order_by(KnowledgeFile.created_at.desc(), KnowledgeFile.id.desc())
        )
        return [map_knowledge_file(row) for row in rows]

    def update_knowledge_file(
        self,
        knowledge_base_id: int,
        file_id: int,
        filename: str,
        file_path: str,
        status: str = "active",
    ) -> KnowledgeFileRecord | None:
        """更新知识库文件的名称、路径和状态。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 知识库文件 ID。
            filename: 新文件名。
            file_path: 新文件保存路径。
            status: 新文件状态。
        """
        file_record = self._scalar_one_or_none(
            select(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.knowledge_base_id == knowledge_base_id,
                KnowledgeFile.status != "deleted",
            )
            .limit(1)
        )
        if not file_record:
            return None
        file_record.filename = filename
        file_record.file_path = file_path
        file_record.status = status
        self._flush()
        self._refresh(file_record)
        return map_knowledge_file(file_record)

    def mark_knowledge_file_deleted(self, knowledge_base_id: int, file_id: int) -> None:
        """将知识库文件标记为已删除。

        Args:
            knowledge_base_id: 文件所属知识库 ID。
            file_id: 知识库文件 ID。
        """
        self._execute(
            update(KnowledgeFile)
            .where(KnowledgeFile.id == file_id, KnowledgeFile.knowledge_base_id == knowledge_base_id)
            .values(status="deleted")
        )

    def add_knowledge_chunks(
        self,
        knowledge_base_id: int,
        file_id: int,
        chunks: list[tuple[int, str, str]],
    ) -> list[KnowledgeChunkRecord]:
        """批量新增知识库文件切块。

        Args:
            knowledge_base_id: 切块所属知识库 ID。
            file_id: 切块所属文件 ID。
            chunks: 切块数据列表，每项为 chunk_index、content、vector_id。
        """
        if not chunks:
            return []
        self._add_all(
            KnowledgeChunk(
                knowledge_base_id=knowledge_base_id,
                file_id=file_id,
                chunk_index=chunk_index,
                content=content,
                vector_id=vector_id,
            )
            for chunk_index, content, vector_id in chunks
        )
        self._flush()
        rows = self._scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id, KnowledgeChunk.file_id == file_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return [map_knowledge_chunk(row) for row in rows]

    def list_knowledge_chunks(self, knowledge_base_id: int, file_id: int) -> list[KnowledgeChunkRecord]:
        """查询某个知识库文件下的全部切块。

        Args:
            knowledge_base_id: 切块所属知识库 ID。
            file_id: 切块所属文件 ID。
        """
        rows = self._scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id, KnowledgeChunk.file_id == file_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return [map_knowledge_chunk(row) for row in rows]

    def count_knowledge_chunks_by_file_ids(self, knowledge_base_id: int, file_ids: list[int]) -> dict[int, int]:
        """批量统计知识库文件的切块数量。

        Args:
            knowledge_base_id: 知识库 ID。
            file_ids: 需要统计切块数量的文件 ID 列表。
        """
        if not file_ids:
            return {}
        rows = self._all(
            select(KnowledgeChunk.file_id, func.count(KnowledgeChunk.id))
            .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id, KnowledgeChunk.file_id.in_(file_ids))
            .group_by(KnowledgeChunk.file_id)
        )
        return {int(file_id): int(chunk_count) for file_id, chunk_count in rows}

    def delete_knowledge_chunks(self, knowledge_base_id: int, file_id: int) -> None:
        """删除某个知识库文件下的全部切块。

        Args:
            knowledge_base_id: 切块所属知识库 ID。
            file_id: 切块所属文件 ID。
        """
        self._execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.knowledge_base_id == knowledge_base_id,
                KnowledgeChunk.file_id == file_id,
            )
        )
