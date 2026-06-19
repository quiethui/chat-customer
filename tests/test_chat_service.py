"""ChatService 编排逻辑的单元测试。

使用内存假依赖覆盖两条主路径：
- 本地兜底（llm 未启用，走关键词工具 + fallback 回答）；
- 远程模型 Function Calling（llm 启用，模型直接返回答案）。
"""

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
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def search(self, vector: list[float], top_k: int, filters: Any = None) -> list[RetrievalResult]:
        return self._results


class FakeContextRepository:
    def __init__(self) -> None:
        self.store: dict[tuple[int, str], list[dict[str, str]]] = {}
        self.appended: list[dict[str, str]] = []

    def get_messages(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        return list(self.store.get((user_id, session_id), []))

    def replace_messages(self, user_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        self.store[(user_id, session_id)] = list(messages)

    def append_messages(self, user_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        self.appended.extend(messages)


class FakeMySQLRepository:
    def __init__(self) -> None:
        self.created_sessions: list[str] = []
        self.messages: list[dict[str, Any]] = []
        self.commits = 0

    def create_chat_session(self, session_id: str, user_id: int, title: str, content: str, remark: str) -> None:
        self.created_sessions.append(session_id)

    def add_chat_message(self, session_id: str, user_id: int, role: str, content: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"session_id": session_id, "role": role, "content": content})

    def commit(self) -> None:
        self.commits += 1

    def list_recent_messages(self, user_id: int, session_id: str, limit: int) -> list[Any]:
        return []

    def get_knowledge_base(self, knowledge_base_id: int) -> None:
        return None


class FakeLLMClient:
    """可配置启用状态的假大模型客户端。"""

    def __init__(self, enabled: bool, chat_message: dict[str, Any] | None = None) -> None:
        self.enabled = enabled
        self.model = "test-model"
        self._chat_message = chat_message or {"role": "assistant", "content": "模型回答"}
        self.answer_calls: list[str] = []

    async def answer(self, prompt: str) -> str:
        self.answer_calls.append(prompt)
        return "兜底回答"

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None) -> dict[str, Any]:
        return self._chat_message


def _service(llm: FakeLLMClient, results: list[RetrievalResult]) -> tuple[ChatService, FakeMySQLRepository, FakeContextRepository]:
    mysql = FakeMySQLRepository()
    context = FakeContextRepository()
    tool_registry = SimpleToolRegistry([])
    service = ChatService(
        embedding=FakeEmbedding(),  # type: ignore[arg-type]
        repository=FakeVectorRepository(results),  # type: ignore[arg-type]
        llm_client=llm,  # type: ignore[arg-type]
        top_k=4,
        reference_limit=3,
        reference_max_chars=240,
        mysql_repository=mysql,  # type: ignore[arg-type]
        context_repository=context,  # type: ignore[arg-type]
        tool_registry=tool_registry,
        agent_executor=AgentExecutor(llm, tool_registry, max_rounds=3),  # type: ignore[arg-type]
    )
    return service, mysql, context


async def test_answer_fallback_path_persists_and_caches() -> None:
    """llm 未启用时走兜底回答，并持久化用户/助手消息、写入上下文。"""
    llm = FakeLLMClient(enabled=False)
    results = [RetrievalResult(text="退货请在7天内申请。", score=1.0, metadata={})]
    service, mysql, context = _service(llm, results)

    result = await service.answer("怎么退货", user_id=1)

    assert result.answer == "兜底回答"
    assert result.session_id  # 自动创建了会话
    assert mysql.created_sessions == [result.session_id]
    # 用户消息与助手消息各落库一条。
    roles = [m["role"] for m in mysql.messages]
    assert roles == ["user", "assistant"]
    # 本轮问答写入上下文缓存（user + assistant）。
    assert len(context.appended) == 2
    assert llm.answer_calls  # 走了兜底 answer


async def test_answer_function_calling_path_returns_model_content() -> None:
    """llm 启用且模型不调用工具时，直接返回模型回答。"""
    llm = FakeLLMClient(enabled=True, chat_message={"role": "assistant", "content": "您好，已为您处理。"})
    results = [RetrievalResult(text="参考资料。", score=1.0, metadata={})]
    service, mysql, _ = _service(llm, results)

    result = await service.answer("你好", user_id=1)

    assert result.answer == "您好，已为您处理。"
    assert not llm.answer_calls  # 未走兜底
    assert [m["role"] for m in mysql.messages] == ["user", "assistant"]


async def test_answer_reuses_existing_session_id() -> None:
    llm = FakeLLMClient(enabled=True, chat_message={"role": "assistant", "content": "ok"})
    service, mysql, _ = _service(llm, [])
    result = await service.answer("问题", user_id=1, session_id="existing-session")
    assert result.session_id == "existing-session"
    assert mysql.created_sessions == []  # 不重复创建会话


async def test_answer_rag_test_mode_skips_model() -> None:
    """RAG 测试模式只返回检索调试信息，不调用模型、不落库。"""
    llm = FakeLLMClient(enabled=True)
    results = [RetrievalResult(text="片段", score=0.9, metadata={})]
    service, mysql, _ = _service(llm, results)

    result = await service.answer("问题", user_id=1, rag_test=True)

    assert result.rag_test is True
    assert result.rag_debug is not None
    assert mysql.messages == []  # 测试模式不落库
