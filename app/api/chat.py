"""聊天接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.response import success_response
from app.dependencies import get_chat_service, get_current_user, get_session_service
from app.repositories.mysql.records import UserRecord
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.session_service import SessionService

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: UserRecord = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
    session_service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    """处理聊天提问，校验会话归属后交给 ChatService 生成回答。

    Args:
        request: 当前接口接收的请求体或请求对象。
        user: 当前登录用户记录。
        service: 当前接口注入的业务服务实例。
        session_service: 会话业务服务实例。
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题不能为空")
    if request.session_id and not session_service.get_session(user.id, request.session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    result = await service.answer(
        question,
        user.id,
        request.session_id,
        request.rag_test,
        request.knowledge_base_ids,
        request.file_ids,
    )
    response = ChatResponse(
        answer=result.answer,
        references=result.references,
        session_id=result.session_id,
        prompt=result.prompt,
        rag_test=result.rag_test,
        rag_debug=result.rag_debug,
    )
    return success_response(data=response.model_dump(by_alias=True), message="回答成功")
