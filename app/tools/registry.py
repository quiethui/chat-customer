"""轻量级 Function Calling 注册与执行模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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
    """聊天工具协议，新增工具需要声明 schema 并实现执行方法。"""

    name: str
    schema: dict[str, Any]

    def can_handle(self, question: str) -> bool:
        """判断本地 fallback 是否应该调用该工具。

        Args:
            question: 用户输入的问题文本。
        """

    def call(self, user_id: int, arguments: dict[str, Any]) -> ToolExecution:
        """按模型选择的参数执行工具查询并返回结果。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            arguments: 模型通过 Function Calling 生成的工具参数。
        """

    def call_from_question(self, user_id: int, question: str) -> ToolExecution:
        """从用户问题中提取参数并执行工具查询，用于本地 fallback。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            question: 用户输入的问题文本。
        """


class SimpleToolRegistry:
    """简单工具注册表，负责暴露 schema 并执行模型选中的工具。

    当前项目暂不引入复杂 Agent 或工作流；注册表只维护工具名称到实例的映射。
    后续新增商品查询、优惠券查询等功能时，继续追加实现了 ChatTool 协议的类即可。
    """

    def __init__(self, tools: list[ChatTool]) -> None:
        """保存聊天工具列表。

        Args:
            tools: 可被聊天流程调用的工具实例列表，执行顺序与列表顺序一致。
        """
        self.tools = tools
        self._tool_map = {tool.name: tool for tool in tools}

    def get_schemas(self) -> list[dict[str, Any]]:
        """返回可传给 OpenAI 兼容模型的工具 schema 列表。

        Returns:
            Chat Completions tools 参数可直接使用的 JSON Schema 列表。
        """
        return [tool.schema for tool in self.tools]

    def execute(self, user_id: int, name: str, arguments: dict[str, Any]) -> ToolExecution:
        """执行模型指定的工具。

        Args:
            user_id: 当前登录用户 ID，用于所有业务数据查询的用户隔离。
            name: 模型选择的工具名称。
            arguments: 模型生成并由后端解析后的工具参数。

        Returns:
            工具执行结果。

        Raises:
            ValueError: 工具名称不存在时抛出。
        """
        tool = self._tool_map.get(name)
        if not tool:
            raise ValueError(f"未知工具：{name}")
        return tool.call(user_id, arguments)

    def call(self, user_id: int, question: str) -> list[ToolExecution]:
        """按关键词调用工具，用于未配置远程模型时的本地 fallback。

        Args:
            user_id: 当前登录用户 ID，用于所有业务数据查询的用户隔离。
            question: 用户本轮输入的问题文本。

        Returns:
            已触发工具的查询结果列表；没有匹配工具时返回空列表。
        """
        executions: list[ToolExecution] = []
        for tool in self.tools:
            if tool.can_handle(question):
                executions.append(tool.call_from_question(user_id, question))
        return executions
