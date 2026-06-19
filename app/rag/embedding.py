"""Embedding 生成工具。"""

import hashlib
import logging
import math
import re


logger = logging.getLogger(__name__)


class HashEmbedding:
    """无需外部模型的轻量 embedding，实现本地开发可用的向量化能力。"""

    def __init__(self, dimension: int = 384) -> None:
        """初始化哈希向量维度。

        Args:
            dimension: 向量维度。
        """
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """将文本转换为固定维度向量，便于向量库相似度检索。

        Args:
            text: 待处理的文本内容。
        """
        vector = [0.0] * self.dimension
        tokens = _tokenize(text)
        for token in tokens:
            # 同一个 token 总是落到同一个维度，并通过 sign 减少哈希碰撞偏差。
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _normalize(vector)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本列表，上传知识库时会使用。

        Args:
            texts: 待批量向量化的文本列表。
        """
        return [self.embed(text) for text in texts]


def create_embedding(backend: str, model_name: str) -> HashEmbedding:
    """根据配置创建 embedding 实例。

    Args:
        backend: 要使用的后端类型配置值。
        model_name: 模型名称。
    """
    if backend == "sentence_transformers":
        return SentenceTransformerEmbedding(model_name)
    # 哈希 embedding 没有语义，召回质量远低于真实模型，仅适合离线占位与本地开发。
    logger.warning(
        "EMBEDDING_BACKEND=%s 使用无语义的 HashEmbedding，RAG 召回质量较差；"
        "生产请设置 EMBEDDING_BACKEND=sentence_transformers",
        backend,
    )
    return HashEmbedding()


class SentenceTransformerEmbedding(HashEmbedding):
    """基于 sentence-transformers 的真实语义向量实现。"""

    def __init__(self, model_name: str) -> None:
        """加载指定模型，并读取模型输出向量维度。

        Args:
            model_name: 模型名称。
        """
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        dimension = int(self.model.get_sentence_embedding_dimension() or 1024)
        super().__init__(dimension=dimension)

    def embed(self, text: str) -> list[float]:
        """调用 sentence-transformers 将单条文本转换为归一化向量。

        Args:
            text: 待处理的文本内容。
        """
        vector = self.model.encode(text, normalize_embeddings=True)
        return [float(item) for item in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """调用 sentence-transformers 批量转换文本，减少模型调用开销。

        Args:
            texts: 待批量向量化的文本列表。
        """
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [[float(item) for item in vector] for vector in vectors]


def _tokenize(text: str) -> list[str]:
    """把文本切成哈希 embedding 使用的 token。

    Args:
        text: 待处理的文本内容。
    """
    normalized = text.lower().strip()
    if not normalized:
        return []
    words = re.findall(r"[a-z0-9]+", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    chinese_bigrams = [
        "".join(chinese_chars[index : index + 2])
        for index in range(max(0, len(chinese_chars) - 1))
    ]
    chinese_trigrams = [
        "".join(chinese_chars[index : index + 3])
        for index in range(max(0, len(chinese_chars) - 2))
    ]
    tokens = words + chinese_chars + chinese_bigrams + chinese_trigrams
    if tokens:
        return tokens
    return [normalized[index : index + 2] for index in range(max(1, len(normalized) - 1))]


def _normalize(vector: list[float]) -> list[float]:
    """将向量归一化为单位长度，方便用点积近似余弦相似度。

    Args:
        vector: 用于检索或归一化的向量。
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
