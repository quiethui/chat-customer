"""聊天消息接口的数据模型定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    """聊天消息列表接口返回的单条消息。"""

    id: int = Field(..., description="消息数据库自增 ID。")
    sessionId: str = Field(..., description="消息所属会话 ID。")
    userId: int = Field(..., description="消息所属用户 ID，用于数据隔离。")
    role: str = Field(..., description="消息角色，通常为 user 或 assistant。")
    content: str = Field(..., description="消息正文内容。")
    modelName: str | None = Field(default=None, description="助手消息使用的模型名称，用户消息一般为空。")
    totalTokens: int = Field(default=0, description="本条消息消耗的 token 数；当前未统计时为 0。")
    references: list[str] = Field(default_factory=list, description="助手回答关联的引用内容列表。")
    createTime: datetime = Field(..., description="消息创建时间。")
