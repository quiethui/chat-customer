"""知识库 API 响应转换函数。"""

from app.repositories.mysql_records import KnowledgeBaseRecord, KnowledgeChunkRecord, KnowledgeFileRecord
from app.schemas.knowledge_base import (
    KnowledgeBaseResponse,
    KnowledgeChunkResponse,
    KnowledgeFileResponse,
    KnowledgeFileUploadResponse,
)


def base_response(record: KnowledgeBaseRecord) -> KnowledgeBaseResponse:
    """转换知识库记录为接口响应。

    Args:
        record: 待转换为响应模型的数据记录。
    """
    return KnowledgeBaseResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        created_at=record.created_at,
    )


def file_response(record: KnowledgeFileRecord, chunk_count: int) -> KnowledgeFileResponse:
    """转换知识库文件记录为接口响应。

    Args:
        record: 待转换为响应模型的数据记录。
        chunk_count: 文件已生成的文本切块数量。
    """
    return KnowledgeFileResponse(
        id=record.id,
        knowledge_base_id=record.knowledge_base_id,
        filename=record.filename,
        file_path=record.file_path,
        status=record.status,
        chunk_count=chunk_count,
        created_at=record.created_at,
    )


def upload_response(record: KnowledgeFileRecord, chunk_count: int) -> KnowledgeFileUploadResponse:
    """转换上传结果为接口响应。

    Args:
        record: 待转换为响应模型的数据记录。
        chunk_count: 文件已生成的文本切块数量。
    """
    return KnowledgeFileUploadResponse(file=file_response(record, chunk_count), chunk_count=chunk_count)


def chunk_response(record: KnowledgeChunkRecord) -> KnowledgeChunkResponse:
    """转换知识库 Chunk 记录为接口响应。

    Args:
        record: 待转换为响应模型的数据记录。
    """
    return KnowledgeChunkResponse(
        id=record.id,
        knowledge_base_id=record.knowledge_base_id,
        file_id=record.file_id,
        chunk_index=record.chunk_index,
        content=record.content,
        char_count=len(record.content),
        vector_id=record.vector_id,
        created_at=record.created_at,
    )
