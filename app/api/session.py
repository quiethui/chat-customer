"""聊天会话接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.response import success_response
from app.dependencies import get_current_user, get_session_service
from app.repositories.mysql_records import ChatSessionRecord, UserRecord
from app.schemas.session import ChatSessionCreate, ChatSessionResponse, ChatSessionUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/system/session", tags=["session"])


@router.get("/list")
def list_sessions(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=25, ge=1, le=100),
    user: UserRecord = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """分页查询当前用户的聊天会话列表。

    Args:
        pageNum: 前端传入的分页页码。
        pageSize: 前端传入的每页条数。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
    """
    sessions = service.list_sessions(user.id, pageNum, pageSize)
    return success_response(data=[_to_response(item).model_dump() for item in sessions], message="获取成功")


@router.post("")
def create_session(
    request: ChatSessionCreate,
    user: UserRecord = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """创建一个空聊天会话，供前端先建会话再发送消息。

    Args:
        request: 当前接口接收的请求体或请求对象。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
    """
    session = service.create_session(user.id, request.sessionTitle, request.sessionContent, request.remark)
    return success_response(data=_to_response(session).model_dump(), message="创建成功")


@router.put("")
def update_session(
    request: ChatSessionUpdate,
    user: UserRecord = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """更新当前用户名下的会话标题、内容或备注。

    Args:
        request: 当前接口接收的请求体或请求对象。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
    """
    session = service.update_session(user.id, request.id, request.sessionTitle, request.sessionContent, request.remark)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return success_response(data=_to_response(session).model_dump(), message="更新成功")


@router.get("/{session_id}")
def get_session(
    session_id: str,
    user: UserRecord = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """获取当前用户名下的单个会话详情。

    Args:
        session_id: 聊天会话 ID。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
    """
    session = service.get_session(user.id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return success_response(data=_to_response(session).model_dump(), message="获取成功")


@router.delete("/{ids}")
def delete_session(
    ids: str,
    user: UserRecord = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """批量软删除当前用户名下的会话，并清理对应 Redis 上下文。

    Args:
        ids: 前端传入的待删除会话 ID 字符串，多个 ID 以逗号分隔。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
    """
    service.delete_sessions(user.id, [item for item in ids.split(",") if item])
    return success_response(message="删除成功")


def _to_response(session: ChatSessionRecord) -> ChatSessionResponse:
    """将数据库会话记录转换为前端需要的响应模型。

    Args:
        session: 待转换的聊天会话记录。
    """
    return ChatSessionResponse(
        id=session.id,
        userId=session.user_id,
        sessionTitle=session.session_title,
        sessionContent=session.session_content,
        remark=session.remark,
        createTime=session.created_at,
        updateTime=session.updated_at,
    )
