"""数据库字典行或 ORM 对象到只读记录模型的转换函数。"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.repositories.mysql.records import (
    ChatMessageRecord,
    ChatSessionRecord,
    CustomerRecord,
    CustomerSessionRecord,
    KnowledgeBaseRecord,
    KnowledgeChunkRecord,
    KnowledgeFileRecord,
    LLMRequestLogRecord,
    ManagerRecord,
    ManagerSessionRecord,
    OrderRecord,
    ProductRecord,
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


def map_manager(row: Any) -> ManagerRecord:
    """将管理员表记录转换为 ManagerRecord。

    Args:
        row: managers 表对应的字典行或 ORM 对象。
    """
    return ManagerRecord(
        id=int(_field(row, "id")),
        username=str(_field(row, "username")),
        password_hash=str(_field(row, "password_hash")),
        salt=str(_field(row, "salt")),
        nickname=_optional(row, "nickname"),
        avatar=_optional(row, "avatar"),
        status=int(_optional(row, "status", 1)),
        is_admin=int(_optional(row, "is_admin", 0)),
        created_at=_optional(row, "created_at"),
        updated_at=_optional(row, "updated_at"),
        deleted_at=_optional(row, "deleted_at"),
    )


def map_manager_session(row: Any) -> ManagerSessionRecord:
    """将管理员登录会话表记录转换为 ManagerSessionRecord。

    Args:
        row: manager_sessions 表对应的字典行或 ORM 对象。
    """
    return ManagerSessionRecord(
        id=int(_field(row, "id")),
        manager_id=int(_field(row, "manager_id")),
        token=str(_field(row, "token")),
        expires_at=_field(row, "expires_at"),
    )


def map_customer(row: Any) -> CustomerRecord:
    """将客户表记录转换为 CustomerRecord。

    Args:
        row: customers 表对应的字典行或 ORM 对象。
    """
    return CustomerRecord(
        id=int(_field(row, "id")),
        customer_no=str(_field(row, "customer_no")),
        nickname=_optional(row, "nickname"),
        phone=_optional(row, "phone"),
        email=_optional(row, "email"),
        password_hash=_optional(row, "password_hash"),
        salt=_optional(row, "salt"),
        source=str(_optional(row, "source", "web")),
        is_anonymous=int(_optional(row, "is_anonymous", 1)),
        status=int(_optional(row, "status", 1)),
        created_at=_optional(row, "created_at"),
        updated_at=_optional(row, "updated_at"),
        deleted_at=_optional(row, "deleted_at"),
        username=_optional(row, "username"),
        avatar=_optional(row, "avatar"),
        last_login_at=_optional(row, "last_login_at"),
        last_login_ip=_optional(row, "last_login_ip"),
    )


def map_customer_session(row: Any) -> CustomerSessionRecord:
    """将客户登录会话表记录转换为 CustomerSessionRecord。

    Args:
        row: customer_sessions 表对应的字典行或 ORM 对象。
    """
    return CustomerSessionRecord(
        id=int(_field(row, "id")),
        customer_id=int(_field(row, "customer_id")),
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
        customer_id=int(_field(row, "customer_id")),
        session_title=str(_field(row, "session_title")),
        session_content=_optional(row, "session_content"),
        remark=_optional(row, "remark"),
        created_at=_field(row, "created_at"),
        updated_at=_field(row, "updated_at"),
        mode=str(_optional(row, "mode", "bot")),
        status=str(_optional(row, "status", "bot")),
        assigned_agent_id=_optional(row, "assigned_agent_id"),
        last_message_at=_optional(row, "last_message_at"),
        rating=_optional(row, "rating"),
        rating_comment=_optional(row, "rating_comment"),
    )


def map_chat_message(row: Any) -> ChatMessageRecord:
    """将聊天消息表记录转换为 ChatMessageRecord。

    Args:
        row: chat_messages 表对应的字典行或 ORM 对象。
    """
    return ChatMessageRecord(
        id=int(_field(row, "id")),
        session_id=str(_field(row, "session_id")),
        customer_id=int(_field(row, "customer_id")),
        role=str(_field(row, "role")),
        content=str(_field(row, "content")),
        model_name=_optional(row, "model_name"),
        total_tokens=int(_optional(row, "total_tokens", 0)),
        references_text=_optional(row, "references_text"),
        created_at=_field(row, "created_at"),
        sender_type=str(_optional(row, "sender_type", "customer")),
        agent_id=_optional(row, "agent_id"),
    )


def map_order(row: Any) -> OrderRecord:
    """将订单表记录转换为 OrderRecord。

    Args:
        row: user_orders 表对应的字典行或 ORM 对象。
    """
    return OrderRecord(
        id=int(_field(row, "id")),
        customer_id=int(_field(row, "customer_id")),
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


def map_product(row: Any) -> ProductRecord:
    """将商品表记录转换为 ProductRecord。

    Args:
        row: products 表对应的字典行或 ORM 对象。
    """
    return ProductRecord(
        id=int(_field(row, "id")),
        product_sku=str(_field(row, "product_sku")),
        name=str(_field(row, "name")),
        category=_optional(row, "category"),
        price=Decimal(str(_field(row, "price"))),
        currency=str(_optional(row, "currency", "CNY")),
        stock=int(_optional(row, "stock", 0)),
        status=str(_optional(row, "status", "on_sale")),
        description=_optional(row, "description"),
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


def map_llm_request_log(row: Any) -> LLMRequestLogRecord:
    """将大模型请求日志表记录转换为 LLMRequestLogRecord。

    Args:
        row: llm_request_logs 表对应的字典行或 ORM 对象。
    """
    return LLMRequestLogRecord(
        id=int(_field(row, "id")),
        model=str(_field(row, "model")),
        base_url=_optional(row, "base_url"),
        request_payload=str(_field(row, "request_payload")),
        response_payload=_optional(row, "response_payload"),
        prompt_tokens=_optional(row, "prompt_tokens"),
        completion_tokens=_optional(row, "completion_tokens"),
        total_tokens=_optional(row, "total_tokens"),
        latency_ms=_optional(row, "latency_ms"),
        status=str(_optional(row, "status", "success")),
        error_message=_optional(row, "error_message"),
        created_at=_field(row, "created_at"),
    )
