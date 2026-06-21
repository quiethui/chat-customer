"""客户端（对外 AI 客服）聊天接口模块。"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import (
    create_mysql_repository,
    get_chat_service,
    get_conversation_bus,
    get_conversation_service,
    get_current_customer,
)
from app.repositories.conversation_bus import ConversationBus
from app.repositories.mysql.records import CustomerRecord
from app.schemas.conversation import (
    ConversationMessageItem,
    CustomerConversationItem,
    CustomerMessageRequest,
    RatingRequest,
)
from app.schemas.customer_chat import (
    CustomerChatRequest,
    CustomerChatResponse,
    StreamDeltaEvent,
    StreamDoneEvent,
    StreamStatusEvent,
)
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/customer", tags=["customer-chat"])

# SSE 事件类型到响应模型的映射，用于统一序列化为带 camelCase 别名的 JSON。
_EVENT_MODELS = {"status": StreamStatusEvent, "delta": StreamDeltaEvent, "done": StreamDoneEvent}


@router.post("/chat")
async def customer_chat(
    request: CustomerChatRequest,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """客户端非流式问答（兼容接口），适合无法消费 SSE 的场景。

    Args:
        request: 当前接口接收的请求体。
        customer: 当前客户端登录的客户记录。
        service: 聊天问答服务实例。
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题不能为空")
    result = await service.answer(question, customer.id, request.session_id)
    response = CustomerChatResponse(
        answer=result.answer,
        references=result.references,
        session_id=result.session_id,
    )
    return success_response(data=response.model_dump(by_alias=True), message="回答成功")


@router.get("/chat/stream")
async def customer_chat_stream(
    question: str,
    sessionId: str | None = None,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """客户端 SSE 流式问答：逐段下发回答，并在结束时返回引用与会话 ID。

    Args:
        question: 客户本轮问题（查询参数）。
        sessionId: 可选会话 ID（查询参数）；为空时后端自动创建。
        customer: 当前客户端登录的客户记录。
        service: 聊天问答服务实例。
    """
    text = question.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题不能为空")

    async def event_generator() -> Any:
        """把服务层事件序列化为 SSE data 帧。"""
        async for event in service.answer_stream(text, customer.id, sessionId):
            model = _EVENT_MODELS[event["type"]](**event)
            yield f"data: {model.model_dump_json(by_alias=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/conversations")
def list_my_conversations(
    customer: CustomerRecord = Depends(get_current_customer),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """列出当前客户的会话（倒序），供复访恢复与登录后的历史会话列表。

    Args:
        customer: 当前客户端登录的客户记录。
        service: 会话编排服务实例。
    """
    sessions = service.list_customer_sessions(customer.id)
    data = [
        CustomerConversationItem(
            session_id=item.id,
            session_title=item.session_title,
            status=item.status,
            mode=item.mode,
            last_message_at=item.last_message_at,
            updated_at=item.updated_at,
            created_at=item.created_at,
        ).model_dump(by_alias=True)
        for item in sessions
    ]
    return success_response(data=data, message="获取成功")

@router.post("/conversations/{session_id}/handoff")
def request_handoff(
    session_id: str,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """客户请求转人工，把会话置为等待坐席接入。

    Args:
        session_id: 聊天会话 ID。
        customer: 当前客户端登录的客户记录。
        service: 会话编排服务实例。
    """
    record = run_with_value_error(lambda: service.request_handoff(customer.id, session_id), status.HTTP_404_NOT_FOUND)
    return success_response(data={"sessionId": record.id, "status": record.status}, message="正在为您转接人工客服")


@router.post("/conversations/{session_id}/rating")
def rate_conversation(
    session_id: str,
    request: RatingRequest,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """客户为会话提交满意度评分。

    Args:
        session_id: 聊天会话 ID。
        request: 满意度评分请求体。
        customer: 当前客户端登录的客户记录。
        service: 会话编排服务实例。
    """
    record = run_with_value_error(
        lambda: service.rate(customer.id, session_id, request.rating, request.comment), status.HTTP_404_NOT_FOUND
    )
    return success_response(data={"sessionId": record.id, "rating": record.rating}, message="感谢您的评价")


@router.post("/conversations/{session_id}/messages")
def send_customer_message(
    session_id: str,
    request: CustomerMessageRequest,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """客户在人工会话中给坐席发送消息（仅人工模式 waiting/serving 可用）。

    Args:
        session_id: 聊天会话 ID。
        request: 客户消息请求体。
        customer: 当前客户端登录的客户记录。
        service: 会话编排服务实例。
    """
    message = run_with_value_error(
        lambda: service.customer_message(customer.id, session_id, request.content), status.HTTP_400_BAD_REQUEST
    )
    data = ConversationMessageItem(
        id=message.id,
        role=message.role,
        sender_type=message.sender_type,
        agent_id=message.agent_id,
        content=message.content,
        created_at=message.created_at,
    ).model_dump(by_alias=True)
    return success_response(data=data, message="发送成功")


@router.get("/conversations/{session_id}/messages")
def list_conversation_history(
    session_id: str,
    customer: CustomerRecord = Depends(get_current_customer),
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """复访时拉取当前客户某会话的历史消息。

    Args:
        session_id: 聊天会话 ID。
        customer: 当前客户端登录的客户记录。
        service: 会话编排服务实例。
    """
    messages = run_with_value_error(
        lambda: service.list_customer_messages(customer.id, session_id), status.HTTP_404_NOT_FOUND
    )
    data = [
        ConversationMessageItem(
            id=message.id,
            role=message.role,
            sender_type=message.sender_type,
            agent_id=message.agent_id,
            content=message.content,
            created_at=message.created_at,
        ).model_dump(by_alias=True)
        for message in messages
    ]
    return success_response(data=data, message="获取成功")


@router.get("/conversations/{session_id}/events")
async def conversation_events(
    session_id: str,
    customer: CustomerRecord = Depends(get_current_customer),
    bus: ConversationBus = Depends(get_conversation_bus),
) -> StreamingResponse:
    """客户订阅会话事件流（SSE），实时接收坐席消息与状态变更。

    会话归属校验在建立流之前用短连接完成，避免 SSE 期间长期占用数据库连接。

    Args:
        session_id: 聊天会话 ID。
        customer: 当前客户端登录的客户记录。
        bus: 会话事件总线实例。
    """
    repository = create_mysql_repository()
    try:
        owned = repository.get_chat_session(customer.id, session_id)
    finally:
        repository.close()
    if not owned:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    async def subscribe_generator() -> Any:
        """把会话总线事件序列化为 SSE data 帧。"""
        async for event in bus.subscribe(session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        subscribe_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
