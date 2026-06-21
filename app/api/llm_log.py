"""大模型请求日志接口模块（仅管理员可访问）。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.response import success_response
from app.dependencies import get_current_admin_manager, get_llm_log_service
from app.repositories.mysql.records import LLMRequestLogRecord, ManagerRecord
from app.schemas.llm_log import LLMRequestLogDetail, LLMRequestLogItem, LLMRequestLogPage
from app.services.llm_log_service import LLMLogService

router = APIRouter(prefix="/system/llm-log", tags=["llm-log"])


@router.get("/list")
def list_logs(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: LLMLogService = Depends(get_llm_log_service),
) -> dict[str, Any]:
    """分页查询大模型请求日志列表（仅管理员）。

    Args:
        pageNum: 前端传入的分页页码。
        pageSize: 前端传入的每页条数。
        admin: 当前登录的管理员用户。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    logs, total = service.list_logs(pageNum, pageSize)
    page = LLMRequestLogPage(list=[_to_item(item) for item in logs], total=total)
    return success_response(data=page.model_dump(), message="获取成功")


@router.get("/{log_id}")
def get_log(
    log_id: int,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: LLMLogService = Depends(get_llm_log_service),
) -> dict[str, Any]:
    """查询单条请求日志详情，含完整请求与响应报文（仅管理员）。

    Args:
        log_id: 日志 ID。
        admin: 当前登录的管理员用户。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    log = service.get_log(log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志不存在")
    return success_response(data=_to_detail(log).model_dump(), message="获取成功")


def _to_item(log: LLMRequestLogRecord) -> LLMRequestLogItem:
    """将请求日志记录转换为列表项响应模型。

    Args:
        log: 待转换的请求日志记录。
    """
    return LLMRequestLogItem(
        id=log.id,
        model=log.model,
        baseUrl=log.base_url,
        promptTokens=log.prompt_tokens,
        completionTokens=log.completion_tokens,
        totalTokens=log.total_tokens,
        latencyMs=log.latency_ms,
        status=log.status,
        errorMessage=log.error_message,
        createTime=log.created_at,
    )


def _to_detail(log: LLMRequestLogRecord) -> LLMRequestLogDetail:
    """将请求日志记录转换为详情响应模型（含完整报文）。

    Args:
        log: 待转换的请求日志记录。
    """
    return LLMRequestLogDetail(
        id=log.id,
        model=log.model,
        baseUrl=log.base_url,
        promptTokens=log.prompt_tokens,
        completionTokens=log.completion_tokens,
        totalTokens=log.total_tokens,
        latencyMs=log.latency_ms,
        status=log.status,
        errorMessage=log.error_message,
        createTime=log.created_at,
        requestPayload=log.request_payload,
        responsePayload=log.response_payload,
    )
