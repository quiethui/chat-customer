"""知识库上传接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.errors import async_run_with_service_errors, async_run_with_value_error
from app.core.config import Settings
from app.core.response import success_response
from app.dependencies import get_app_settings, get_knowledge_service
from app.rag.parser import SUPPORTED_EXTENSIONS
from app.schemas.upload import ChunkItem, UploadChunksResponse, UploadResponse, UploadVectorsResponse, VectorChunkItem
from app.services.knowledge_service import KnowledgeService
from app.utils.files import save_supported_upload_file

router = APIRouter(tags=["knowledge"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    """接收知识库文件，保存到本地后解析并写入向量库。

    Args:
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        max_bytes=settings.max_upload_bytes,
    )
    result = await async_run_with_service_errors(
        lambda: service.ingest_file(saved_path, original_name),
        status.HTTP_400_BAD_REQUEST,
    )

    response = UploadResponse(
        file_name=result.file_name,
        document_id=result.document_id,
        chunk_count=result.chunk_count,
    )
    return success_response(data=response.model_dump(), message="上传成功")


@router.post("/upload/chunks")
async def upload_document_chunks(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    """接收知识库文件，直接返回解析后的文本切块，不写入向量库。

    Args:
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        max_bytes=settings.max_upload_bytes,
    )
    result = await async_run_with_value_error(
        lambda: service.preview_chunks(saved_path, original_name),
        status.HTTP_400_BAD_REQUEST,
    )

    chunks = [
        ChunkItem(index=index, content=chunk, char_count=len(chunk))
        for index, chunk in enumerate(result.chunks, start=1)
    ]
    response = UploadChunksResponse(file_name=result.file_name, chunk_count=len(chunks), chunks=chunks)
    return success_response(data=response.model_dump(), message="切块预览成功")


@router.post("/upload/vectors")
async def upload_document_vectors(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    """接收知识库文件，直接返回文本切块和向量值，不写入向量库。

    Args:
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        max_bytes=settings.max_upload_bytes,
    )
    result = await async_run_with_value_error(
        lambda: service.preview_vectors(saved_path, original_name),
        status.HTTP_400_BAD_REQUEST,
    )

    response = UploadVectorsResponse(
        file_name=result.file_name,
        document_id=None,
        chunk_count=len(result.chunks),
        embedding_dimension=result.embedding_dimension,
        chunks=_build_vector_chunk_items(result.chunks, result.vectors),
    )
    return success_response(data=response.model_dump(), message="向量预览成功")


@router.post("/upload/with-vectors")
async def upload_document_with_vectors(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    """接收知识库文件，写入向量库后返回文本切块和向量值。

    Args:
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        max_bytes=settings.max_upload_bytes,
    )
    result = await async_run_with_service_errors(
        lambda: service.ingest_file_with_vectors(saved_path, original_name),
        status.HTTP_400_BAD_REQUEST,
    )

    response = UploadVectorsResponse(
        file_name=result.file_name,
        document_id=result.document_id,
        chunk_count=len(result.chunks),
        embedding_dimension=result.embedding_dimension,
        chunks=_build_vector_chunk_items(result.chunks, result.vectors),
    )
    return success_response(data=response.model_dump(), message="上传成功，已返回切块和向量")


def _build_vector_chunk_items(chunks: list[str], vectors: list[list[float]]) -> list[VectorChunkItem]:
    """把切块和向量组装为接口响应对象。

    Args:
        chunks: 文档切块文本列表。
        vectors: 与 chunks 一一对应的 embedding 向量列表。

    Returns:
        包含序号、文本、字符数和向量值的响应对象列表。
    """
    return [
        VectorChunkItem(index=index, content=chunk, char_count=len(chunk), vector=vector)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1)
    ]
