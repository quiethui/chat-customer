"""ChatService.answer_stream 流式问答的单元测试。

覆盖两条主路径：
- 远程模型启用：AgentExecutor 服务端跑工具轮，最终回答按段下发；
- 本地兜底：stream_answer 逐段产出兜底回答。
并校验 status→delta→done 事件序列与消息持久化（sender_type）。
"""

from collections.abc import AsyncIterator
from typing import Any

from app.agent import AgentExecutor
from app.repositories.vector.base import RetrievalResult
from app.services.chat_service import ChatService
from app.tools.registry import SimpleToolRegistry


class FakeEmbedding:
    dimension = 8

    def embed(self, text: str) -> list[float]:
        return [0.0] * self.dimension


class FakeVectorRepository:
    def search(self, vector: list[float], top_k: int, filters: Any = None) -> list[RetrievalResult]:
        return []


class FakeContextRepository:
    def __init__(self) -> None:
        self.appended: list[dict[str, str]] = []

    def get_messages(self, customer_id: int, session_id: str) -> list[dict[str, str]]:
        return []

    def replace_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        pass

    def append_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        self.appended.extend(messages)


class FakeMySQLRepository:
    def __init__(self) -> None:
        self.created_sessions: list[str] = []
        self.messages: list[dict[str, Any]] = []
        self.commits = 0

    def create_chat_session(self, session_id: str, customer_id: int, title: str, content: str, remark: str) -> None:
        self.created_sessions.append(session_id)

    def add_chat_message(self, session_id: str, customer_id: int, role: str, content: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"role": role, "sender_type": kwargs.get("sender_type"), "content": content})

    def commit(self) -> None:
        self.commits += 1

    def list_recent_messages(self, customer_id: int, session_id: str, limit: int) -> list[Any]:
        return []


class FakeLLMClient:
    """可配置启用状态的假大模型客户端，支持流式与非流式。"""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.model = "test-model"

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None) -> dict[str, Any]:
        return {"role": "assistant", "content": "您好，已为您处理。"}

    async def answer(self, prompt: str) -> str:
        return "兜底回答"

    async def stream_answer(self, prompt: str) -> AsyncIterator[str]:
        for piece in ["兜底", "回答"]:
            yield piece


def _service(llm: FakeLLMClient) -> tuple[ChatService, FakeMySQLRepository, FakeContextRepository]:
    mysql = FakeMySQLRepository()
    context = FakeContextRepository()
    registry = SimpleToolRegistry([])
    service = ChatService(
        embedding=FakeEmbedding(),  # type: ignore[arg-type]
        repository=FakeVectorRepository(),  # type: ignore[arg-type]
        llm_client=llm,  # type: ignore[arg-type]
        top_k=4,
        reference_limit=3,
        reference_max_chars=240,
        mysql_repository=mysql,  # type: ignore[arg-type]
        context_repository=context,  # type: ignore[arg-type]
        tool_registry=registry,
        agent_executor=AgentExecutor(llm, registry, max_rounds=3),  # type: ignore[arg-type]
    )
    return service, mysql, context


async def _collect(agen: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event async for event in agen]


async def test_answer_stream_enabled_emits_status_delta_done() -> None:
    """远程模型启用：首个事件为 status、末个为 done，中间有 delta，且回答可还原。"""
    llm = FakeLLMClient(enabled=True)
    service, mysql, _ = _service(llm)

    events = await _collect(service.answer_stream("你好", customer_id=1))

    types = [event["type"] for event in events]
    assert types[0] == "status"
    assert types[-1] == "done"
    assert "delta" in types
    answer = "".join(event["text"] for event in events if event["type"] == "delta")
    assert answer == "您好，已为您处理。"
    assert events[-1]["session_id"]
    # 客户消息与机器人消息各落库一条，sender_type 正确。
    senders = [(m["role"], m["sender_type"]) for m in mysql.messages]
    assert ("user", "customer") in senders
    assert ("assistant", "bot") in senders


async def test_answer_stream_fallback_uses_stream_answer() -> None:
    """本地兜底：通过 stream_answer 逐段产出兜底回答。"""
    llm = FakeLLMClient(enabled=False)
    service, _, _ = _service(llm)

    events = await _collect(service.answer_stream("你好", customer_id=1))

    answer = "".join(event["text"] for event in events if event["type"] == "delta")
    assert answer == "兜底回答"
    assert events[-1]["type"] == "done"


async def test_answer_stream_reuses_existing_session() -> None:
    """传入已有会话 ID 时不重复创建会话。"""
    llm = FakeLLMClient(enabled=True)
    service, mysql, _ = _service(llm)

    events = await _collect(service.answer_stream("问题", customer_id=1, session_id="sess-1"))

    assert mysql.created_sessions == []
    assert events[-1]["session_id"] == "sess-1"
