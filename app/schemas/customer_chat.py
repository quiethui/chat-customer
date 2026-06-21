"""客户端聊天接口的数据模型定义（含 SSE 事件模型）。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerChatRequest(BaseModel):
    """客户端聊天提问请求体。"""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., min_length=1, max_length=2000, description="客户本轮输入的问题文本。")
    session_id: str | None = Field(
        default=None, alias="sessionId", max_length=64, description="会话 ID；为空时后端自动创建新会话。"
    )


class CustomerChatResponse(BaseModel):
    """客户端非流式聊天回答响应数据。"""

    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(..., description="大模型生成的客服回答。")
    references: list[str] = Field(default_factory=list, description="本次回答引用的知识库片段或业务工具结果。")
    session_id: str | None = Field(default=None, alias="sessionId", description="本次问答所属会话 ID。")


class StreamStatusEvent(BaseModel):
    """SSE 进度事件：提示客户端当前处理阶段。"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["status"] = "status"
    message: str = Field(..., description="进度提示文案，例如「正在思考…」。")
    session_id: str | None = Field(default=None, alias="sessionId", description="本次问答所属会话 ID。")


class StreamDeltaEvent(BaseModel):
    """SSE 回答增量事件：逐段下发的回答文本。"""

    type: Literal["delta"] = "delta"
    text: str = Field(..., description="本段回答增量文本。")


class StreamDoneEvent(BaseModel):
    """SSE 结束事件：携带引用与会话 ID。"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["done"] = "done"
    references: list[str] = Field(default_factory=list, description="本次回答引用的知识库片段或业务工具结果。")
    session_id: str | None = Field(default=None, alias="sessionId", description="本次问答所属会话 ID。")
