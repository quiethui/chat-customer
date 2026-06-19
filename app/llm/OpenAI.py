"""OpenAI 兼容客户端。"""

from openai import AsyncOpenAI


class OpenAIClient:
    """OpenAI 兼容聊天客户端，未配置远程模型时自动走本地兜底回答。"""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str,
        fallback_reference_limit: int = 3,
        fallback_reference_max_chars: int = 240,
    ) -> None:
        """初始化 OpenAI 兼容客户端。

        Args:
            api_key: OpenAI 兼容接口的访问密钥。
            base_url: OpenAI 兼容接口的基础地址。
            model: OpenAI 兼容接口使用的模型名称。
            fallback_reference_limit: 本地兜底回答可使用的参考内容数量上限。
            fallback_reference_max_chars: 单条参考内容在本地兜底回答中的最大字符数。
        """
        self.model = model
        self.fallback_reference_limit = fallback_reference_limit
        self.fallback_reference_max_chars = fallback_reference_max_chars
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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


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
