"""多知识库管理接口模块。"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError

from app.api.errors import run_with_service_errors, run_with_value_error
from app.api.mappers.knowledge_base import base_response, chunk_response, file_response, upload_response
from app.core.config import Settings
from app.core.response import success_response
from app.dependencies import (
    get_app_settings,
    get_current_user,
    get_knowledge_base_service,
    process_knowledge_file_background,
)
from app.rag.parser import SUPPORTED_EXTENSIONS
from app.schemas.knowledge_base import KnowledgeBaseCreateRequest
from app.services.knowledge_base_service import KnowledgeBaseService
from app.utils.files import save_supported_upload_file

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"], dependencies=[Depends(get_current_user)])


@router.post("")
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """创建知识库。

    Args:
        request: 当前接口接收的请求体或请求对象。
        service: 当前接口注入的业务服务实例。
    """
    try:
        record = service.create_base(request.name, request.description)
    except IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="知识库名称已存在") from error
    return success_response(data=base_response(record).model_dump(), message="知识库创建成功")


@router.get("")
async def list_knowledge_bases(service: KnowledgeBaseService = Depends(get_knowledge_base_service)) -> dict[str, Any]:
    """获取知识库列表。

    Args:
        service: 当前接口注入的业务服务实例。
    """
    records = service.list_bases()
    return success_response(data=[base_response(record).model_dump() for record in records], message="查询成功")


@router.post("/{knowledge_base_id}/files")
async def upload_knowledge_file(
    knowledge_base_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """上传文件到指定知识库，并在后台解析和生成向量。

    Args:
        knowledge_base_id: 知识库 ID。
        background_tasks: FastAPI 后台任务调度器。
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        f"knowledge-bases/{knowledge_base_id}",
        max_bytes=settings.max_upload_bytes,
    )
    file_record, chunk_count = run_with_service_errors(
        lambda: service.upload_file(knowledge_base_id, saved_path, original_name),
        status.HTTP_400_BAD_REQUEST,
    )
    background_tasks.add_task(
        process_knowledge_file_background,
        knowledge_base_id,
        file_record.id,
        original_name,
        saved_path,
    )
    return success_response(data=upload_response(file_record, chunk_count).model_dump(), message="文件上传成功，正在后台处理")


@router.get("/{knowledge_base_id}/files")
async def list_knowledge_files(
    knowledge_base_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """获取指定知识库下的文件列表。

    Args:
        knowledge_base_id: 知识库 ID。
        service: 当前接口注入的业务服务实例。
    """
    records = run_with_value_error(
        lambda: service.list_files(knowledge_base_id),
        status.HTTP_404_NOT_FOUND,
    )
    return success_response(
        data=[file_response(file_record, chunk_count).model_dump() for file_record, chunk_count in records],
        message="查询成功",
    )


@router.delete("/{knowledge_base_id}/files/{file_id}")
async def delete_knowledge_file(
    knowledge_base_id: int,
    file_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """删除知识库文件，同时删除 MySQL chunk 和对应向量。

    Args:
        knowledge_base_id: 知识库 ID。
        file_id: 知识库文件 ID。
        service: 当前接口注入的业务服务实例。
    """
    run_with_value_error(
        lambda: service.delete_file(knowledge_base_id, file_id),
        status.HTTP_404_NOT_FOUND,
    )
    return success_response(data={"id": file_id}, message="文件删除成功")


@router.put("/{knowledge_base_id}/files/{file_id}")
async def reupload_knowledge_file(
    knowledge_base_id: int,
    file_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """重新上传知识库文件，并在后台解析和生成向量。

    Args:
        knowledge_base_id: 知识库 ID。
        file_id: 知识库文件 ID。
        background_tasks: FastAPI 后台任务调度器。
        file: 前端上传的文件对象。
        settings: 应用配置对象。
        service: 当前接口注入的业务服务实例。
    """
    saved_path, original_name = await save_supported_upload_file(
        file,
        settings.upload_dir,
        SUPPORTED_EXTENSIONS,
        f"knowledge-bases/{knowledge_base_id}",
        max_bytes=settings.max_upload_bytes,
    )
    file_record, chunk_count = run_with_service_errors(
        lambda: service.reupload_file(knowledge_base_id, file_id, saved_path, original_name),
        status.HTTP_404_NOT_FOUND,
    )
    background_tasks.add_task(
        process_knowledge_file_background,
        knowledge_base_id,
        file_id,
        original_name,
        saved_path,
    )
    return success_response(
        data=upload_response(file_record, chunk_count).model_dump(),
        message="文件重新上传成功，正在后台处理",
    )


@router.get("/{knowledge_base_id}/files/{file_id}/chunks")
async def list_knowledge_file_chunks(
    knowledge_base_id: int,
    file_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """查看指定知识库文件下的 Chunk 列表。

    Args:
        knowledge_base_id: 知识库 ID。
        file_id: 知识库文件 ID。
        service: 当前接口注入的业务服务实例。
    """
    chunks = run_with_value_error(
        lambda: service.list_chunks(knowledge_base_id, file_id),
        status.HTTP_404_NOT_FOUND,
    )
    return success_response(data=[chunk_response(chunk).model_dump() for chunk in chunks], message="查询成功")


@router.post("/{knowledge_base_id}/files/{file_id}/reparse")
async def reparse_knowledge_file(
    knowledge_base_id: int,
    file_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """重新解析已上传文件，并重建 Chunk 和向量。

    Args:
        knowledge_base_id: 知识库 ID。
        file_id: 知识库文件 ID。
        service: 当前接口注入的业务服务实例。
    """
    chunk_count = run_with_service_errors(
        lambda: service.reparse_file(knowledge_base_id, file_id),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data={"id": file_id, "chunk_count": chunk_count}, message="重新解析成功")


@router.post("/{knowledge_base_id}/files/{file_id}/re-embedding")
async def reembedding_knowledge_file(
    knowledge_base_id: int,
    file_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    """基于现有 Chunk 文本重新生成 embedding 并替换向量。

    Args:
        knowledge_base_id: 知识库 ID。
        file_id: 知识库文件 ID。
        service: 当前接口注入的业务服务实例。
    """
    chunk_count = run_with_service_errors(
        lambda: service.reembed_file(knowledge_base_id, file_id),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data={"id": file_id, "chunk_count": chunk_count}, message="重新 embedding 成功")
