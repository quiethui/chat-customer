"""文本切块工具。"""

from app.rag.text_utils import QA_ENTRY_PATTERN


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    """按文本块切分知识库内容，尽量避免截断问答条目。

    Args:
        text: 待处理的文本内容。
        chunk_size: 单个文本切块的最大字符数。
        chunk_overlap: 相邻文本切块之间的重叠字符数。
    """
    blocks = _split_blocks(text)
    if not blocks:
        return []
    if _contains_qa_entries(blocks):
        return _split_qa_blocks(blocks, chunk_size, chunk_overlap)

    chunks: list[str] = []
    current = ""
    for block in blocks:
        # 优先把多个短段落合并成一个 chunk，降低向量库写入数量。
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(block) <= chunk_size:
            current = block
        else:
            chunks.extend(_split_long_block(block, chunk_size, chunk_overlap))
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _split_blocks(text: str) -> list[str]:
    """按空行切分文本块，保留商城问答条目的完整性。

    Args:
        text: 待处理的文本内容。
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = normalized.split("\n\n")
    return ["\n".join(line.strip() for line in block.splitlines() if line.strip()) for block in raw_blocks if block.strip()]


def _contains_qa_entries(blocks: list[str]) -> bool:
    """判断文本块是否包含商城问答条目。

    Args:
        blocks: 按段落拆分后的文本块列表。
    """
    return any(_extract_qa_entries(block) for block in blocks)


def _split_qa_blocks(blocks: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """将商城问答条目按单条问答切为向量 chunk。

    Args:
        blocks: 按段落拆分后的文本块列表。
        chunk_size: 单个文本切块的最大字符数。
        chunk_overlap: 相邻文本切块之间的重叠字符数。
    """
    chunks: list[str] = []
    for block in blocks:
        entries = _extract_qa_entries(block)
        if entries:
            for entry in entries:
                chunks.extend(_fit_chunk_size(entry, chunk_size, chunk_overlap))
        else:
            chunks.extend(_fit_chunk_size(block, chunk_size, chunk_overlap))
    return chunks


def _extract_qa_entries(text: str) -> list[str]:
    """从文本中提取独立商城问答条目。

    Args:
        text: 待处理的文本内容。
    """
    return [match.group(1).strip() for match in QA_ENTRY_PATTERN.finditer(text)]


def _fit_chunk_size(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """确保单条文本不超过 chunk 大小限制。

    Args:
        text: 待处理的文本内容。
        chunk_size: 单个文本切块的最大字符数。
        chunk_overlap: 相邻文本切块之间的重叠字符数。
    """
    if len(text) <= chunk_size:
        return [text]
    return _split_long_block(text, chunk_size, chunk_overlap)


def _split_long_block(block: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """超长文本块退化为重叠字符切块。

    Args:
        block: 待继续切分的单个长文本块。
        chunk_size: 单个文本切块的最大字符数。
        chunk_overlap: 相邻文本切块之间的重叠字符数。
    """
    chunks: list[str] = []
    start = 0
    # 使用 overlap 保留上下文，避免答案依据刚好被切断在两个 chunk 之间。
    step = max(1, chunk_size - chunk_overlap)
    while start < len(block):
        chunk = block[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
