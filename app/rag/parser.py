"""文档解析工具。"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}  # 上传接口允许导入的知识库文件后缀。


def parse_document(path: Path) -> str:
    """根据文件后缀解析文档正文，返回可切块的纯文本内容。

    Args:
        path: 目标文件路径或请求路径。
    """
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"不支持的文件类型：{suffix}")
