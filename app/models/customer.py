"""AI 客服系统的 MySQL ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP

from app.db.base import Base


class Manager(Base):
    """管理员（管理后台用户/坐席）表 ORM 模型。"""

    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 管理员自增主键。
    username: Mapped[str] = mapped_column(String(64), nullable=False)  # 管理员登录名，全局唯一。
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 加盐哈希后的密码。
    salt: Mapped[str] = mapped_column(String(64), nullable=False)  # 密码哈希使用的随机盐。
    nickname: Mapped[str | None] = mapped_column(String(64))  # 管理员昵称，空值时展示 username。
    avatar: Mapped[str | None] = mapped_column(String(500))  # 管理员头像 URL。
    status: Mapped[int] = mapped_column(mysql.TINYINT, nullable=False, default=1, server_default="1")  # 管理员状态，1 表示正常。
    is_admin: Mapped[int] = mapped_column(mysql.TINYINT, nullable=False, default=0, server_default="0")  # 是否管理员，1 表示管理员，0 表示普通坐席。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 管理员创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 管理员更新时间。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 管理员软删除时间，空值表示未删除。

    sessions: Mapped[list[ManagerSession]] = relationship(back_populates="manager", cascade="all, delete-orphan")  # 管理员登录会话集合。

    __table_args__ = (UniqueConstraint("username", name="uk_managers_username"),)  # 用户名唯一索引。


class ManagerSession(Base):
    """管理员登录会话表 ORM 模型。"""

    __tablename__ = "manager_sessions"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 登录会话自增主键。
    manager_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("managers.id", ondelete="CASCADE"), nullable=False)  # 会话所属管理员 ID。
    token: Mapped[str] = mapped_column(String(128), nullable=False)  # 登录凭证 Token。
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Token 过期时间。
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)  # Token 撤销时间，空值表示有效。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 会话创建时间。

    manager: Mapped[Manager] = relationship(back_populates="sessions")  # 会话所属管理员。

    __table_args__ = (
        UniqueConstraint("token", name="uk_manager_sessions_token"),  # Token 唯一索引。
        Index("idx_manager_sessions_manager_id", "manager_id"),  # 管理员 ID 查询索引。
        Index("idx_manager_sessions_expires_at", "expires_at"),  # 过期时间查询索引。
    )


class Customer(Base):
    """客户表 ORM 模型（对外 AI 客服服务对象，含匿名访客与已注册客户）。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 客户自增主键。
    customer_no: Mapped[str] = mapped_column(String(64), nullable=False)  # 客户编号，全局唯一。
    username: Mapped[str | None] = mapped_column(String(64))  # 登录账号，全局唯一；匿名访客为 NULL。
    nickname: Mapped[str | None] = mapped_column(String(64))  # 客户昵称，可空，匿名访客可自动生成。
    phone: Mapped[str | None] = mapped_column(String(32))  # 客户手机号，可空。
    email: Mapped[str | None] = mapped_column(String(128))  # 客户邮箱，可空。
    avatar: Mapped[str | None] = mapped_column(String(500))  # 客户头像 URL；为空时前端展示默认头像。
    password_hash: Mapped[str | None] = mapped_column(String(64))  # 加盐哈希密码，匿名访客为空。
    salt: Mapped[str | None] = mapped_column(String(64))  # 密码哈希随机盐，匿名访客为空。
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="web", server_default="web")  # 客户来源渠道。
    is_anonymous: Mapped[int] = mapped_column(mysql.TINYINT, nullable=False, default=1, server_default="1")  # 是否匿名访客，1 表示匿名。
    status: Mapped[int] = mapped_column(mysql.TINYINT, nullable=False, default=1, server_default="1")  # 客户状态，1 表示正常。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 客户创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 客户更新时间。
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)  # 上次登录时间；匿名访客为空。
    last_login_ip: Mapped[str | None] = mapped_column(String(64))  # 上次登录 IP（取 X-Forwarded-For 真实 IP）。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 客户软删除时间，空值表示未删除。

    sessions: Mapped[list[CustomerSession]] = relationship(back_populates="customer", cascade="all, delete-orphan")  # 客户登录会话集合。

    __table_args__ = (
        UniqueConstraint("customer_no", name="uk_customers_customer_no"),  # 客户编号唯一索引。
        UniqueConstraint("username", name="uk_customers_username"),  # 登录账号唯一索引（允许多个 NULL）。
    )


class CustomerSession(Base):
    """客户登录会话表 ORM 模型（镜像 manager_sessions）。"""

    __tablename__ = "customer_sessions"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 客户会话自增主键。
    customer_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )  # 会话所属客户 ID。
    token: Mapped[str] = mapped_column(String(128), nullable=False)  # 客户端登录凭证 Token。
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Token 过期时间。
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)  # Token 撤销时间，空值表示有效。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 会话创建时间。

    customer: Mapped[Customer] = relationship(back_populates="sessions")  # 会话所属客户。

    __table_args__ = (
        UniqueConstraint("token", name="uk_customer_sessions_token"),  # Token 唯一索引。
        Index("idx_customer_sessions_customer_id", "customer_id"),  # 客户 ID 查询索引。
        Index("idx_customer_sessions_expires_at", "expires_at"),  # 过期时间查询索引。
    )


class ChatSession(Base):
    """聊天会话表 ORM 模型。"""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 聊天会话 ID。
    customer_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )  # 会话所属客户 ID。
    session_title: Mapped[str] = mapped_column(String(120), nullable=False)  # 会话标题。
    session_content: Mapped[str | None] = mapped_column(Text)  # 会话摘要或首轮提问内容。
    remark: Mapped[str | None] = mapped_column(String(255))  # 会话备注。
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="bot", server_default="bot")  # 服务模式：bot/agent。
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="bot", server_default="bot")  # 会话状态：bot/waiting/serving/closed。
    assigned_agent_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("managers.id", ondelete="SET NULL"),
    )  # 当前接管坐席的管理员 ID，未接管为空。
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)  # 最近一条消息时间，用于坐席队列排序。
    rating: Mapped[int | None] = mapped_column(mysql.TINYINT)  # 客户满意度评分，未评价为空。
    rating_comment: Mapped[str | None] = mapped_column(String(500))  # 客户满意度评价文字，未评价为空。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 会话创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 会话最后更新时间。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 会话软删除时间。

    messages: Mapped[list[ChatMessage]] = relationship(back_populates="session", cascade="all, delete-orphan")  # 会话下的消息集合。

    __table_args__ = (
        Index("idx_chat_sessions_customer_updated", "customer_id", "updated_at"),  # 客户会话列表排序索引。
        Index("idx_chat_sessions_status_last_msg", "status", "last_message_at"),  # 坐席队列状态排序索引。
    )


class ChatMessage(Base):
    """聊天消息表 ORM 模型。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 消息自增主键。
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)  # 消息所属会话 ID。
    customer_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )  # 消息所属客户 ID。
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 消息角色（供 LLM 上下文构建）。
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False, default="customer", server_default="customer")  # 消息发送方：customer/bot/agent。
    agent_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("managers.id", ondelete="SET NULL"),
    )  # 人工消息的坐席管理员 ID，非人工消息为空。
    content: Mapped[str] = mapped_column(mysql.MEDIUMTEXT, nullable=False)  # 消息正文。
    model_name: Mapped[str | None] = mapped_column(String(100))  # 助手回复使用的模型名称。
    total_tokens: Mapped[int] = mapped_column(mysql.INTEGER, nullable=False, default=0, server_default="0")  # 消息消耗的 token 数。
    references_text: Mapped[str | None] = mapped_column(mysql.MEDIUMTEXT)  # 助手回答引用来源文本。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 消息创建时间。

    session: Mapped[ChatSession] = relationship(back_populates="messages")  # 消息所属会话。

    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id", "id"),  # 会话消息列表索引。
        Index("idx_chat_messages_customer_id", "customer_id"),  # 客户消息查询索引。
    )


class UserOrder(Base):
    """订单表 ORM 模型（按客户隔离，表名保留 user_orders）。"""

    __tablename__ = "user_orders"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 订单自增主键。
    customer_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )  # 订单所属客户 ID。
    order_no: Mapped[str] = mapped_column(String(64), nullable=False)  # 订单号，全局唯一。
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)  # 商品名称。
    product_sku: Mapped[str | None] = mapped_column(String(100))  # 商品 SKU。
    product_quantity: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False, default=1, server_default="1")  # 商品购买数量。
    order_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)  # 订单金额。
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY", server_default="CNY")  # 订单币种。
    order_status: Mapped[str] = mapped_column(String(32), nullable=False)  # 订单状态编码。
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)  # 支付时间。
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime)  # 发货时间。
    receiver_name: Mapped[str | None] = mapped_column(String(64))  # 收货人姓名。
    receiver_phone: Mapped[str | None] = mapped_column(String(32))  # 收货人手机号。
    remark: Mapped[str | None] = mapped_column(String(255))  # 订单备注。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 订单创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 订单更新时间。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 订单软删除时间。

    __table_args__ = (
        UniqueConstraint("order_no", name="uk_user_orders_order_no"),  # 订单号唯一索引。
        Index("idx_user_orders_customer_created", "customer_id", "created_at"),  # 客户订单时间索引。
        Index("idx_user_orders_customer_status", "customer_id", "order_status"),  # 客户订单状态索引。
    )


class KnowledgeBase(Base):
    """知识库主表 ORM 模型。"""

    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 知识库自增主键。
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 知识库名称。
    description: Mapped[str | None] = mapped_column(String(500))  # 知识库描述。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 知识库创建时间。

    files: Mapped[list[KnowledgeFile]] = relationship(back_populates="knowledge_base", cascade="all, delete-orphan")  # 知识库文件集合。

    __table_args__ = (UniqueConstraint("name", name="uk_knowledge_bases_name"),)  # 知识库名称唯一索引。


class KnowledgeFile(Base):
    """知识库文件表 ORM 模型。"""

    __tablename__ = "knowledge_files"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 文件自增主键。
    knowledge_base_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )  # 所属知识库 ID。
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # 用户上传的原始文件名。
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # 文件保存路径。
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")  # 文件处理状态。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 文件创建时间。

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="files")  # 文件所属知识库。
    chunks: Mapped[list[KnowledgeChunk]] = relationship(back_populates="file", cascade="all, delete-orphan")  # 文件切块集合。

    __table_args__ = (Index("idx_knowledge_files_base_id", "knowledge_base_id"),)  # 知识库文件查询索引。


class KnowledgeChunk(Base):
    """知识库切块表 ORM 模型。"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 切块自增主键。
    knowledge_base_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )  # 所属知识库 ID。
    file_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("knowledge_files.id", ondelete="CASCADE"), nullable=False)  # 所属文件 ID。
    chunk_index: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)  # 文件内切块序号。
    content: Mapped[str] = mapped_column(mysql.MEDIUMTEXT, nullable=False)  # 切块文本内容。
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)  # 向量库中的业务向量 ID。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 切块创建时间。

    file: Mapped[KnowledgeFile] = relationship(back_populates="chunks")  # 切块所属文件。

    __table_args__ = (
        Index("idx_knowledge_chunks_base_file", "knowledge_base_id", "file_id"),  # 知识库文件切块查询索引。
        Index("idx_knowledge_chunks_vector_id", "vector_id"),  # 向量 ID 查询索引。
    )


class LLMRequestLog(Base):
    """大模型请求日志表 ORM 模型，记录每次 OpenAI 兼容接口调用的请求与响应。"""

    __tablename__ = "llm_request_logs"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 日志自增主键。
    model: Mapped[str] = mapped_column(String(100), nullable=False)  # 本次请求使用的模型名称。
    base_url: Mapped[str | None] = mapped_column(String(500))  # OpenAI 兼容接口基础地址。
    request_payload: Mapped[str] = mapped_column(mysql.MEDIUMTEXT, nullable=False)  # 完整请求参数 JSON。
    response_payload: Mapped[str | None] = mapped_column(mysql.MEDIUMTEXT)  # 完整响应数据 JSON，失败时为空。
    prompt_tokens: Mapped[int | None] = mapped_column(mysql.INTEGER(unsigned=True))  # 提示词消耗 token 数。
    completion_tokens: Mapped[int | None] = mapped_column(mysql.INTEGER(unsigned=True))  # 补全消耗 token 数。
    total_tokens: Mapped[int | None] = mapped_column(mysql.INTEGER(unsigned=True))  # 本次请求总消耗 token 数。
    latency_ms: Mapped[int | None] = mapped_column(mysql.INTEGER(unsigned=True))  # 请求往返耗时（毫秒）。
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success", server_default="success")  # 请求结果状态。
    error_message: Mapped[str | None] = mapped_column(String(1000))  # 请求失败时的错误摘要。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 日志创建时间。

    __table_args__ = (
        Index("idx_llm_request_logs_model_created", "model", "created_at"),  # 按模型和时间查询索引。
        Index("idx_llm_request_logs_status", "status"),  # 按请求结果状态查询索引。
    )


class Product(Base):
    """商品表 ORM 模型，全局商品目录，供 AI 客服查询商品信息。"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 商品自增主键。
    product_sku: Mapped[str] = mapped_column(String(100), nullable=False)  # 商品 SKU，全局唯一。
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 商品名称。
    category: Mapped[str | None] = mapped_column(String(64))  # 商品类目。
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)  # 商品售价。
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY", server_default="CNY")  # 售价币种。
    stock: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False, default=0, server_default="0")  # 库存数量。
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="on_sale", server_default="on_sale")  # 商品状态编码。
    description: Mapped[str | None] = mapped_column(String(500))  # 商品简介。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 商品创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 商品更新时间。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 商品软删除时间。

    __table_args__ = (
        UniqueConstraint("product_sku", name="uk_products_sku"),  # 商品 SKU 唯一索引。
        Index("idx_products_name", "name"),  # 商品名称查询索引。
        Index("idx_products_category", "category"),  # 商品类目查询索引。
        Index("idx_products_status", "status"),  # 商品状态查询索引。
    )
