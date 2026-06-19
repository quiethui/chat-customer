"""RAG 文本处理公共工具。"""

import re


QA_ENTRY_PATTERN = re.compile(
    r"(?:^|\n)(?:\[\d+\]\s*)?(\d{3}\.\s*问：.*?答：.*?)(?=\n(?:\[\d+\]\s*)?\d{3}\.\s*问：|\Z)",
    re.S,
)


def keyword_score(question: str, text: str) -> int:
    """按问题关键词与候选文本的重合度打分。

    Args:
        question: 用户输入的问题文本。
        text: 待处理的文本内容。
    """
    question_tokens = set(tokenize_mixed_text(question))
    text_tokens = set(tokenize_mixed_text(text))
    return len(question_tokens & text_tokens)


def tokenize_mixed_text(text: str) -> list[str]:
    """生成适合中英文混合文本的轻量关键词。

    Args:
        text: 待处理的文本内容。
    """
    normalized = text.lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    chinese_bigrams = [
        "".join(chinese_chars[index : index + 2])
        for index in range(max(0, len(chinese_chars) - 1))
    ]
    return words + chinese_chars + chinese_bigrams


def normalize_spaces(text: str) -> str:
    """规范化文本中的连续空白字符。

    Args:
        text: 待处理的文本内容。
    """
    return re.sub(r"\s+", " ", text).strip()


def normalize_dedupe_key(text: str) -> str:
    """生成文本去重键。

    Args:
        text: 待处理的文本内容。
    """
    return re.sub(r"\W+", "", text).lower()
