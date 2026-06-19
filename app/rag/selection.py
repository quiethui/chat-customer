"""RAG 检索上下文选择与引用整理工具。"""

from dataclasses import dataclass

from app.repositories.vector import RetrievalResult
from app.rag.text_utils import QA_ENTRY_PATTERN, keyword_score, normalize_dedupe_key, normalize_spaces


@dataclass(frozen=True)
class _TextCandidate:
    """待排序和去重的候选文本。"""

    text: str
    order: int


def select_prompt_contexts(question: str, results: list[RetrievalResult], limit: int) -> list[str]:
    """从向量检索结果中选择传给大模型的最相关文本片段。

    Args:
        question: 用户输入的问题文本。
        results: 向量检索返回的候选结果列表。
        limit: 最多返回或保留的记录数量。
    """
    if limit <= 0:
        return []

    candidates = _collect_context_candidates(results)
    sorted_candidates = _sort_candidates(question, candidates)

    contexts: list[str] = []
    seen: set[str] = set()
    for candidate in sorted_candidates:
        key = normalize_dedupe_key(candidate.text)
        if key in seen:
            continue
        contexts.append(candidate.text)
        seen.add(key)
        if len(contexts) >= limit:
            break
    return contexts


def build_references(question: str, contexts: list[str], limit: int, max_chars: int) -> list[str]:
    """从检索上下文生成短而相关的引用列表。

    Args:
        question: 用户输入的问题文本。
        contexts: 用于拼接 Prompt 或引用的上下文文本列表。
        limit: 最多返回或保留的记录数量。
        max_chars: 单条文本保留的最大字符数。
    """
    if limit <= 0 or max_chars <= 0:
        return []

    candidates = _collect_reference_candidates(contexts, max_chars)
    sorted_candidates = _sort_candidates(question, candidates)

    references: list[str] = []
    seen: set[str] = set()
    for candidate in sorted_candidates:
        reference = _clip_reference(candidate.text, max_chars)
        key = normalize_dedupe_key(reference)
        if not reference or key in seen:
            continue
        references.append(reference)
        seen.add(key)
        if len(references) >= limit:
            break
    return references


def _collect_context_candidates(results: list[RetrievalResult]) -> list[_TextCandidate]:
    """将检索结果拆成更细粒度的候选上下文。

    Args:
        results: 向量检索返回的候选结果列表。
    """
    candidates: list[_TextCandidate] = []
    for result_index, result in enumerate(results):
        snippets = _extract_qa_snippets(result.text) or [result.text]
        for snippet_index, snippet in enumerate(snippets):
            candidates.append(_TextCandidate(snippet.strip(), result_index * 10000 + snippet_index))
    return candidates


def _collect_reference_candidates(contexts: list[str], max_chars: int) -> list[_TextCandidate]:
    """收集可作为引用展示的候选文本。

    Args:
        contexts: 用于拼接 Prompt 或引用的上下文文本列表。
        max_chars: 单条文本保留的最大字符数。
    """
    candidates: list[_TextCandidate] = []
    for context in contexts:
        qa_references = _extract_qa_references(context)
        references = qa_references or [_clip_reference(context, max_chars)]
        for reference in references:
            candidates.append(_TextCandidate(reference.strip(), len(candidates)))
    return candidates


def _sort_candidates(question: str, candidates: list[_TextCandidate]) -> list[_TextCandidate]:
    """按问题关键词重合度和原始顺序排序候选文本。

    Args:
        question: 用户输入的问题文本。
        candidates: 待排序的候选文本列表。
    """
    return sorted(
        (candidate for candidate in candidates if candidate.text),
        key=lambda candidate: (-keyword_score(question, candidate.text), candidate.order),
    )


def _extract_qa_snippets(text: str) -> list[str]:
    """从包含多条商城问答的 chunk 中拆出独立问答。

    Args:
        text: 待处理的文本内容。
    """
    return [normalize_spaces(match.group(1)) for match in QA_ENTRY_PATTERN.finditer(text)]


def _extract_qa_references(text: str) -> list[str]:
    """从商城问答 demo 文本中提取完整问答引用。

    Args:
        text: 待处理的文本内容。
    """
    return [
        _trim_to_sentence(match.group(1).strip())
        for match in QA_ENTRY_PATTERN.finditer(text)
        if "答：" in match.group(1)
    ]


def _clip_reference(text: str, max_chars: int) -> str:
    """将引用裁剪为适合前端展示的短文本。

    Args:
        text: 待处理的文本内容。
        max_chars: 单条文本保留的最大字符数。
    """
    normalized = normalize_spaces(text)
    if len(normalized) <= max_chars:
        return normalized

    clipped = normalized[:max_chars].rstrip()
    sentence = _trim_to_sentence(clipped)
    if len(sentence) >= max_chars // 2:
        return f"{sentence}……"
    return f"{clipped}……"


def _trim_to_sentence(text: str) -> str:
    """尽量在句末标点处结束引用，避免半句话展示。

    Args:
        text: 待处理的文本内容。
    """
    stripped = text.strip()
    punctuation_positions = [stripped.rfind(mark) for mark in "。！？；!?;"]
    last_position = max(punctuation_positions)
    if last_position == -1:
        return stripped
    return stripped[: last_position + 1]
