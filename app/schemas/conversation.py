"""转人工与坐席会话接口的数据模型定义。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationQueueItem(BaseModel):
    """坐席队列中的单条会话摘要。"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(..., alias="sessionId", description="会话 ID。")
    customer_id: int = Field(..., alias="customerId", description="客户 ID。")
    customer_nickname: str | None = Field(default=None, alias="customerNickname", description="客户昵称。")
    session_title: str = Field(..., alias="sessionTitle", description="会话标题。")
    status: str = Field(..., description="会话状态：bot/waiting/serving/closed。")
    mode: str = Field(..., description="服务模式：bot/agent。")
    assigned_agent_id: int | None = Field(default=None, alias="assignedAgentId", description="接管坐席用户 ID。")
    assigned_agent_name: str | None = Field(default=None, alias="assignedAgentName", description="接管坐席昵称。")
    last_message_at: datetime | None = Field(default=None, alias="lastMessageAt", description="最近活跃时间。")
    rating: int | None = Field(default=None, description="满意度评分。")
    updated_at: datetime | None = Field(default=None, alias="updatedAt", description="会话更新时间。")


class ConversationMessageItem(BaseModel):
    """会话消息记录。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="消息 ID。")
    role: str = Field(..., description="消息角色（LLM 上下文）：user/assistant。")
    sender_type: str = Field(..., alias="senderType", description="发送方：customer/bot/agent。")
    agent_id: int | None = Field(default=None, alias="agentId", description="人工消息坐席 ID。")
    content: str = Field(..., description="消息正文。")
    created_at: datetime | None = Field(default=None, alias="createdAt", description="消息创建时间。")


class CustomerConversationItem(BaseModel):
    """客户端「我的会话」列表项（供复访恢复与历史会话列表展示）。"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(..., alias="sessionId", description="会话 ID。")
    session_title: str = Field(..., alias="sessionTitle", description="会话标题。")
    status: str = Field(..., description="会话状态：bot/waiting/serving/closed。")
    mode: str = Field(..., description="服务模式：bot/agent。")
    last_message_at: datetime | None = Field(default=None, alias="lastMessageAt", description="最近消息时间。")
    updated_at: datetime | None = Field(default=None, alias="updatedAt", description="会话更新时间。")
    created_at: datetime | None = Field(default=None, alias="createdAt", description="会话创建时间。")


class AgentReplyRequest(BaseModel):
    """坐席回复请求体。"""

    content: str = Field(..., min_length=1, max_length=2000, description="坐席回复正文。")


class CustomerMessageRequest(BaseModel):
    """客户在人工会话中发送消息的请求体。"""

    content: str = Field(..., min_length=1, max_length=2000, description="客户在人工会话中发送的消息正文。")


class RatingRequest(BaseModel):
    """客户满意度评分请求体。"""

    rating: int = Field(..., ge=1, le=5, description="满意度评分，1 到 5。")
    comment: str | None = Field(default=None, max_length=500, description="评价文字，可选。")


class AgentTransferRequest(BaseModel):
    """坐席转接请求体。"""

    target_agent_id: int = Field(..., alias="targetAgentId", description="目标坐席用户 ID。")
    reason: str | None = Field(default=None, max_length=500, description="转接原因备注，可选。")
