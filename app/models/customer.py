"""AI 客服系统的 MySQL ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP

from app.db.base import Base


class User(Base):
    """系统用户表 ORM 模型。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 用户自增主键。
    username: Mapped[str] = mapped_column(String(64), nullable=False)  # 用户登录名，全局唯一。
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 加盐哈希后的密码。
    salt: Mapped[str] = mapped_column(String(64), nullable=False)  # 密码哈希使用的随机盐。
    nickname: Mapped[str | None] = mapped_column(String(64))  # 用户昵称，空值时展示 username。
    avatar: Mapped[str | None] = mapped_column(String(500))  # 用户头像 URL。
    status: Mapped[int] = mapped_column(mysql.TINYINT, nullable=False, default=1, server_default="1")  # 用户状态，1 表示正常。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 用户创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 用户更新时间。

    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan")  # 用户登录会话集合。

    __table_args__ = (UniqueConstraint("username", name="uk_users_username"),)  # 用户名唯一索引。


class UserSession(Base):
    """用户登录会话表 ORM 模型。"""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 登录会话自增主键。
    user_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 会话所属用户 ID。
    token: Mapped[str] = mapped_column(String(128), nullable=False)  # 登录凭证 Token。
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Token 过期时间。
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)  # Token 撤销时间，空值表示有效。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 会话创建时间。

    user: Mapped[User] = relationship(back_populates="sessions")  # 会话所属用户。

    __table_args__ = (
        UniqueConstraint("token", name="uk_user_sessions_token"),  # Token 唯一索引。
        Index("idx_user_sessions_user_id", "user_id"),  # 用户 ID 查询索引。
        Index("idx_user_sessions_expires_at", "expires_at"),  # 过期时间查询索引。
    )


class ChatSession(Base):
    """聊天会话表 ORM 模型。"""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 聊天会话 ID。
    user_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 会话所属用户 ID。
    session_title: Mapped[str] = mapped_column(String(120), nullable=False)  # 会话标题。
    session_content: Mapped[str | None] = mapped_column(Text)  # 会话摘要或首轮提问内容。
    remark: Mapped[str | None] = mapped_column(String(255))  # 会话备注。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 会话创建时间。
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )  # 会话最后更新时间。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 会话软删除时间。

    messages: Mapped[list[ChatMessage]] = relationship(back_populates="session", cascade="all, delete-orphan")  # 会话下的消息集合。

    __table_args__ = (Index("idx_chat_sessions_user_updated", "user_id", "updated_at"),)  # 用户会话列表排序索引。


class ChatMessage(Base):
    """聊天消息表 ORM 模型。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 消息自增主键。
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)  # 消息所属会话 ID。
    user_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 消息所属用户 ID。
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 消息角色。
    content: Mapped[str] = mapped_column(mysql.MEDIUMTEXT, nullable=False)  # 消息正文。
    model_name: Mapped[str | None] = mapped_column(String(100))  # 助手回复使用的模型名称。
    total_tokens: Mapped[int] = mapped_column(mysql.INTEGER, nullable=False, default=0, server_default="0")  # 消息消耗的 token 数。
    references_text: Mapped[str | None] = mapped_column(mysql.MEDIUMTEXT)  # 助手回答引用来源文本。
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())  # 消息创建时间。

    session: Mapped[ChatSession] = relationship(back_populates="messages")  # 消息所属会话。

    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id", "id"),  # 会话消息列表索引。
        Index("idx_chat_messages_user_id", "user_id"),  # 用户消息查询索引。
    )


class UserOrder(Base):
    """用户订单表 ORM 模型。"""

    __tablename__ = "user_orders"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)  # 订单自增主键。
    user_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 订单所属用户 ID。
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
        Index("idx_user_orders_user_created", "user_id", "created_at"),  # 用户订单时间索引。
        Index("idx_user_orders_user_status", "user_id", "order_status"),  # 用户订单状态索引。
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
