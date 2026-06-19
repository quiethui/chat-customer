"""聊天服务。"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from uuid import uuid4

from app.llm.OpenAI import OpenAIClient
from app.rag.embedding import HashEmbedding
from app.rag.prompt import build_customer_prompt
from app.rag.selection import build_references, select_prompt_contexts
from app.repositories.context_repository import ContextRepository
from app.repositories.mysql_repository import MySQLRepository
from app.repositories.vector import VectorRepository, VectorSearchFilter
from app.services.chat_debug import build_rag_debug, format_rag_debug_answer
from app.tools.registry import SimpleToolRegistry


logger = logging.getLogger(__name__)


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
            tool_registry: Tool Calling 工具注册表实例。
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

    async def answer(
        self,
        question: str,
        user_id: int,
        session_id: str | None = None,
        rag_test: bool = False,
        knowledge_base_ids: list[int] | None = None,
        file_ids: list[int] | None = None,
    ) -> AnswerResult:
        """基于问题检索知识库、调用业务工具、读取上下文并生成答案。

        Args:
            question: 用户本轮输入的问题。
            user_id: 当前登录用户 ID，用于会话、消息和业务数据隔离。
            session_id: 可选聊天会话 ID；为空时自动创建新会话。
            rag_test: 是否开启 RAG 测试模式；开启后只返回检索结果和 Prompt。
            knowledge_base_ids: 可选知识库过滤 ID 列表。
            file_ids: 可选文件过滤 ID 列表。

        Returns:
            包含回答、参考片段、会话 ID 和最终 Prompt 的回答结果。
        """
        # 没有会话 ID 时创建新会话，返回本轮使用的 session_id。
        session_id = session_id or self._create_session(user_id, question)
        # 读取最近聊天上下文，返回可放入 Prompt 的历史消息列表。
        history = self._get_history(user_id, session_id)
        # 调用可匹配的业务工具，返回用户可见的工具结果文本。
        tool_results = self._call_tools(user_id, question, rag_test)

        # RAG 主流程：问题向量化 -> 向量检索 -> 精选上下文 -> 拼接 Prompt -> 调用模型。
        start_time = perf_counter()
        # 将用户问题转成向量，供向量库相似度检索使用。
        query_vector = self.embedding.embed(question)
        # 多文件知识库下，如果只从向量库取 TOP_K 个候选，相关 chunk 容易被其他文件挤掉。
        # 这里扩大候选池，再用关键词重排精选进入 Prompt，保持回答内容不膨胀。
        search_limit = max(self.top_k, min(self.top_k * 5, 30))
        # 默认只检索 active 文件，避免 failed/deleted/processing 的残留向量进入回答。
        filters = VectorSearchFilter(
            knowledge_base_ids=[str(item) for item in knowledge_base_ids] if knowledge_base_ids else None,
            file_ids=[str(item) for item in file_ids] if file_ids else None,
            file_statuses=["active"],
        )
        # 根据问题向量检索知识库，返回候选知识片段。
        results = self.repository.search(query_vector, search_limit, filters)
        # 从候选片段中精选最适合放入 Prompt 的上下文。
        contexts = select_prompt_contexts(question, results, self.top_k)
        # 组装客服回答 Prompt，包含问题、知识库上下文、历史消息和工具结果。
        prompt = build_customer_prompt(question, contexts, history, tool_results)
        if rag_test:
            elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
            # 构造 RAG 调试信息，返回检索耗时、候选片段和最终 Prompt。
            rag_debug = build_rag_debug(
                results,
                contexts,
                prompt,
                search_limit,
                elapsed_ms,
                self._get_knowledge_base_name,
            )
            # 将结构化调试信息格式化成便于页面展示的文本回答。
            answer = format_rag_debug_answer(rag_debug)
            return AnswerResult(
                answer=answer,
                references=[],
                session_id=session_id,
                prompt=prompt,
                rag_test=True,
                rag_debug=rag_debug,
            )

        # 用户消息先落库，确保即使后续模型调用失败也能保留用户输入。
        self.mysql_repository.add_chat_message(session_id, user_id, "user", question)
        self.mysql_repository.commit()
        # 调用大模型生成最终客服回答，返回回答文本。
        answer = await self.llm_client.answer(prompt)
        # 根据入选上下文生成引用列表，返回给前端展示回答依据。
        references = build_references(question, contexts, self.reference_limit, self.reference_max_chars)
        if tool_results:
            references = [*tool_results, *references]

        # 保存助手回复及引用，便于后续查看会话记录。
        self.mysql_repository.add_chat_message(
            session_id,
            user_id,
            "assistant",
            answer,
            self.llm_client.model,
            references=references,
        )
        # 将本轮问答追加到 Redis 上下文，供下一轮对话使用。
        self._append_context(user_id, session_id, question, answer)
        return AnswerResult(answer=answer, references=references, session_id=session_id, prompt=prompt)

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

    def _call_tools(self, user_id: int, question: str, rag_test: bool) -> list[str]:
        """按当前模式调用可用工具。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            question: 用户输入的问题文本。
            rag_test: 是否开启 RAG 测试模式。
        """
        if rag_test:
            return []
        return [item.content for item in self.tool_registry.call(user_id, question)]

    def _create_session(self, user_id: int, question: str) -> str:
        """为未指定会话的提问自动创建会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            question: 用户输入的问题文本。
        """
        session_id = uuid4().hex
        title = question.strip()[:120] or "新对话"
        self.mysql_repository.create_chat_session(session_id, user_id, title, question, question[:120])
        return session_id

    def _get_history(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        """优先从 Redis 读取历史上下文，缓存缺失时回源 MySQL。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        try:
            cached_messages = self.context_repository.get_messages(user_id, session_id)
        except Exception:
            logger.warning("读取 Redis 聊天上下文失败：user_id=%s session_id=%s", user_id, session_id, exc_info=True)
            cached_messages = []
        if cached_messages:
            return cached_messages

        db_messages = self.mysql_repository.list_recent_messages(user_id, session_id, 10)
        messages = [
            {"role": item.role, "content": item.content}
            for item in db_messages
            if item.role in {"user", "assistant"}
        ]
        try:
            self.context_repository.replace_messages(user_id, session_id, messages)
        except Exception:
            logger.warning("回填 Redis 聊天上下文失败：user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        return messages

    def _append_context(self, user_id: int, session_id: str, question: str, answer: str) -> None:
        """将本轮问答追加到 Redis 上下文缓存。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            question: 用户输入的问题文本。
            answer: 本轮生成的客服回答。
        """
        try:
            self.context_repository.append_messages(
                user_id,
                session_id,
                [{"role": "user", "content": question}, {"role": "assistant", "content": answer}],
            )
        except Exception:
            logger.warning("追加 Redis 聊天上下文失败：user_id=%s session_id=%s", user_id, session_id, exc_info=True)
