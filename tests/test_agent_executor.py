"""AgentExecutor 工具调用循环的单元测试。"""

from typing import Any

from app.agent import AgentExecutor
from app.tools.registry import SimpleToolRegistry, ToolExecution


class ScriptedLLM:
    """按预设顺序返回响应的假大模型客户端。"""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None) -> dict[str, Any]:
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


class EchoTool:
    """回显参数的假工具。"""

    name = "echo"
    schema: dict[str, Any] = {
        "type": "function",
        "function": {"name": "echo", "description": "回显", "parameters": {"type": "object", "properties": {}}},
    }

    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[str, Any]]] = []

    def can_handle(self, question: str) -> bool:
        return True

    def call(self, user_id: int, arguments: dict[str, Any]) -> ToolExecution:
        self.calls.append((user_id, arguments))
        return ToolExecution(name="echo", content=f"echo:{arguments.get('text', '')}")

    def call_from_question(self, user_id: int, question: str) -> ToolExecution:
        return self.call(user_id, {"text": question})


class BoomTool:
    """执行即抛错的假工具。"""

    name = "boom"
    schema: dict[str, Any] = {
        "type": "function",
        "function": {"name": "boom", "description": "炸", "parameters": {"type": "object", "properties": {}}},
    }

    def can_handle(self, question: str) -> bool:
        return True

    def call(self, user_id: int, arguments: dict[str, Any]) -> ToolExecution:
        raise RuntimeError("tool failed")

    def call_from_question(self, user_id: int, question: str) -> ToolExecution:
        return self.call(user_id, {})


def _tool_call(call_id: str, name: str, arguments: str) -> dict[str, Any]:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


async def test_run_without_tool_calls_returns_content() -> None:
    llm = ScriptedLLM([{"role": "assistant", "content": "你好"}])
    executor = AgentExecutor(llm, SimpleToolRegistry([]), max_rounds=3)  # type: ignore[arg-type]

    result = await executor.run(customer_id=1, prompt="hi")

    assert result.answer == "你好"
    assert result.rounds == 1
    assert result.trace == []
    assert result.tool_results == []


async def test_run_executes_tool_then_answers() -> None:
    tool = EchoTool()
    llm = ScriptedLLM(
        [
            {"role": "assistant", "tool_calls": [_tool_call("1", "echo", '{"text": "hello"}')]},
            {"role": "assistant", "content": "最终回答"},
        ]
    )
    executor = AgentExecutor(llm, SimpleToolRegistry([tool]), max_rounds=3)  # type: ignore[arg-type]

    result = await executor.run(customer_id=42, prompt="问题")

    assert result.answer == "最终回答"
    assert result.rounds == 2
    assert result.tool_results == ["echo:hello"]
    assert tool.calls == [(42, {"text": "hello"})]
    assert len(result.trace) == 1
    assert result.trace[0].ok is True
    assert result.trace[0].name == "echo"


async def test_run_converges_after_max_rounds() -> None:
    """达到最大轮数后去掉工具选项强制收敛回答。"""
    tool = EchoTool()
    llm = ScriptedLLM(
        [
            {"role": "assistant", "tool_calls": [_tool_call("1", "echo", "{}")]},  # 第 1 轮
            {"role": "assistant", "content": "收敛回答"},  # 强制收敛
        ]
    )
    executor = AgentExecutor(llm, SimpleToolRegistry([tool]), max_rounds=1)  # type: ignore[arg-type]

    result = await executor.run(customer_id=1, prompt="问题")

    assert result.answer == "收敛回答"
    assert result.rounds == 1
    assert len(result.trace) == 1
    # 最后一次收敛调用不应再带工具 schema。
    assert llm.calls[-1]["tools"] is None


async def test_run_records_failed_tool_in_trace() -> None:
    llm = ScriptedLLM(
        [
            {"role": "assistant", "tool_calls": [_tool_call("1", "boom", "{}")]},
            {"role": "assistant", "content": "抱歉，稍后再试"},
        ]
    )
    executor = AgentExecutor(llm, SimpleToolRegistry([BoomTool()]), max_rounds=3)  # type: ignore[arg-type]

    result = await executor.run(customer_id=1, prompt="问题")

    assert result.answer == "抱歉，稍后再试"
    assert result.tool_results == []  # 失败结果不进入可见引用
    assert len(result.trace) == 1
    assert result.trace[0].ok is False


async def test_run_handles_invalid_json_arguments() -> None:
    tool = EchoTool()
    llm = ScriptedLLM(
        [
            {"role": "assistant", "tool_calls": [_tool_call("1", "echo", "not-json")]},
            {"role": "assistant", "content": "ok"},
        ]
    )
    executor = AgentExecutor(llm, SimpleToolRegistry([tool]), max_rounds=3)  # type: ignore[arg-type]

    result = await executor.run(customer_id=1, prompt="问题")

    assert result.answer == "ok"
    # 非法 JSON 参数被解析为空字典。
    assert tool.calls == [(1, {})]
