"""聊天会话和消息 ORM 数据访问方法。"""

from datetime import datetime, timezone

from sqlalchemy import select, update

from app.models import ChatMessage, ChatSession
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql_mappers import map_chat_message, map_chat_session
from app.repositories.mysql_records import ChatMessageRecord, ChatSessionRecord


class ChatMySQLMixin(BaseMySQLMixin):
    """封装聊天会话和消息相关 MySQL 操作。"""

    def list_chat_sessions(self, user_id: int, page: int, page_size: int) -> list[ChatSessionRecord]:
        """分页查询当前用户未删除的聊天会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
        """
        offset = max(page - 1, 0) * page_size
        rows = self._scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None))
            .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_chat_session(row) for row in rows]

    def create_chat_session(
        self,
        session_id: str,
        user_id: int,
        title: str,
        content: str | None,
        remark: str | None,
    ) -> ChatSessionRecord:
        """创建聊天会话。

        Args:
            session_id: 聊天会话 ID。
            user_id: 当前用户 ID，用于数据隔离。
            title: 会话标题。
            content: 会话摘要或首轮提问内容。
            remark: 会话备注。
        """
        chat_session = ChatSession(
            id=session_id,
            user_id=user_id,
            session_title=title,
            session_content=content,
            remark=remark,
        )
        self._add(chat_session)
        self._flush()
        self._refresh(chat_session)
        return map_chat_session(chat_session)

    def get_chat_session(self, user_id: int, session_id: str) -> ChatSessionRecord | None:
        """查询当前用户的单个未删除会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        chat_session = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None))
            .limit(1)
        )
        return map_chat_session(chat_session) if chat_session else None

    def update_chat_session(
        self,
        user_id: int,
        session_id: str,
        title: str | None,
        content: str | None,
        remark: str | None,
    ) -> ChatSessionRecord | None:
        """更新当前用户的聊天会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            title: 新会话标题；None 表示不更新。
            content: 新会话摘要；None 表示不更新。
            remark: 新会话备注；None 表示不更新。
        """
        chat_session = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None))
            .limit(1)
        )
        if not chat_session:
            return None
        if title is not None:
            chat_session.session_title = title
        if content is not None:
            chat_session.session_content = content
        if remark is not None:
            chat_session.remark = remark
        if title is not None or content is not None or remark is not None:
            chat_session.updated_at = _utc_now()
            self._flush()
            self._refresh(chat_session)
        return map_chat_session(chat_session)

    def delete_chat_sessions(self, user_id: int, session_ids: list[str]) -> None:
        """批量软删除当前用户的聊天会话。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_ids: 需要软删除的聊天会话 ID 列表。
        """
        if not session_ids:
            return
        self._execute(
            update(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.id.in_(session_ids))
            .values(deleted_at=_utc_now())
        )

    def add_chat_message(
        self,
        session_id: str,
        user_id: int,
        role: str,
        content: str,
        model_name: str | None = None,
        total_tokens: int = 0,
        references: list[str] | None = None,
    ) -> ChatMessageRecord:
        """新增聊天消息并刷新所属会话更新时间。

        Args:
            session_id: 消息所属会话 ID。
            user_id: 当前用户 ID，用于数据隔离。
            role: 消息角色，例如 user 或 assistant。
            content: 消息正文。
            model_name: 助手回复使用的模型名称。
            total_tokens: 本条消息消耗的 token 数。
            references: 助手回答引用来源列表。
        """
        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            model_name=model_name,
            total_tokens=total_tokens,
            references_text="\n".join(references or []),
        )
        self._add(message)
        self._execute(
            update(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .values(updated_at=_utc_now())
        )
        self._flush()
        self._refresh(message)
        return map_chat_message(message)

    def list_chat_messages(self, user_id: int, session_id: str) -> list[ChatMessageRecord]:
        """查询当前用户某个会话下的全部消息。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        rows = self._scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        return [map_chat_message(row) for row in rows]

    def list_recent_messages(self, user_id: int, session_id: str, limit: int) -> list[ChatMessageRecord]:
        """查询当前用户某个会话的最近若干条消息。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            limit: 最多返回的消息数量。
        """
        rows = list(
            self._scalars(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id.desc())
                .limit(limit)
            )
        )
        return [map_chat_message(row) for row in reversed(rows)]


def _utc_now() -> datetime:
    """返回去掉时区信息的 UTC 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
