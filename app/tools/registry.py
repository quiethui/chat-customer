"""轻量级 Tool Calling 注册与执行模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolExecution:
    """单次工具调用结果。

    Attributes:
        name: 工具唯一名称，便于后续日志、调试和扩展其他查询工具。
        content: 工具返回给大模型的结构化文本，要求只包含当前用户可见的数据。
    """

    name: str
    content: str


class ChatTool(Protocol):
    """聊天工具协议，新增工具只需要实现这两个方法。"""

    name: str

    def can_handle(self, question: str) -> bool:
        """判断当前用户问题是否应该调用该工具。

        Args:
            question: 用户输入的问题文本。
        """

    def call(self, user_id: int, question: str) -> ToolExecution:
        """按当前用户上下文执行工具查询并返回结果。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            question: 用户输入的问题文本。
        """


class SimpleToolRegistry:
    """顺序执行的简单工具注册表。

    当前项目暂不引入复杂 Agent 或工作流；注册表只负责根据问题触发匹配工具，
    后续新增商品查询、优惠券查询等功能时，继续追加实现了 ChatTool 协议的类即可。
    """

    def __init__(self, tools: list[ChatTool]) -> None:
        """保存聊天工具列表。

        Args:
            tools: 可被聊天流程调用的工具实例列表，执行顺序与列表顺序一致。
        """
        self.tools = tools

    def call(self, user_id: int, question: str) -> list[ToolExecution]:
        """调用所有能处理当前问题的工具。

        Args:
            user_id: 当前登录用户 ID，用于所有业务数据查询的用户隔离。
            question: 用户本轮输入的问题文本。

        Returns:
            已触发工具的查询结果列表；没有匹配工具时返回空列表。
        """
        executions: list[ToolExecution] = []
        for tool in self.tools:
            if tool.can_handle(question):
                executions.append(tool.call(user_id, question))
        return executions
