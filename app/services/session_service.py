"""聊天会话服务。"""

from __future__ import annotations

from uuid import uuid4

from app.repositories.context_repository import ContextRepository
from app.repositories.mysql.records import ChatSessionRecord
from app.repositories.mysql_repository import MySQLRepository


class SessionService:
    """聊天会话业务服务，负责会话 CRUD 与上下文缓存清理。"""

    def __init__(self, repository: MySQLRepository, context_repository: ContextRepository) -> None:
        """初始化会话服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
            context_repository: 聊天上下文仓储实例。
        """
        self.repository = repository
        self.context_repository = context_repository

    def list_sessions(self, user_id: int, page: int = 1, page_size: int = 25) -> list[ChatSessionRecord]:
        """分页查询当前用户的会话列表，并限制页大小避免一次返回过多数据。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            page: 分页页码。
            page_size: 每页返回的记录数量。
        """
        return self.repository.list_chat_sessions(user_id, max(page, 1), min(max(page_size, 1), 100))

    def create_session(self, user_id: int, title: str, content: str | None = None, remark: str | None = None) -> ChatSessionRecord:
        """创建当前用户的新会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            title: 聊天会话标题。
            content: 消息正文内容。
            remark: 会话备注内容。
        """
        return self.repository.create_chat_session(uuid4().hex, user_id, title.strip()[:120], content, remark)

    def get_session(self, user_id: int, session_id: str) -> ChatSessionRecord | None:
        """按会话 ID 查询当前用户的会话，查不到返回 None。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        return self.repository.get_chat_session(user_id, session_id)

    def update_session(self, user_id: int, session_id: str, title: str | None, content: str | None, remark: str | None) -> ChatSessionRecord | None:
        """更新当前用户的会话基础信息。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            title: 聊天会话标题。
            content: 消息正文内容。
            remark: 会话备注内容。
        """
        return self.repository.update_chat_session(user_id, session_id, title, content, remark)

    def delete_sessions(self, user_id: int, session_ids: list[str]) -> None:
        """软删除会话，并尽量删除对应 Redis 上下文缓存。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_ids: 需要删除的聊天会话 ID 列表。
        """
        self.repository.delete_chat_sessions(user_id, session_ids)
        for session_id in session_ids:
            try:
                self.context_repository.delete_session(user_id, session_id)
            except Exception:
                continue
