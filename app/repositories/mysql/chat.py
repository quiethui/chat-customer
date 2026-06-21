"""聊天会话和消息 ORM 数据访问方法。"""

from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.models import ChatMessage, ChatSession
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_chat_message, map_chat_session
from app.repositories.mysql.records import ChatMessageRecord, ChatSessionRecord


class ChatMySQLMixin(BaseMySQLMixin):
    """封装聊天会话和消息相关 MySQL 操作。"""

    def list_chat_sessions(self, customer_id: int, page: int, page_size: int) -> list[ChatSessionRecord]:
        """分页查询当前客户未删除的聊天会话。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
        """
        offset = max(page - 1, 0) * page_size
        rows = self._scalars(
            select(ChatSession)
            .where(ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
            .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_chat_session(row) for row in rows]

    def create_chat_session(
        self,
        session_id: str,
        customer_id: int,
        title: str,
        content: str | None,
        remark: str | None,
    ) -> ChatSessionRecord:
        """创建聊天会话。

        Args:
            session_id: 聊天会话 ID。
            customer_id: 当前客户 ID，用于数据隔离。
            title: 会话标题。
            content: 会话摘要或首轮提问内容。
            remark: 会话备注。
        """
        chat_session = ChatSession(
            id=session_id,
            customer_id=customer_id,
            session_title=title,
            session_content=content,
            remark=remark,
        )
        self._add(chat_session)
        self._flush()
        self._refresh(chat_session)
        return map_chat_session(chat_session)

    def get_chat_session(self, customer_id: int, session_id: str) -> ChatSessionRecord | None:
        """查询当前客户的单个未删除会话。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        chat_session = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
            .limit(1)
        )
        return map_chat_session(chat_session) if chat_session else None

    def update_chat_session(
        self,
        customer_id: int,
        session_id: str,
        title: str | None,
        content: str | None,
        remark: str | None,
    ) -> ChatSessionRecord | None:
        """更新当前客户的聊天会话。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            title: 新会话标题；None 表示不更新。
            content: 新会话摘要；None 表示不更新。
            remark: 新会话备注；None 表示不更新。
        """
        chat_session = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
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

    def delete_chat_sessions(self, customer_id: int, session_ids: list[str]) -> None:
        """批量软删除当前客户的聊天会话。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_ids: 需要软删除的聊天会话 ID 列表。
        """
        if not session_ids:
            return
        self._execute(
            update(ChatSession)
            .where(ChatSession.customer_id == customer_id, ChatSession.id.in_(session_ids))
            .values(deleted_at=_utc_now())
        )

    def add_chat_message(
        self,
        session_id: str,
        customer_id: int,
        role: str,
        content: str,
        model_name: str | None = None,
        total_tokens: int = 0,
        references: list[str] | None = None,
        sender_type: str = "customer",
        agent_id: int | None = None,
    ) -> ChatMessageRecord:
        """新增聊天消息并刷新所属会话更新时间。

        Args:
            session_id: 消息所属会话 ID。
            customer_id: 当前客户 ID，用于数据隔离。
            role: 消息角色（供 LLM 上下文），例如 user 或 assistant。
            content: 消息正文。
            model_name: 助手回复使用的模型名称。
            total_tokens: 本条消息消耗的 token 数。
            references: 助手回答引用来源列表。
            sender_type: 消息发送方，customer=客户、bot=机器人、agent=人工坐席。
            agent_id: 人工消息的坐席用户 ID，非人工消息为空。
        """
        message = ChatMessage(
            session_id=session_id,
            customer_id=customer_id,
            role=role,
            content=content,
            model_name=model_name,
            total_tokens=total_tokens,
            references_text="\n".join(references or []),
            sender_type=sender_type,
            agent_id=agent_id,
        )
        self._add(message)
        self._execute(
            update(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.customer_id == customer_id)
            .values(updated_at=_utc_now())
        )
        self._flush()
        self._refresh(message)
        return map_chat_message(message)

    def list_chat_messages(self, customer_id: int, session_id: str) -> list[ChatMessageRecord]:
        """查询当前客户某个会话下的全部消息。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        rows = self._scalars(
            select(ChatMessage)
            .where(ChatMessage.customer_id == customer_id, ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        return [map_chat_message(row) for row in rows]

    def list_recent_messages(self, customer_id: int, session_id: str, limit: int) -> list[ChatMessageRecord]:
        """查询当前客户某个会话的最近若干条消息。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            limit: 最多返回的消息数量。
        """
        rows = list(
            self._scalars(
                select(ChatMessage)
                .where(ChatMessage.customer_id == customer_id, ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id.desc())
                .limit(limit)
            )
        )
        return [map_chat_message(row) for row in reversed(rows)]

    def list_customer_sessions(self, customer_id: int, limit: int = 50) -> list[ChatSessionRecord]:
        """查询当前客户最近的未删除会话（按活跃时间倒序），供复访恢复与历史会话列表。

        与 ``list_chat_sessions`` 的分页用途不同，本方法面向客户端「我的会话」一次性拉取最近若干条。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            limit: 最多返回的会话数量。
        """
        rows = self._scalars(
            select(ChatSession)
            .where(ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
            .order_by(func.coalesce(ChatSession.last_message_at, ChatSession.updated_at).desc())
            .limit(limit)
        )
        return [map_chat_session(row) for row in rows]

    def reassign_session(self, session_id: str, new_customer_id: int) -> bool:
        """把某个会话及其全部消息改挂到新客户（匿名登录合并用，同事务执行）。

        合并越权防护由调用方负责（须先校验该会话确属来访匿名身份）。

        Args:
            session_id: 待改挂的聊天会话 ID。
            new_customer_id: 目标客户 ID（登录命中的账号）。
        """
        row = self._scalar_one_or_none(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted_at.is_(None)).limit(1)
        )
        if not row:
            return False
        self._execute(
            update(ChatMessage).where(ChatMessage.session_id == session_id).values(customer_id=new_customer_id)
        )
        row.customer_id = new_customer_id
        self._flush()
        return True

    # ---- 坐席端会话队列与转人工相关方法（不按 customer 隔离，坐席可见全量） ----

    def list_conversations(
        self,
        statuses: list[str] | None,
        page: int,
        page_size: int,
    ) -> list[ChatSessionRecord]:
        """分页查询坐席会话队列（全量，不按客户隔离），按最近活跃倒序。

        Args:
            statuses: 需要过滤的会话状态列表；为空时返回全部未删除会话。
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
        """
        offset = max(page - 1, 0) * page_size
        conditions = [ChatSession.deleted_at.is_(None)]
        if statuses:
            conditions.append(ChatSession.status.in_(statuses))
        rows = self._scalars(
            select(ChatSession)
            .where(*conditions)
            .order_by(func.coalesce(ChatSession.last_message_at, ChatSession.updated_at).desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_chat_session(row) for row in rows]

    def get_conversation(self, session_id: str) -> ChatSessionRecord | None:
        """按会话 ID 查询单个未删除会话（坐席视角，不按客户隔离）。

        Args:
            session_id: 聊天会话 ID。
        """
        row = self._scalar_one_or_none(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted_at.is_(None)).limit(1)
        )
        return map_chat_session(row) if row else None

    def list_conversation_messages(self, session_id: str) -> list[ChatMessageRecord]:
        """查询某个会话下的全部消息（坐席视角，不按客户隔离）。

        Args:
            session_id: 聊天会话 ID。
        """
        rows = self._scalars(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc())
        )
        return [map_chat_message(row) for row in rows]

    def claim_conversation(self, session_id: str, agent_id: int) -> ChatSessionRecord | None:
        """坐席接管处于等待状态的会话：waiting → serving 并记录坐席。

        Args:
            session_id: 聊天会话 ID。
            agent_id: 接管坐席的用户 ID。
        """
        row = self._scalar_one_or_none(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted_at.is_(None)).limit(1)
        )
        if not row or row.status != "waiting":
            return None
        row.status = "serving"
        row.mode = "agent"
        row.assigned_agent_id = agent_id
        row.last_message_at = _utc_now()
        self._flush()
        self._refresh(row)
        return map_chat_session(row)

    def update_conversation_status(
        self,
        session_id: str,
        new_status: str,
        mode: str | None = None,
        clear_agent: bool = False,
    ) -> ChatSessionRecord | None:
        """更新会话状态（转人工/关闭/交还机器人等状态机流转通用方法）。

        Args:
            session_id: 聊天会话 ID。
            new_status: 目标会话状态：bot/waiting/serving/closed。
            mode: 目标服务模式：bot/agent；为空表示不更新。
            clear_agent: 是否清空接管坐席（交还机器人时使用）。
        """
        row = self._scalar_one_or_none(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted_at.is_(None)).limit(1)
        )
        if not row:
            return None
        row.status = new_status
        if mode is not None:
            row.mode = mode
        if clear_agent:
            row.assigned_agent_id = None
        row.last_message_at = _utc_now()
        self._flush()
        self._refresh(row)
        return map_chat_session(row)

    def add_agent_message(self, session_id: str, agent_id: int, content: str) -> ChatMessageRecord | None:
        """新增一条人工坐席消息（sender_type=agent）并刷新会话活跃时间。

        Args:
            session_id: 消息所属会话 ID。
            agent_id: 发送消息的坐席用户 ID。
            content: 坐席回复正文。
        """
        row = self._scalar_one_or_none(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.deleted_at.is_(None)).limit(1)
        )
        if not row:
            return None
        message = ChatMessage(
            session_id=session_id,
            customer_id=row.customer_id,
            role="assistant",
            sender_type="agent",
            agent_id=agent_id,
            content=content,
        )
        self._add(message)
        row.last_message_at = _utc_now()
        row.updated_at = _utc_now()
        self._flush()
        self._refresh(message)
        return map_chat_message(message)

    def add_customer_message(self, session_id: str, customer_id: int, content: str) -> ChatMessageRecord | None:
        """新增一条客户在人工会话中发送的消息（sender_type=customer）并刷新会话活跃时间。

        与 ``add_chat_message`` 不同，本方法用于人工会话：按客户隔离校验会话归属，
        且同步刷新 ``last_message_at`` 以让坐席队列把活跃会话排到前面。

        Args:
            session_id: 消息所属会话 ID。
            customer_id: 当前客户 ID，用于数据隔离与会话归属校验。
            content: 客户发送的消息正文。
        """
        row = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
            .limit(1)
        )
        if not row:
            return None
        message = ChatMessage(
            session_id=session_id,
            customer_id=customer_id,
            role="user",
            sender_type="customer",
            content=content,
        )
        self._add(message)
        row.last_message_at = _utc_now()
        row.updated_at = _utc_now()
        self._flush()
        self._refresh(message)
        return map_chat_message(message)

    def set_conversation_rating(
        self,
        customer_id: int,
        session_id: str,
        rating: int,
        rating_comment: str | None,
    ) -> ChatSessionRecord | None:
        """客户为自己的会话写入满意度评分（按客户隔离）。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            rating: 满意度评分。
            rating_comment: 满意度评价文字，可为空。
        """
        row = self._scalar_one_or_none(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.customer_id == customer_id, ChatSession.deleted_at.is_(None))
            .limit(1)
        )
        if not row:
            return None
        row.rating = rating
        row.rating_comment = rating_comment
        self._flush()
        self._refresh(row)
        return map_chat_session(row)

    def touch_last_message_at(self, session_id: str) -> None:
        """刷新会话最近活跃时间，用于坐席队列排序。

        Args:
            session_id: 聊天会话 ID。
        """
        self._execute(
            update(ChatSession).where(ChatSession.id == session_id).values(last_message_at=_utc_now())
        )


def _utc_now() -> datetime:
    """返回去掉时区信息的 UTC 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
