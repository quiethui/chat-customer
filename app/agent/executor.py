"""Agent 执行器。

把"模型自主选择工具 -> 执行工具 -> 回传结果 -> 再次询问模型"的多轮循环
从聊天服务中独立出来，便于复用、测试，并记录每一步的执行 trace 以支持可观测性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.openai_client import OpenAIClient
    from app.tools.registry import SimpleToolRegistry


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCallStep:
    """一次工具调用的执行轨迹，用于日志与调试。"""

    round_index: int  # 第几轮工具调用，从 1 开始。
    name: str  # 模型选择的工具名称。
    arguments: dict[str, Any]  # 模型生成并解析后的工具参数。
    content: str  # 工具返回（或失败兜底）的结果文本。
    ok: bool  # 工具是否执行成功。


@dataclass
class AgentRunResult:
    """Agent 一次完整运行的结果。"""

    answer: str  # 模型最终回答。
    tool_results: list[str] = field(default_factory=list)  # 可展示给用户的工具结果文本。
    trace: list[ToolCallStep] = field(default_factory=list)  # 工具调用执行轨迹。
    rounds: int = 0  # 实际与模型交互的工具调用轮数。


class AgentExecutor:
    """基于 OpenAI 兼容 Function Calling 的工具调用执行器。

    模型根据工具 schema 自主决定是否调用工具；执行器负责回传工具结果、控制
    最大轮数，并在超过轮数后强制收敛为一次普通回答。
    """

    def __init__(self, llm_client: OpenAIClient, tool_registry: SimpleToolRegistry, max_rounds: int = 3) -> None:
        """初始化 Agent 执行器。

        Args:
            llm_client: OpenAI 兼容大模型客户端实例。
            tool_registry: Tool Calling 工具注册表实例。
            max_rounds: 最大工具调用轮数，超过后强制收敛为一次普通回答。
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_rounds = max(1, max_rounds)

    async def run(self, customer_id: int, prompt: str) -> AgentRunResult:
        """运行一次工具调用循环并返回最终回答。

        Args:
            customer_id: 当前客户 ID，用于工具执行时的数据隔离。
            prompt: 已拼接 RAG 上下文、历史消息和客户问题的客服 Prompt。

        Returns:
            包含最终回答、可见工具结果和执行轨迹的运行结果。
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        result = AgentRunResult(answer="")
        tool_schemas = self.tool_registry.get_schemas()
        for round_index in range(1, self.max_rounds + 1):
            result.rounds = round_index
            message = await self.llm_client.chat(messages, tool_schemas)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                result.answer = str(message.get("content") or "")
                return result

            messages.append(self._build_assistant_tool_call_message(message, tool_calls))
            for tool_call in tool_calls:
                tool_message, step = self._execute_tool_call(customer_id, round_index, tool_call)
                messages.append(tool_message)
                result.trace.append(step)
                if step.ok and step.content:
                    result.tool_results.append(step.content)

        # 超过最大轮数仍未收敛，去掉工具选项再要一次最终回答，避免无限循环。
        logger.info("Agent 达到最大工具轮数 %s，强制收敛回答：customer_id=%s", self.max_rounds, customer_id)
        final_message = await self.llm_client.chat(messages)
        result.answer = str(final_message.get("content") or "")
        return result

    def _build_assistant_tool_call_message(
        self,
        message: dict[str, Any],
        tool_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """构建可回传给 Chat Completions 的 assistant tool_calls 消息。

        Args:
            message: 模型返回的原始 assistant 消息。
            tool_calls: 模型请求执行的工具调用列表。

        Returns:
            符合 Chat Completions 多轮工具调用格式的 assistant 消息。
        """
        assistant_message: dict[str, Any] = {"role": "assistant", "tool_calls": tool_calls}
        content = message.get("content")
        if content:
            assistant_message["content"] = content
        return assistant_message

    def _execute_tool_call(
        self,
        customer_id: int,
        round_index: int,
        tool_call: dict[str, Any],
    ) -> tuple[dict[str, Any], ToolCallStep]:
        """执行模型指定的单次工具调用，构建 tool 消息与执行轨迹。

        Args:
            customer_id: 当前客户 ID，用于工具执行时的数据隔离。
            round_index: 当前工具调用轮数。
            tool_call: 模型返回的单个 tool_call 字典。

        Returns:
            可追加到 Chat Completions 的 tool 消息，以及本次调用的执行轨迹。
        """
        tool_call_id = str(tool_call.get("id") or "")
        function = tool_call.get("function") or {}
        name = str(function.get("name") or "")
        arguments = self._parse_tool_arguments(function.get("arguments"))
        try:
            execution = self.tool_registry.execute(customer_id, name, arguments)
        except Exception:
            logger.warning("执行模型工具调用失败：tool=%s customer_id=%s", name, customer_id, exc_info=True)
            content = "暂时无法完成该业务查询，请用客服口吻说明稍后再试或建议用户补充信息。"
            step = ToolCallStep(round_index=round_index, name=name, arguments=arguments, content=content, ok=False)
            return self._build_tool_message(tool_call_id, content), step
        step = ToolCallStep(
            round_index=round_index,
            name=execution.name,
            arguments=arguments,
            content=execution.content,
            ok=True,
        )
        return self._build_tool_message(tool_call_id, execution.content), step

    def _parse_tool_arguments(self, value: object) -> dict[str, Any]:
        """解析模型返回的工具参数 JSON。

        Args:
            value: tool_call.function.arguments 字段，通常是 JSON 字符串。

        Returns:
            解析后的参数字典；解析失败时返回空字典。
        """
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or not value.strip():
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            logger.warning("模型工具参数不是合法 JSON：%s", value)
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _build_tool_message(self, tool_call_id: str, content: str) -> dict[str, Any]:
        """构建 Chat Completions tool 角色消息。

        Args:
            tool_call_id: 模型返回的工具调用 ID。
            content: 工具执行结果文本。

        Returns:
            可追加到消息列表中的 tool 消息。
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
