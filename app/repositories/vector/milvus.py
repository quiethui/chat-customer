"""Milvus 向量仓储实现。"""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from app.repositories.vector.base import RetrievalResult, VectorDocument, VectorSearchFilter


class MilvusVectorRepository:
    """Milvus 或 Milvus Lite 向量仓储。"""

    def __init__(self, uri: str, token: str | None, collection_name: str, dimension: int) -> None:
        """初始化 Milvus 客户端和集合。

        Args:
            uri: Milvus 服务地址或本地 Lite 文件路径。
            token: 认证访问令牌。
            collection_name: Milvus 集合名称。
            dimension: 向量维度。
        """
        if _is_local_milvus_uri(uri):
            _ensure_local_milvus_parent(uri)

        MilvusClient, data_type = _import_milvus_components()
        self.dimension = dimension
        self.collection_name = collection_name
        self.client = MilvusClient(uri=uri, token=token) if token else MilvusClient(uri=uri)
        if not self.client.has_collection(collection_name):
            self._create_collection(collection_name, dimension, data_type)
        else:
            self._validate_existing_collection(collection_name, dimension)
        self._requires_manual_id = not self._collection_uses_auto_id(collection_name)

    def _create_collection(self, collection_name: str, dimension: int, data_type: Any) -> None:
        """创建适配文本检索的 Milvus 集合。

        Args:
            collection_name: Milvus 集合名称。
            dimension: 向量维度。
            data_type: Milvus 向量字段使用的数据类型。
        """
        schema = type(self.client).create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=data_type.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=data_type.FLOAT_VECTOR, dim=dimension)
        schema.add_field(field_name="text", datatype=data_type.VARCHAR, max_length=65535)
        schema.add_field(field_name="document_id", datatype=data_type.VARCHAR, max_length=128)
        schema.add_field(field_name="file_name", datatype=data_type.VARCHAR, max_length=512)
        schema.add_field(field_name="knowledge_base_id", datatype=data_type.VARCHAR, max_length=64)
        schema.add_field(field_name="file_id", datatype=data_type.VARCHAR, max_length=64)
        schema.add_field(field_name="file_status", datatype=data_type.VARCHAR, max_length=32)
        schema.add_field(field_name="vector_id", datatype=data_type.VARCHAR, max_length=128)

        index_params = type(self.client).prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self.client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
            consistency_level="Strong",
        )

    def _validate_existing_collection(self, collection_name: str, dimension: int) -> None:
        """校验已有 Milvus 集合是否匹配当前 embedding 维度。"""
        description = self.client.describe_collection(collection_name)
        actual_dimension = _collection_vector_dimension(description)
        if actual_dimension is not None and actual_dimension != dimension:
            raise RuntimeError(
                f"Milvus collection {collection_name} 向量维度为 {actual_dimension}，"
                f"当前 embedding 维度为 {dimension}，请更换 collection 或重建向量库"
            )
        field_names = _collection_field_names(description)
        required_fields = {"vector", "text", "document_id", "file_name", "knowledge_base_id", "file_id", "vector_id"}
        missing_fields = required_fields - field_names
        if missing_fields:
            raise RuntimeError(f"Milvus collection {collection_name} 缺少字段：{', '.join(sorted(missing_fields))}")

    def _collection_uses_auto_id(self, collection_name: str) -> bool:
        """判断现有集合是否由 Milvus 自动生成主键。

        Args:
            collection_name: Milvus 集合名称。
        """
        description = self.client.describe_collection(collection_name)
        return bool(description.get("auto_id"))

    def add_documents(self, documents: list[VectorDocument]) -> None:
        """批量写入知识文档到 Milvus。

        Args:
            documents: 待写入向量库的文档列表。
        """
        if not documents:
            return
        for document in documents:
            _ensure_dimension(document.vector, self.dimension)
        self.client.insert(
            collection_name=self.collection_name,
            data=[self._document_to_row(document) for document in documents],
        )
        self.client.flush(collection_name=self.collection_name)

    def _document_to_row(self, document: VectorDocument) -> dict[str, Any]:
        """将知识文档转换为 Milvus 行数据。

        Args:
            document: 待写入向量库的文档对象。
        """
        row: dict[str, Any] = {
            "vector": document.vector,
            "text": document.text,
            "document_id": document.metadata.get("document_id", ""),
            "file_name": document.metadata.get("file_name", ""),
            "knowledge_base_id": document.metadata.get("knowledge_base_id", ""),
            "file_id": document.metadata.get("file_id", ""),
            "file_status": document.metadata.get("file_status", ""),
            "vector_id": document.metadata.get("vector_id", ""),
        }
        if self._requires_manual_id:
            row["id"] = uuid4().int & ((1 << 63) - 1)
        return row

    def search(
        self,
        vector: list[float],
        top_k: int,
        filters: VectorSearchFilter | None = None,
    ) -> list[RetrievalResult]:
        """在 Milvus 中检索最相似的知识文档。

        Args:
            vector: 用于检索或归一化的向量。
            top_k: 向量检索返回的候选数量。
            filters: 可选的知识库、文件和状态过滤条件。
        """
        _ensure_dimension(vector, self.dimension)
        self.client.load_collection(self.collection_name)
        search_kwargs: dict[str, Any] = {
            "collection_name": self.collection_name,
            "data": [vector],
            "limit": top_k,
            "output_fields": ["text", "document_id", "file_name", "knowledge_base_id", "file_id", "file_status", "vector_id"],
        }
        filter_expression = _build_filter_expression(filters)
        if filter_expression:
            search_kwargs["filter"] = filter_expression
        results = self.client.search(**search_kwargs)
        rows = results[0] if results else []
        return [self._search_row_to_result(row) for row in rows]

    def _search_row_to_result(self, row: dict[str, Any]) -> RetrievalResult:
        """将 Milvus 搜索行转换为检索结果。

        Args:
            row: 数据库查询返回的一行记录。
        """
        entity = row.get("entity", {})
        return RetrievalResult(
            text=entity.get("text", ""),
            score=float(row.get("distance", 0.0)),
            metadata={
                "document_id": entity.get("document_id", ""),
                "file_name": entity.get("file_name", ""),
                "knowledge_base_id": entity.get("knowledge_base_id", ""),
                "file_id": entity.get("file_id", ""),
                "file_status": entity.get("file_status", ""),
                "vector_id": entity.get("vector_id", ""),
            },
        )

    def delete_by_file_id(self, file_id: int) -> None:
        """从 Milvus 删除某个知识库文件的所有向量。

        Args:
            file_id: 知识库文件 ID。
        """
        if not self.client.has_collection(self.collection_name):
            return
        self.client.delete(collection_name=self.collection_name, filter=f'file_id == "{_escape_filter_value(str(file_id))}"')
        self.client.flush(collection_name=self.collection_name)

    def delete_by_vector_ids(self, vector_ids: list[str]) -> None:
        """从 Milvus 删除指定业务向量 ID。"""
        if not vector_ids or not self.client.has_collection(self.collection_name):
            return
        self.client.delete(collection_name=self.collection_name, filter=_in_filter("vector_id", vector_ids))
        self.client.flush(collection_name=self.collection_name)


def _build_filter_expression(filters: VectorSearchFilter | None) -> str:
    if filters is None:
        return ""
    expressions = []
    if filters.knowledge_base_ids:
        expressions.append(_in_filter("knowledge_base_id", filters.knowledge_base_ids))
    if filters.file_ids:
        expressions.append(_in_filter("file_id", filters.file_ids))
    if filters.file_statuses:
        expressions.append(_in_filter("file_status", filters.file_statuses))
    return " and ".join(expressions)


def _in_filter(field_name: str, values: list[str]) -> str:
    escaped_values = [f'"{_escape_filter_value(str(value))}"' for value in values]
    return f"{field_name} in [{', '.join(escaped_values)}]"


def _escape_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _ensure_dimension(vector: list[float], dimension: int) -> None:
    if len(vector) != dimension:
        raise ValueError(f"向量维度不匹配：期望 {dimension}，实际 {len(vector)}")


def _collection_field_names(description: dict[str, Any]) -> set[str]:
    fields = _collection_fields(description)
    return {str(field.get("name") or field.get("field_name")) for field in fields if field.get("name") or field.get("field_name")}


def _collection_vector_dimension(description: dict[str, Any]) -> int | None:
    for field in _collection_fields(description):
        name = field.get("name") or field.get("field_name")
        if name != "vector":
            continue
        params = field.get("params") or field.get("type_params") or {}
        dimension = params.get("dim") or field.get("dim")
        if dimension is None:
            return None
        return int(dimension)
    return None


def _collection_fields(description: dict[str, Any]) -> list[dict[str, Any]]:
    schema = description.get("schema") or {}
    fields = schema.get("fields") or description.get("fields") or []
    return [field for field in fields if isinstance(field, dict)]


def _import_milvus_components() -> tuple[Any, Any]:
    """导入 pymilvus 组件，并避免其自动读取本地 MILVUS_URI。"""
    original_milvus_uri = os.environ.get("MILVUS_URI")
    original_dotenv_disabled = os.environ.get("PYTHON_DOTENV_DISABLED")
    should_restore_milvus_uri = "MILVUS_URI" in os.environ
    should_restore_dotenv_disabled = "PYTHON_DOTENV_DISABLED" in os.environ

    os.environ["MILVUS_URI"] = ""
    os.environ["PYTHON_DOTENV_DISABLED"] = "true"
    try:
        from pymilvus import DataType, MilvusClient
    except ImportError as error:
        raise RuntimeError("请先安装 pymilvus[milvus_lite] 依赖后再使用 Milvus Lite") from error
    finally:
        if should_restore_milvus_uri and original_milvus_uri is not None:
            os.environ["MILVUS_URI"] = original_milvus_uri
        else:
            os.environ.pop("MILVUS_URI", None)

        if should_restore_dotenv_disabled and original_dotenv_disabled is not None:
            os.environ["PYTHON_DOTENV_DISABLED"] = original_dotenv_disabled
        else:
            os.environ.pop("PYTHON_DOTENV_DISABLED", None)

    return MilvusClient, DataType


def _is_local_milvus_uri(uri: str) -> bool:
    """判断 URI 是否为 Milvus Lite 本地数据库路径。

    Args:
        uri: Milvus 服务地址或本地 Lite 文件路径。
    """
    parsed_uri = urlparse(uri)
    return parsed_uri.scheme in {"", "file"}


def _ensure_local_milvus_parent(uri: str) -> None:
    """确保 Milvus Lite 数据库文件的父目录存在。

    Args:
        uri: Milvus 服务地址或本地 Lite 文件路径。
    """
    path = Path(uri.removeprefix("file://")).expanduser()
    parent = path.parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)
