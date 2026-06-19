"""RAG 文档导入公共流程。"""

from pathlib import Path

from app.rag.parser import parse_document
from app.rag.splitter import split_text


def parse_file_chunks(path: Path, chunk_size: int, chunk_overlap: int) -> list[str]:
    """解析文档并按配置切块，确保返回非空 chunk 列表。

    Args:
        path: 目标文件路径或请求路径。
        chunk_size: 单个文本切块的最大字符数。
        chunk_overlap: 相邻文本切块之间的重叠字符数。
    """
    text = parse_document(path)
    chunks = split_text(text, chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("文档内容为空，无法导入知识库")
    return chunks
