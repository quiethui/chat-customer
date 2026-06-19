"""数据库字典行或 ORM 对象到只读记录模型的转换函数。"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.repositories.mysql_records import (
    AuthSessionRecord,
    ChatMessageRecord,
    ChatSessionRecord,
    KnowledgeBaseRecord,
    KnowledgeChunkRecord,
    KnowledgeFileRecord,
    OrderRecord,
    UserRecord,
)


def _field(row: Any, key: str) -> Any:
    """读取必填字段，兼容字典行和 ORM 对象。

    Args:
        row: 数据库返回的字典行或 ORM 对象。
        key: 需要读取的字段名。
    """
    if isinstance(row, Mapping):
        return row[key]
    return getattr(row, key)


def _optional(row: Any, key: str, default: Any = None) -> Any:
    """读取可选字段，兼容字典行和 ORM 对象。

    Args:
        row: 数据库返回的字典行或 ORM 对象。
        key: 需要读取的字段名。
        default: 字段不存在时返回的默认值。
    """
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def map_user(row: Any) -> UserRecord:
    """将用户表记录转换为 UserRecord。

    Args:
        row: users 表对应的字典行或 ORM 对象。
    """
    return UserRecord(
        id=int(_field(row, "id")),
        username=str(_field(row, "username")),
        password_hash=str(_field(row, "password_hash")),
        salt=str(_field(row, "salt")),
        nickname=_optional(row, "nickname"),
        avatar=_optional(row, "avatar"),
        status=int(_optional(row, "status", 1)),
    )


def map_auth_session(row: Any) -> AuthSessionRecord:
    """将登录会话表记录转换为 AuthSessionRecord。

    Args:
        row: user_sessions 表对应的字典行或 ORM 对象。
    """
    return AuthSessionRecord(
        id=int(_field(row, "id")),
        user_id=int(_field(row, "user_id")),
        token=str(_field(row, "token")),
        expires_at=_field(row, "expires_at"),
    )


def map_chat_session(row: Any) -> ChatSessionRecord:
    """将聊天会话表记录转换为 ChatSessionRecord。

    Args:
        row: chat_sessions 表对应的字典行或 ORM 对象。
    """
    return ChatSessionRecord(
        id=str(_field(row, "id")),
        user_id=int(_field(row, "user_id")),
        session_title=str(_field(row, "session_title")),
        session_content=_optional(row, "session_content"),
        remark=_optional(row, "remark"),
        created_at=_field(row, "created_at"),
        updated_at=_field(row, "updated_at"),
    )


def map_chat_message(row: Any) -> ChatMessageRecord:
    """将聊天消息表记录转换为 ChatMessageRecord。

    Args:
        row: chat_messages 表对应的字典行或 ORM 对象。
    """
    return ChatMessageRecord(
        id=int(_field(row, "id")),
        session_id=str(_field(row, "session_id")),
        user_id=int(_field(row, "user_id")),
        role=str(_field(row, "role")),
        content=str(_field(row, "content")),
        model_name=_optional(row, "model_name"),
        total_tokens=int(_optional(row, "total_tokens", 0)),
        references_text=_optional(row, "references_text"),
        created_at=_field(row, "created_at"),
    )


def map_order(row: Any) -> OrderRecord:
    """将订单表记录转换为 OrderRecord。

    Args:
        row: user_orders 表对应的字典行或 ORM 对象。
    """
    return OrderRecord(
        id=int(_field(row, "id")),
        user_id=int(_field(row, "user_id")),
        order_no=str(_field(row, "order_no")),
        product_name=str(_field(row, "product_name")),
        product_quantity=int(_optional(row, "product_quantity", 1)),
        order_amount=Decimal(str(_field(row, "order_amount"))),
        currency=str(_optional(row, "currency", "CNY")),
        order_status=str(_field(row, "order_status")),
        paid_at=_optional(row, "paid_at"),
        shipped_at=_optional(row, "shipped_at"),
        remark=_optional(row, "remark"),
        created_at=_field(row, "created_at"),
        updated_at=_field(row, "updated_at"),
    )


def map_knowledge_base(row: Any) -> KnowledgeBaseRecord:
    """将知识库主表记录转换为 KnowledgeBaseRecord。

    Args:
        row: knowledge_bases 表对应的字典行或 ORM 对象。
    """
    return KnowledgeBaseRecord(
        id=int(_field(row, "id")),
        name=str(_field(row, "name")),
        description=_optional(row, "description"),
        created_at=_field(row, "created_at"),
    )


def map_knowledge_file(row: Any) -> KnowledgeFileRecord:
    """将知识库文件表记录转换为 KnowledgeFileRecord。

    Args:
        row: knowledge_files 表对应的字典行或 ORM 对象。
    """
    return KnowledgeFileRecord(
        id=int(_field(row, "id")),
        knowledge_base_id=int(_field(row, "knowledge_base_id")),
        filename=str(_field(row, "filename")),
        file_path=str(_field(row, "file_path")),
        status=str(_field(row, "status")),
        created_at=_field(row, "created_at"),
    )


def map_knowledge_chunk(row: Any) -> KnowledgeChunkRecord:
    """将知识库切块表记录转换为 KnowledgeChunkRecord。

    Args:
        row: knowledge_chunks 表对应的字典行或 ORM 对象。
    """
    return KnowledgeChunkRecord(
        id=int(_field(row, "id")),
        knowledge_base_id=int(_field(row, "knowledge_base_id")),
        file_id=int(_field(row, "file_id")),
        chunk_index=int(_field(row, "chunk_index")),
        content=str(_field(row, "content")),
        vector_id=str(_field(row, "vector_id")),
        created_at=_field(row, "created_at"),
    )
