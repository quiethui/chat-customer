"""聊天消息记录接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.response import success_response
from app.dependencies import get_current_user, get_message_service
from app.repositories.mysql_records import ChatMessageRecord, UserRecord
from app.schemas.message import ChatMessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/system/message", tags=["message"])


@router.get("/list")
def list_messages(
    sessionId: str = Query(..., min_length=1),
    user: UserRecord = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
) -> dict[str, Any]:
    """按会话 ID 查询当前用户可见的聊天消息列表。

    Args:
        sessionId: 前端传入的聊天会话 ID。
        user: 当前登录用户记录。
        service: 当前接口注入的消息服务实例。
    """
    messages = service.list_messages(user.id, sessionId)
    return success_response(data=[_to_response(item).model_dump() for item in messages], message="获取成功")


def _to_response(message: ChatMessageRecord) -> ChatMessageResponse:
    """将数据库消息记录转换为前端需要的驼峰字段响应。

    Args:
        message: 响应消息或待转换的消息记录。
    """
    return ChatMessageResponse(
        id=message.id,
        sessionId=message.session_id,
        userId=message.user_id,
        role=message.role,
        content=message.content,
        modelName=message.model_name,
        totalTokens=message.total_tokens,
        references=[item for item in (message.references_text or "").split("\n") if item],
        createTime=message.created_at,
    )
