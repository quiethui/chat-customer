"""聊天服务。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.agent import AgentExecutor
from app.llm.openai_client import OpenAIClient, split_for_stream
from app.rag.embedding import HashEmbedding
from app.rag.prompt import build_customer_prompt
from app.rag.selection import build_references, select_prompt_contexts
from app.repositories.context_repository import ContextRepository
from app.repositories.mysql_repository import MySQLRepository
from app.repositories.vector import RetrievalResult, VectorRepository, VectorSearchFilter
from app.services.chat_debug import build_rag_debug, format_rag_debug_answer
from app.tools.registry import SimpleToolRegistry


logger = logging.getLogger(__name__)


# 向量检索候选池相对 TOP_K 的放大倍数与绝对上限：多文件知识库下扩大候选池，
# 再用关键词重排精选进入 Prompt，避免相关 chunk 被其他文件挤掉。
_SEARCH_POOL_MULTIPLIER = 5
_SEARCH_POOL_MAX = 30


@dataclass
class AnswerResult:
    """聊天服务生成一次回答后的完整结果。"""

    answer: str  # 大模型生成的最终客服回答。
    references: list[str]  # 回答依据，包含知识库引用和可见的工具查询结果。
    session_id: str  # 本次问答所属会话 ID。
    prompt: str  # 实际提交给模型的 Prompt，便于排查回答质量。
    rag_test: bool = False  # 是否为 RAG 测试响应。
    rag_debug: dict | None = None  # RAG 测试模式下返回的结构化调试信息。


class ChatService:
    """串联上下文、工具调用、向量检索和大模型生成的聊天编排服务。"""

    def __init__(
        self,
        embedding: HashEmbedding,
        repository: VectorRepository,
        llm_client: OpenAIClient,
        top_k: int,
        reference_limit: int,
        reference_max_chars: int,
        mysql_repository: MySQLRepository,
        context_repository: ContextRepository,
        tool_registry: SimpleToolRegistry,
        agent_executor: AgentExecutor,
    ) -> None:
        """初始化聊天服务依赖和引用展示配置。

        Args:
            embedding: 文本向量化服务实例。
            repository: 当前服务使用的数据仓储实例。
            llm_client: OpenAI 兼容大模型客户端实例。
            top_k: 向量检索返回的候选数量。
            reference_limit: 本地兜底回答可返回的引用数量上限。
            reference_max_chars: 单条引用在本地兜底回答中的最大字符数。
            mysql_repository: MySQL 数据仓储实例。
            context_repository: 聊天上下文仓储实例。
            tool_registry: Tool Calling 工具注册表实例，供本地 fallback 关键词触发使用。
            agent_executor: 远程模型 Function Calling 工具调用执行器。
        """
        self.embedding = embedding
        self.repository = repository
        self.llm_client = llm_client
        self.top_k = top_k
        self.reference_limit = reference_limit
        self.reference_max_chars = reference_max_chars
        self.mysql_repository = mysql_repository
        self.context_repository = context_repository
        self.tool_registry = tool_registry
        self.agent_executor = agent_executor

    async def answer(
        self,
        question: str,
        customer_id: int,
        session_id: str | None = None,
        rag_test: bool = False,
        knowledge_base_ids: list[int] | None = None,
        file_ids: list[int] | None = None,
    ) -> AnswerResult:
        """基于问题检索知识库、调用业务工具、读取上下文并生成答案。

        Args:
            question: 客户本轮输入的问题。
            customer_id: 当前客户 ID，用于会话、消息和业务数据隔离。
            session_id: 可选聊天会话 ID；为空时自动创建新会话。
            rag_test: 是否开启 RAG 测试模式；开启后只返回检索结果和 Prompt。
            knowledge_base_ids: 可选知识库过滤 ID 列表。
            file_ids: 可选文件过滤 ID 列表。

        Returns:
            包含回答、参考片段、会话 ID 和最终 Prompt 的回答结果。
        """
        # 没有会话 ID 时创建新会话，返回本轮使用的 session_id。
        session_id = session_id or self._create_session(customer_id, question)
        # 读取最近聊天上下文，返回可放入 Prompt 的历史消息列表。
        history = self._get_history(customer_id, session_id)

        # RAG 检索：问题向量化 -> 向量检索 -> 精选上下文。向量数据库服务异常时不中断服务。
        start_time = perf_counter()
        try:
            results, contexts, search_limit = self._retrieve(question, knowledge_base_ids, file_ids)
        except Exception:
            logger.warning(
                "向量检索失败，将不使用知识库上下文：customer_id=%s session_id=%s",
                customer_id,
                session_id,
                exc_info=True,
            )
            results, contexts, search_limit = [], [], 0
        if rag_test:
            return self._build_rag_test_result(question, contexts, history, results, search_limit, start_time, session_id)

        # 客户消息先落库，确保即使后续模型调用失败也能保留客户输入。
        self.mysql_repository.add_chat_message(session_id, customer_id, "user", question, sender_type="customer")
        self.mysql_repository.commit()

        # 远程模型走 Function Calling，本地 fallback 走关键词触发，各自返回真正提交给模型的 Prompt。
        answer, tool_results, prompt = await self._generate(customer_id, question, contexts, history)
        # 生成回答依据：业务工具结果优先，其后接知识库引用。
        references = self._build_references(question, contexts, tool_results)
        # 保存助手回复及引用，并把本轮问答写入 Redis 上下文，供下一轮对话使用。
        self._persist_and_cache(customer_id, session_id, question, answer, references)
        return AnswerResult(answer=answer, references=references, session_id=session_id, prompt=prompt)

    async def answer_stream(
        self,
        question: str,
        customer_id: int,
        session_id: str | None = None,
        knowledge_base_ids: list[int] | None = None,
        file_ids: list[int] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式回答：工具轮在服务端跑，最终回答逐段下发。

        事件序列：先 `status`（提示进度），再若干 `delta`（逐段回答），最后 `done`
        （携带 references 与 session_id）。工具调用与持久化均在服务端完成，客户端只消费回答增量。

        Args:
            question: 客户本轮输入的问题。
            customer_id: 当前客户 ID，用于会话、消息和业务数据隔离。
            session_id: 可选聊天会话 ID；为空时自动创建新会话。
            knowledge_base_ids: 可选知识库过滤 ID 列表。
            file_ids: 可选文件过滤 ID 列表。

        Yields:
            SSE 事件字典，包含 type 及对应字段（message / text / references / session_id）。
        """
        session_id = session_id or self._create_session(customer_id, question)
        history = self._get_history(customer_id, session_id)

        # RAG 检索：向量数据库服务异常时不中断服务，contexts 置空，只用历史上下文和工具回答。
        try:
            _, contexts, _ = self._retrieve(question, knowledge_base_ids, file_ids)
        except Exception:
            logger.warning(
                "向量检索失败，将不使用知识库上下文：customer_id=%s session_id=%s",
                customer_id,
                session_id,
                exc_info=True,
            )
            contexts = []

        # 客户消息先落库并提交，确保即使后续模型调用失败也能保留客户输入。
        self.mysql_repository.add_chat_message(session_id, customer_id, "user", question, sender_type="customer")
        self.mysql_repository.commit()
        yield {"type": "status", "message": "正在思考…", "session_id": session_id}

        if self.llm_client.enabled:
            # 远程模型路径：交给 AgentExecutor 在服务端跑完工具轮，再把最终回答逐段下发。
            prompt = build_customer_prompt(question, contexts, history, None)
            run_result = await self.agent_executor.run(customer_id, prompt)
            tool_results = run_result.tool_results
            if tool_results:
                yield {"type": "status", "message": "已为您查询到相关业务信息", "session_id": session_id}
            answer = run_result.answer
            for piece in split_for_stream(answer):
                yield {"type": "delta", "text": piece}
        else:
            # 本地 fallback：关键词触发工具后，用 stream_answer 逐段产出兜底回答。
            tool_results = [item.content for item in self.tool_registry.call(customer_id, question)]
            if tool_results:
                yield {"type": "status", "message": "已为您查询到相关业务信息", "session_id": session_id}
            prompt = build_customer_prompt(question, contexts, history, tool_results)
            collected: list[str] = []
            async for piece in self.llm_client.stream_answer(prompt):
                collected.append(piece)
                yield {"type": "delta", "text": piece}
            answer = "".join(collected)

        references = self._build_references(question, contexts, tool_results)
        self._persist_and_cache(customer_id, session_id, question, answer, references)
        self.mysql_repository.commit()
        yield {"type": "done", "references": references, "session_id": session_id}

    def _retrieve(
        self,
        question: str,
        knowledge_base_ids: list[int] | None,
        file_ids: list[int] | None,
    ) -> tuple[list[RetrievalResult], list[str], int]:
        """向量化问题并检索知识库，返回候选结果、精选上下文和本次候选数量。

        Args:
            question: 客户本轮输入的问题。
            knowledge_base_ids: 可选知识库过滤 ID 列表。
            file_ids: 可选文件过滤 ID 列表。

        Returns:
            向量检索候选结果、精选进入 Prompt 的上下文，以及本次检索候选数量。
        """
        # 将客户问题转成向量，供向量库相似度检索使用。
        query_vector = self.embedding.embed(question)
        search_limit = max(self.top_k, min(self.top_k * _SEARCH_POOL_MULTIPLIER, _SEARCH_POOL_MAX))
        # 默认只检索 active 文件，避免 failed/deleted/processing 的残留向量进入回答。
        filters = VectorSearchFilter(
            knowledge_base_ids=[str(item) for item in knowledge_base_ids] if knowledge_base_ids else None,
            file_ids=[str(item) for item in file_ids] if file_ids else None,
            file_statuses=["active"],
        )
        # 根据问题向量检索知识库，并从候选片段中精选最适合放入 Prompt 的上下文。
        results = self.repository.search(query_vector, search_limit, filters)
        contexts = select_prompt_contexts(question, results, self.top_k)
        return results, contexts, search_limit

    def _build_rag_test_result(
        self,
        question: str,
        contexts: list[str],
        history: list[dict[str, str]],
        results: list[RetrievalResult],
        search_limit: int,
        start_time: float,
        session_id: str,
    ) -> AnswerResult:
        """组装 RAG 测试模式响应：只返回检索结果和 Prompt，不调用模型。

        Args:
            question: 客户本轮输入的问题。
            contexts: 精选进入 Prompt 的上下文片段。
            history: 当前会话的最近历史消息。
            results: 向量检索返回的候选结果列表。
            search_limit: 本次向量检索候选数量。
            start_time: RAG 检索开始时间戳，用于统计耗时。
            session_id: 本轮问答所属会话 ID。

        Returns:
            携带结构化调试信息的回答结果。
        """
        prompt = build_customer_prompt(question, contexts, history, [])
        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        # 构造 RAG 调试信息，返回检索耗时、候选片段和最终 Prompt。
        rag_debug = build_rag_debug(results, contexts, prompt, search_limit, elapsed_ms, self._get_knowledge_base_name)
        # 将结构化调试信息格式化成便于页面展示的文本回答。
        return AnswerResult(
            answer=format_rag_debug_answer(rag_debug),
            references=[],
            session_id=session_id,
            prompt=prompt,
            rag_test=True,
            rag_debug=rag_debug,
        )

    async def _generate(
        self,
        customer_id: int,
        question: str,
        contexts: list[str],
        history: list[dict[str, str]],
    ) -> tuple[str, list[str], str]:
        """按模型可用性生成回答，返回回答、可见工具结果和真正提交给模型的 Prompt。

        Args:
            customer_id: 当前客户 ID，用于工具执行时的数据隔离。
            question: 客户本轮输入的问题。
            contexts: 精选进入 Prompt 的上下文片段。
            history: 当前会话的最近历史消息。

        Returns:
            模型最终回答、可展示的工具结果文本列表，以及真正提交给模型的 Prompt。
        """
        if self.llm_client.enabled:
            # 远程模型路径：交给 AgentExecutor 驱动工具调用循环。模型基于工具 schema 自主
            # 决定是否调用工具，工具结果通过独立 tool 消息回传，因此首轮 Prompt 即为真正
            # 提交给模型的内容。
            prompt = build_customer_prompt(question, contexts, history, None)
            run_result = await self.agent_executor.run(customer_id, prompt)
            if run_result.trace:
                logger.info(
                    "Agent 工具调用完成：customer_id=%s rounds=%s tools=%s",
                    customer_id,
                    run_result.rounds,
                    [step.name for step in run_result.trace],
                )
            return run_result.answer, run_result.tool_results, prompt
        # 本地 fallback 没有模型工具选择能力，只保留旧的关键词触发以便离线演示可用。
        tool_results = [item.content for item in self.tool_registry.call(customer_id, question)]
        prompt = build_customer_prompt(question, contexts, history, tool_results)
        answer = await self.llm_client.answer(prompt)
        return answer, tool_results, prompt

    def _build_references(self, question: str, contexts: list[str], tool_results: list[str]) -> list[str]:
        """生成回答依据列表：业务工具结果优先展示，其后接知识库引用。

        Args:
            question: 客户本轮输入的问题。
            contexts: 精选进入 Prompt 的上下文片段。
            tool_results: 本轮成功执行的可见工具结果文本列表。

        Returns:
            返回给前端展示的回答依据列表。
        """
        references = build_references(question, contexts, self.reference_limit, self.reference_max_chars)
        if tool_results:
            return [*tool_results, *references]
        return references

    def _persist_and_cache(
        self,
        customer_id: int,
        session_id: str,
        question: str,
        answer: str,
        references: list[str],
    ) -> None:
        """保存助手回复并将本轮问答写入 Redis 上下文缓存。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 本轮问答所属会话 ID。
            question: 客户本轮输入的问题。
            answer: 本轮生成的客服回答。
            references: 本轮回答的引用依据列表。
        """
        # 保存助手回复及引用（发送方为机器人），便于后续查看会话记录。
        self.mysql_repository.add_chat_message(
            session_id, customer_id, "assistant", answer, self.llm_client.model, references=references, sender_type="bot",
        )
        # 将本轮问答追加到 Redis 上下文，供下一轮对话使用。
        self._append_context(customer_id, session_id, question, answer)

    def _get_knowledge_base_name(self, knowledge_base_id: str | None, cache: dict[str, str]) -> str | None:
        """根据知识库 ID 查询知识库名称，并使用本次请求内缓存减少数据库查询。

        Args:
            knowledge_base_id: 知识库 ID。
            cache: 知识库名称缓存字典。
        """
        if not knowledge_base_id:
            return None
        if knowledge_base_id in cache:
            return cache[knowledge_base_id]
        try:
            record = self.mysql_repository.get_knowledge_base(int(knowledge_base_id))
        except (TypeError, ValueError):
            record = None
        if not record:
            return None
        cache[knowledge_base_id] = record.name
        return record.name

    def _create_session(self, customer_id: int, question: str) -> str:
        """为未指定会话的提问自动创建会话。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            question: 客户输入的问题文本。
        """
        session_id = uuid4().hex
        title = question.strip()[:120] or "新对话"
        self.mysql_repository.create_chat_session(session_id, customer_id, title, question, question[:120])
        return session_id

    def _get_history(self, customer_id: int, session_id: str) -> list[dict[str, str]]:
        """优先从 Redis 读取历史上下文，缓存缺失时回源 MySQL。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        try:
            cached_messages = self.context_repository.get_messages(customer_id, session_id)
        except Exception:
            logger.warning("读取 Redis 聊天上下文失败：customer_id=%s session_id=%s", customer_id, session_id, exc_info=True)
            cached_messages = []
        if cached_messages:
            return cached_messages

        db_messages = self.mysql_repository.list_recent_messages(customer_id, session_id, 10)
        messages = [
            {"role": item.role, "content": item.content}
            for item in db_messages
            if item.role in {"user", "assistant"}
        ]
        try:
            self.context_repository.replace_messages(customer_id, session_id, messages)
        except Exception:
            logger.warning("回填 Redis 聊天上下文失败：customer_id=%s session_id=%s", customer_id, session_id, exc_info=True)
        return messages

    def _append_context(self, customer_id: int, session_id: str, question: str, answer: str) -> None:
        """将本轮问答追加到 Redis 上下文缓存。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            question: 客户输入的问题文本。
            answer: 本轮生成的客服回答。
        """
        try:
            self.context_repository.append_messages(
                customer_id,
                session_id,
                [{"role": "user", "content": question}, {"role": "assistant", "content": answer}],
            )
        except Exception:
            logger.warning("追加 Redis 聊天上下文失败：customer_id=%s session_id=%s", customer_id, session_id, exc_info=True)
