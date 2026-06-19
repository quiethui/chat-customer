"""聊天 RAG 调试信息构建工具。"""

from collections.abc import Callable
from typing import Any

from app.repositories.vector import RetrievalResult

KnowledgeBaseNameGetter = Callable[[str | None, dict[str, str]], str | None]


def build_rag_debug(
    results: list[RetrievalResult],
    contexts: list[str],
    prompt: str,
    search_limit: int,
    elapsed_ms: float,
    knowledge_base_name_getter: KnowledgeBaseNameGetter,
) -> dict[str, Any]:
    """构建 RAG 测试模式的结构化调试信息。

    Args:
        results: 向量检索返回的候选结果列表。
        contexts: 用于拼接 Prompt 或引用的上下文文本列表。
        prompt: 提交给大模型的完整 Prompt。
        search_limit: 向量检索阶段使用的候选数量。
        elapsed_ms: RAG 检索和组装过程耗时，单位毫秒。
        knowledge_base_name_getter: 按知识库 ID 获取知识库名称的回调函数。
    """
    context_keys = {_normalize_debug_text(context) for context in contexts}
    knowledge_base_name_cache: dict[str, str] = {}
    chunks: list[dict[str, Any]] = []
    for rank, result in enumerate(results, start=1):
        metadata = result.metadata or {}
        knowledge_base_id = metadata.get("knowledge_base_id") or None
        knowledge_base_name = knowledge_base_name_getter(knowledge_base_id, knowledge_base_name_cache)
        chunks.append(
            {
                "rank": rank,
                "score": round(float(result.score), 6),
                "content": result.text,
                "fileName": metadata.get("file_name") or None,
                "fileId": metadata.get("file_id") or None,
                "knowledgeBaseId": knowledge_base_id,
                "knowledgeBaseName": knowledge_base_name,
                "vectorId": metadata.get("vector_id") or None,
                "documentId": metadata.get("document_id") or None,
                "usedInPrompt": _normalize_debug_text(result.text) in context_keys,
            }
        )
    return {
        "elapsedMs": elapsed_ms,
        "searchLimit": search_limit,
        "promptContextCount": len(contexts),
        "finalPrompt": prompt,
        "chunks": chunks,
    }


def format_rag_debug_answer(rag_debug: dict[str, Any]) -> str:
    """将 RAG 测试调试信息格式化为 Markdown，兼容普通聊天展示。

    Args:
        rag_debug: RAG 测试模式下的结构化调试数据。
    """
    lines = [
        "# RAG 测试结果",
        "",
        f"- 耗时：{rag_debug['elapsedMs']} ms",
        f"- 检索候选数：{rag_debug['searchLimit']}",
        f"- 进入 Prompt 的 Chunk 数：{rag_debug['promptContextCount']}",
        "",
        "## 命中 Chunks",
    ]
    for chunk in rag_debug["chunks"]:
        lines.extend(_format_debug_chunk(chunk))
    lines.extend(["", "## 最终 Prompt", "", "```text", rag_debug["finalPrompt"], "```"])
    return "\n".join(lines)


def _format_debug_chunk(chunk: dict[str, Any]) -> list[str]:
    """格式化单个调试 chunk。

    Args:
        chunk: 单个 RAG 调试 chunk 字典。
    """
    return [
        "",
        f"### #{chunk['rank']}  score={chunk['score']}",
        f"- 文件：{chunk.get('fileName') or '-'}",
        f"- 知识库：{chunk.get('knowledgeBaseName') or chunk.get('knowledgeBaseId') or '-'}",
        f"- File ID：{chunk.get('fileId') or '-'}",
        f"- Vector ID：{chunk.get('vectorId') or '-'}",
        f"- 进入 Prompt：{'是' if chunk.get('usedInPrompt') else '否'}",
        "",
        "```text",
        chunk.get("content") or "",
        "```",
    ]


def _normalize_debug_text(text: str) -> str:
    """生成 RAG 调试使用的文本去重键。

    Args:
        text: 待处理的文本内容。
    """
    return "".join((text or "").split())
