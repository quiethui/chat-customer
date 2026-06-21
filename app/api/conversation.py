"""坐席端会话队列与转人工接口模块（仅坐席/管理员可访问）。"""

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import get_conversation_bus, get_conversation_service, get_current_agent_manager
from app.repositories.conversation_bus import ConversationBus
from app.repositories.mysql.records import ChatMessageRecord, ManagerRecord
from app.schemas.conversation import AgentReplyRequest, AgentTransferRequest, ConversationMessageItem, ConversationQueueItem
from app.services.conversation_service import ConversationService, ConversationView

router = APIRouter(prefix="/system/conversations", tags=["conversation"])


@router.get("/events")
async def agent_events(
    agent: ManagerRecord = Depends(get_current_agent_manager),
    bus: ConversationBus = Depends(get_conversation_bus),
) -> StreamingResponse:
    """坐席订阅全局广播事件流（SSE），实时接收转人工请求、接管确认、客户消息提醒。

    所有在线坐席共享同一频道，前端按事件 type 与 sessionId/agentId 分发处理。

    Args:
        agent: 当前坐席用户记录（保留以触发鉴权依赖）。
        bus: 会话事件总线实例。
    """
    _ = agent

    async def subscribe_generator() -> Any:
        """把广播事件序列化为 SSE data 帧。"""
        async for event in bus.subscribe_broadcast():
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        subscribe_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/agents")
def list_available_agents(
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """获取可用坐席列表（用于转接）。

    Args:
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    _ = agent
    managers = service.repository.list_managers(1, 100)
    agents = [
        {"id": m.id, "nickname": m.nickname or m.username}
        for m in managers[0]
        if m.status == 1 and m.deleted_at is None
    ]
    return success_response(data=agents, message="获取成功")


@router.get("")
def list_conversations(
    status_filter: str | None = Query(default=None, alias="status"),
    scope: str = Query(default="mine", pattern="^(mine|all)$"),
    page: int = 1,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """查询坐席会话队列，可按逗号分隔的 status 过滤（默认等待+服务中）。

    Args:
        status_filter: 逗号分隔的会话状态过滤字符串，例如 waiting,serving。
        scope: 队列范围，mine=自己的+待接入，all=全部会话。
        page: 分页页码。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    statuses = [item.strip() for item in status_filter.split(",") if item.strip()] if status_filter else None
    views = service.list_queue(statuses, agent, scope, page=page)
    data = [_to_queue_item(view, service.repository).model_dump(by_alias=True) for view in views]
    return success_response(data=data, message="获取成功")


@router.get("/{session_id}/messages")
def list_messages(
    session_id: str,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """查询某个会话的全部消息（坐席视角，不按客户隔离）。

    Args:
        session_id: 聊天会话 ID。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    messages = run_with_value_error(lambda: service.list_messages(session_id), status.HTTP_404_NOT_FOUND)
    data = [_to_message_item(message).model_dump(by_alias=True) for message in messages]
    return success_response(data=data, message="获取成功")


@router.post("/{session_id}/claim")
def claim(
    session_id: str,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """坐席接管等待中的会话。

    Args:
        session_id: 聊天会话 ID。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    record = run_with_value_error(lambda: service.claim(agent.id, session_id), status.HTTP_409_CONFLICT)
    return success_response(data={"sessionId": record.id, "status": record.status}, message="接管成功")


@router.post("/{session_id}/messages")
def reply(
    session_id: str,
    request: AgentReplyRequest,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """坐席回复消息，落库并推送到客户。

    Args:
        session_id: 聊天会话 ID。
        request: 坐席回复请求体。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    try:
        message = service.reply(agent, session_id, request.content)
        return success_response(data=_to_message_item(message).model_dump(by_alias=True), message="回复成功")
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{session_id}/close")
def close(
    session_id: str,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """关闭会话。

    Args:
        session_id: 聊天会话 ID。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    try:
        record = service.close(agent, session_id)
        return success_response(data={"sessionId": record.id, "status": record.status}, message="已关闭会话")
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{session_id}/handback")
def handback(
    session_id: str,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """把会话交还给智能助手。

    Args:
        session_id: 聊天会话 ID。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    try:
        record = service.handback(agent, session_id)
        return success_response(data={"sessionId": record.id, "status": record.status}, message="已交还智能助手")
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{session_id}/transfer")
def transfer(
    session_id: str,
    request: AgentTransferRequest,
    agent: ManagerRecord = Depends(get_current_agent_manager),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """转接会话给其他坐席。

    Args:
        session_id: 聊天会话 ID。
        request: 转接请求体。
        agent: 当前坐席用户记录。
        service: 会话编排服务实例。
    """
    try:
        record = service.transfer(agent, session_id, request.target_agent_id, request.reason)
        return success_response(
            data={"sessionId": record.id, "status": record.status, "assignedAgentId": record.assigned_agent_id},
            message="转接成功",
        )
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


def _to_queue_item(view: ConversationView, repository) -> ConversationQueueItem:
    """将会话视图转换为坐席队列项响应模型。

    Args:
        view: 会话编排服务返回的会话视图。
        repository: 数据仓储实例，用于查询坐席信息。
    """
    session = view.session
    agent_name = None
    if session.assigned_agent_id:
        agent = repository.get_manager_by_id(session.assigned_agent_id)
        agent_name = agent.nickname if agent else None
    return ConversationQueueItem(
        session_id=session.id,
        customer_id=session.customer_id,
        customer_nickname=view.customer.nickname if view.customer else None,
        session_title=session.session_title,
        status=session.status,
        mode=session.mode,
        assigned_agent_id=session.assigned_agent_id,
        assigned_agent_name=agent_name,
        last_message_at=session.last_message_at,
        rating=session.rating,
        updated_at=session.updated_at,
    )


def _to_message_item(message: ChatMessageRecord) -> ConversationMessageItem:
    """将聊天消息记录转换为会话消息响应模型。

    Args:
        message: 聊天消息记录。
    """
    return ConversationMessageItem(
        id=message.id,
        role=message.role,
        sender_type=message.sender_type,
        agent_id=message.agent_id,
        content=message.content,
        created_at=message.created_at,
    )
