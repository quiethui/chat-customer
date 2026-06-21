"""大模型请求日志接口的数据模型定义。"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class LLMRequestLogItem(BaseModel):
    """请求日志列表项，不含完整请求/响应报文以减小传输体积。"""

    id: int = Field(..., description="日志 ID。")
    model: str = Field(..., description="本次请求使用的模型名称。")
    baseUrl: str | None = Field(default=None, description="OpenAI 兼容接口基础地址。")
    promptTokens: int | None = Field(default=None, description="提示词消耗 token 数。")
    completionTokens: int | None = Field(default=None, description="补全消耗 token 数。")
    totalTokens: int | None = Field(default=None, description="本次请求总消耗 token 数。")
    latencyMs: int | None = Field(default=None, description="请求往返耗时（毫秒）。")
    status: str = Field(..., description="请求结果：success=成功，error=失败。")
    errorMessage: str | None = Field(default=None, description="请求失败时的错误摘要。")
    createTime: datetime = Field(..., description="日志创建时间。")


class LLMRequestLogDetail(LLMRequestLogItem):
    """请求日志详情，附带完整请求参数与响应数据 JSON 文本。"""

    requestPayload: str = Field(..., description="完整请求参数 JSON 文本。")
    responsePayload: str | None = Field(default=None, description="完整响应数据 JSON 文本；失败时为空。")


class LLMRequestLogPage(BaseModel):
    """请求日志分页结果。"""

    list: List[LLMRequestLogItem] = Field(default_factory=list, description="当前页日志列表。")
    total: int = Field(..., description="日志总条数，用于前端分页。")
