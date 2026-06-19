"""OpenAI 兼容客户端。"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from time import perf_counter
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from app.repositories.mysql_repository import MySQLRepository


logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI 兼容聊天客户端，未配置远程模型时自动走本地兜底回答。"""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str,
        fallback_reference_limit: int = 3,
        fallback_reference_max_chars: int = 240,
        log_repository_factory: Callable[[], MySQLRepository] | None = None,
    ) -> None:
        """初始化 OpenAI 兼容客户端。

        Args:
            api_key: OpenAI 兼容接口的访问密钥。
            base_url: OpenAI 兼容接口的基础地址。
            model: OpenAI 兼容接口使用的模型名称。
            fallback_reference_limit: 本地兜底回答可使用的参考内容数量上限。
            fallback_reference_max_chars: 单条参考内容在本地兜底回答中的最大字符数。
            log_repository_factory: 创建独立事务 MySQL 仓储的工厂，用于记录请求日志；为空时不落库。
        """
        self.model = model
        self.base_url = base_url
        self.fallback_reference_limit = fallback_reference_limit
        self.fallback_reference_max_chars = fallback_reference_max_chars
        self._log_repository_factory = log_repository_factory
        # 只要配置了 API Key 或 Base URL，就认为用户希望调用远程 OpenAI 兼容服务。
        self.enabled = bool(api_key or base_url)
        self.client = AsyncOpenAI(api_key=api_key or "not-needed", base_url=base_url) if self.enabled else None

    async def answer(self, prompt: str) -> str:
        """调用远程模型或本地 fallback 生成回答。

        Args:
            prompt: 提交给大模型的完整 Prompt。
        """
        if not self.client:
            return _fallback_answer(
                prompt,
                self.fallback_reference_limit,
                self.fallback_reference_max_chars,
            )
        message = await self.chat([{"role": "user", "content": prompt}])
        return str(message.get("content") or "")

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """调用 Chat Completions，并返回可序列化的消息字典。

        Args:
            messages: OpenAI Chat Completions 消息列表。
            tools: 可选 Function Calling 工具 schema 列表。

        Returns:
            模型返回的 assistant 消息，可能包含 tool_calls。
        """
        if not self.client:
            prompt = "\n\n".join(str(item.get("content") or "") for item in messages if item.get("role") == "user")
            return {
                "role": "assistant",
                "content": _fallback_answer(prompt, self.fallback_reference_limit, self.fallback_reference_max_chars),
            }
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        # 记录请求往返耗时，无论成功失败都尽量落库一条请求日志，便于排查与审计。
        start_time = perf_counter()
        try:
            response = await self.client.chat.completions.create(**request)
        except Exception as exc:
            latency_ms = int((perf_counter() - start_time) * 1000)
            await self._save_request_log(request, None, {}, latency_ms, "error", str(exc))
            raise
        latency_ms = int((perf_counter() - start_time) * 1000)
        # 保存完整响应数据，并从 usage 中提取 token 用量。
        response_payload = response.model_dump(exclude_none=True)
        usage = response_payload.get("usage") or {}
        await self._save_request_log(request, response_payload, usage, latency_ms, "success", None)
        return response.choices[0].message.model_dump(exclude_none=True)

    async def _save_request_log(
        self,
        request: dict[str, Any],
        response: dict[str, Any] | None,
        usage: dict[str, Any],
        latency_ms: int,
        status: str,
        error_message: str | None,
    ) -> None:
        """将一次请求的参数与响应写入日志表；落库失败只告警，不影响聊天主流程。

        Args:
            request: 提交给 Chat Completions 的完整请求参数。
            response: 模型完整响应的可序列化字典；请求失败时为 None。
            usage: 响应中的 token 用量信息，缺失时为空字典。
            latency_ms: 请求往返耗时（毫秒）。
            status: 请求结果状态，success 或 error。
            error_message: 请求失败时的错误摘要；成功时为 None。
        """
        if self._log_repository_factory is None:
            return
        try:
            # 写库为同步阻塞操作，放到线程池执行，避免阻塞事件循环。
            await asyncio.to_thread(
                self._persist_request_log, request, response, usage, latency_ms, status, error_message
            )
        except Exception:
            logger.warning("保存大模型请求日志失败：model=%s", self.model, exc_info=True)

    def _persist_request_log(
        self,
        request: dict[str, Any],
        response: dict[str, Any] | None,
        usage: dict[str, Any],
        latency_ms: int,
        status: str,
        error_message: str | None,
    ) -> None:
        """用独立事务的 MySQL 仓储写入单条请求日志。

        Args:
            request: 提交给 Chat Completions 的完整请求参数。
            response: 模型完整响应的可序列化字典；请求失败时为 None。
            usage: 响应中的 token 用量信息，缺失时为空字典。
            latency_ms: 请求往返耗时（毫秒）。
            status: 请求结果状态，success 或 error。
            error_message: 请求失败时的错误摘要；成功时为 None。
        """
        factory = self._log_repository_factory
        if factory is None:
            return
        repository = factory()
        try:
            repository.add_llm_request_log(
                model=self.model,
                base_url=self.base_url,
                request_payload=json.dumps(request, ensure_ascii=False, default=str),
                response_payload=(
                    json.dumps(response, ensure_ascii=False, default=str) if response is not None else None
                ),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                latency_ms=latency_ms,
                status=status,
                error_message=error_message[:1000] if error_message else None,
            )
            repository.commit()
        except Exception:
            repository.rollback()
            raise
        finally:
            repository.close()


def _fallback_answer(prompt: str, reference_limit: int, reference_max_chars: int) -> str:
    """在未配置远程模型时生成短回答。

    Args:
        prompt: 提交给大模型的完整 Prompt。
        reference_limit: 本地兜底回答可返回的引用数量上限。
        reference_max_chars: 单条引用在本地兜底回答中的最大字符数。
    """
    tool_marker = "内部业务查询结果"
    marker = "内部服务资料"
    question_marker = "用户问题："
    tool_context = _extract_prompt_section(prompt, tool_marker, marker)
    context = _extract_prompt_section(prompt, marker, question_marker)
    question = prompt.split(question_marker, 1)[-1].strip()
    # 工具结果通常比服务资料更精确，例如订单查询，因此本地兜底也优先返回工具结果。
    if tool_context and tool_context != "暂无业务查询结果":
        return f"您好，以下是我为您查到的信息：\n{_clean_fallback_text(tool_context)}"
    if not context or context == "暂无相关服务资料":
        return f"您好，目前我这边暂时没有查到明确说明。您可以补充更多信息，我帮您进一步确认。"
    references = _build_fallback_references(context, reference_limit, reference_max_chars)
    reference_text = "\n".join(f"- {reference}" for reference in references)
    return f"您好，关于“{question}”，可以这样处理：\n{reference_text}"


def _extract_prompt_section(prompt: str, start_marker: str, end_marker: str) -> str:
    """从 Prompt 中提取指定区块文本。"""
    if start_marker not in prompt:
        return ""
    section = prompt.split(start_marker, 1)[-1]
    section = section.split("：", 1)[-1] if "：" in section else section
    return section.split(end_marker, 1)[0].strip()


def _build_fallback_references(context: str, limit: int, max_chars: int) -> list[str]:
    """从内部参考内容中构建本地兜底回答条目。"""
    if limit <= 0:
        return []
    normalized = _normalize_spaces(_clean_fallback_text(context))
    if not normalized:
        return []
    return [_clip_reference(normalized, max_chars)][:limit]


def _clip_reference(text: str, max_chars: int) -> str:
    """按最大字符数裁剪单条参考内容。"""
    normalized = _normalize_spaces(text)
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}……"


def _clean_fallback_text(text: str) -> str:
    """清理本地兜底回答中不适合展示给用户的编号。"""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and "]" in stripped:
            stripped = stripped.split("]", 1)[-1].strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def _normalize_spaces(text: str) -> str:
    """将连续空白字符归一化为空格。"""
    return " ".join((text or "").split())
