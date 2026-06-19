"""会话接口的数据模型定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    """新建会话请求体。"""

    sessionTitle: str = Field(..., min_length=1, max_length=120, description="会话标题，通常取用户首个问题的前若干字符。")
    sessionContent: str | None = Field(default=None, max_length=2000, description="会话摘要或首轮内容，可为空。")
    remark: str | None = Field(default=None, max_length=255, description="会话备注信息，可为空。")


class ChatSessionUpdate(BaseModel):
    """更新会话请求体，只更新非空字段。"""

    id: str = Field(..., min_length=1, max_length=64, description="要更新的会话 ID。")
    sessionTitle: str | None = Field(default=None, max_length=120, description="新的会话标题；为空表示不修改。")
    sessionContent: str | None = Field(default=None, max_length=2000, description="新的会话内容；为空表示不修改。")
    remark: str | None = Field(default=None, max_length=255, description="新的备注；为空表示不修改。")


class ChatSessionResponse(BaseModel):
    """会话接口返回给前端的会话数据。"""

    id: str = Field(..., description="会话 ID。")
    userId: int = Field(..., description="会话所属用户 ID。")
    sessionTitle: str = Field(..., description="会话标题。")
    sessionContent: str | None = Field(default=None, description="会话摘要或首轮内容。")
    remark: str | None = Field(default=None, description="会话备注。")
    createTime: datetime = Field(..., description="会话创建时间。")
    updateTime: datetime = Field(..., description="会话最后更新时间。")
