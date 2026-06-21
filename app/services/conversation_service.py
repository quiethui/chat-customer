"""转人工与坐席会话编排服务（转人工状态机）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.conversation_bus import ConversationBus
from app.repositories.mysql.records import ChatMessageRecord, ChatSessionRecord, CustomerRecord
from app.repositories.mysql_repository import MySQLRepository

# 坐席队列默认展示的会话状态：等待接入与服务中。
DEFAULT_QUEUE_STATUSES = ("waiting", "serving")


@dataclass(frozen=True)
class ConversationView:
    """坐席视角的会话视图：会话记录 + 所属客户信息。"""

    session: ChatSessionRecord  # 会话记录（含状态、坐席、评分等）。
    customer: CustomerRecord | None  # 会话所属客户记录，可能为空。


class ConversationService:
    """转人工状态机：转人工、接管、坐席回复、关闭、交还机器人。

    状态流转：bot --（客户请求）--> waiting --（坐席接管）--> serving
    --（关闭）--> closed；serving/waiting --（交还）--> bot。
    """

    def __init__(self, repository: MySQLRepository, bus: ConversationBus) -> None:
        """初始化会话编排服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
            bus: 会话事件总线，用于把坐席动作推送给客户 SSE。
        """
        self.repository = repository
        self.bus = bus

    def list_queue(self, statuses: list[str] | None, page: int = 1, page_size: int = 25) -> list[ConversationView]:
        """查询坐席会话队列（全量），并补充每条会话的客户信息。

        Args:
            statuses: 需要过滤的会话状态；为空时使用默认（等待+服务中）。
            page: 分页页码。
            page_size: 每页返回的记录数量。
        """
        effective = statuses if statuses else list(DEFAULT_QUEUE_STATUSES)
        sessions = self.repository.list_conversations(effective, max(page, 1), min(max(page_size, 1), 100))
        return [ConversationView(session=item, customer=self._customer(item.customer_id)) for item in sessions]

    def get_conversation(self, session_id: str) -> ConversationView:
        """查询单个会话详情（坐席视角）。

        Args:
            session_id: 聊天会话 ID。
        """
        session = self.repository.get_conversation(session_id)
        if not session:
            raise ValueError("会话不存在")
        return ConversationView(session=session, customer=self._customer(session.customer_id))

    def list_messages(self, session_id: str) -> list[ChatMessageRecord]:
        """查询会话的全部消息（坐席视角）。

        Args:
            session_id: 聊天会话 ID。
        """
        if not self.repository.get_conversation(session_id):
            raise ValueError("会话不存在")
        return self.repository.list_conversation_messages(session_id)

    def list_customer_messages(self, customer_id: int, session_id: str) -> list[ChatMessageRecord]:
        """查询当前客户某个会话的历史消息（按客户隔离，供复访拉取）。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        if not self.repository.get_chat_session(customer_id, session_id):
            raise ValueError("会话不存在")
        return self.repository.list_chat_messages(customer_id, session_id)

    def list_customer_sessions(self, customer_id: int, limit: int = 50) -> list[ChatSessionRecord]:
        """列出当前客户最近的会话（倒序），供客户端复访恢复与历史会话列表。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            limit: 最多返回的会话数量。
        """
        return self.repository.list_customer_sessions(customer_id, limit)

    def request_handoff(self, customer_id: int, session_id: str) -> ChatSessionRecord:
        """客户请求转人工：bot/serving → waiting，并通知该会话频道。

        Args:
            customer_id: 当前客户 ID，用于校验会话归属。
            session_id: 聊天会话 ID。
        """
        if not self.repository.get_chat_session(customer_id, session_id):
            raise ValueError("会话不存在")
        record = self.repository.update_conversation_status(session_id, "waiting")
        if not record:
            raise ValueError("会话不存在")
        self.repository.commit()
        self.bus.publish(session_id, {"type": "status", "status": "waiting", "message": "正在为您转接人工客服…"})
        customer = self._customer(customer_id)
        self.bus.publish_broadcast(
            {
                "type": "handoff_request",
                "sessionId": record.id,
                "customerId": customer_id,
                "customerNickname": customer.nickname if customer else None,
                "sessionTitle": record.session_title,
                "requestedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
        return record

    def claim(self, agent_id: int, session_id: str) -> ChatSessionRecord:
        """坐席接管等待中的会话：waiting → serving，并通知客户已接入。

        Args:
            agent_id: 接管坐席的用户 ID。
            session_id: 聊天会话 ID。
        """
        record = self.repository.claim_conversation(session_id, agent_id)
        if not record:
            raise ValueError("会话不存在或已被接管")
        self.repository.commit()
        self.bus.publish(session_id, {"type": "status", "status": "serving", "message": "客服已接入，正在为您服务"})
        self.bus.publish_broadcast(
            {"type": "handoff_claimed", "sessionId": record.id, "agentId": agent_id}
        )
        return record

    def reply(self, agent_id: int, session_id: str, content: str) -> ChatMessageRecord:
        """坐席回复消息：落库 sender_type=agent 并推送到客户 SSE。

        Args:
            agent_id: 发送消息的坐席用户 ID。
            session_id: 聊天会话 ID。
            content: 坐席回复正文。
        """
        text = content.strip()
        if not text:
            raise ValueError("回复内容不能为空")
        session = self.repository.get_conversation(session_id)
        if not session:
            raise ValueError("会话不存在")
        if session.status != "serving":
            raise ValueError("请先接管会话再回复")
        message = self.repository.add_agent_message(session_id, agent_id, text)
        if not message:
            raise ValueError("会话不存在")
        self.repository.commit()
        self.bus.publish(
            session_id,
            {"type": "agent_message", "text": text, "messageId": message.id, "agentId": agent_id},
        )
        return message

    def customer_message(self, customer_id: int, session_id: str, content: str) -> ChatMessageRecord:
        """客户在人工会话中给坐席发送消息：落库 sender_type=customer 并推送到会话频道。

        仅在人工模式（waiting/serving）下允许：bot 模式应走机器人问答接口，closed 不可再发言。

        Args:
            customer_id: 当前客户 ID，用于校验会话归属与数据隔离。
            session_id: 聊天会话 ID。
            content: 客户发送的消息正文。
        """
        text = content.strip()
        if not text:
            raise ValueError("消息内容不能为空")
        session = self.repository.get_chat_session(customer_id, session_id)
        if not session:
            raise ValueError("会话不存在")
        if session.status not in ("waiting", "serving"):
            raise ValueError("当前不是人工会话，无法发送消息")
        message = self.repository.add_customer_message(session_id, customer_id, text)
        if not message:
            raise ValueError("会话不存在")
        self.repository.commit()
        self.bus.publish(
            session_id,
            {"type": "customer_message", "text": text, "messageId": message.id, "customerId": customer_id},
        )
        customer = self._customer(customer_id)
        preview = text if len(text) <= 80 else f"{text[:80]}…"
        self.bus.publish_broadcast(
            {
                "type": "customer_message",
                "sessionId": session_id,
                "messageId": message.id,
                "customerId": customer_id,
                "customerNickname": customer.nickname if customer else None,
                "assignedAgentId": session.assigned_agent_id,
                "textPreview": preview,
            }
        )
        return message

    def close(self, session_id: str) -> ChatSessionRecord:
        """关闭会话：状态置为 closed 并通知客户会话结束。

        Args:
            session_id: 聊天会话 ID。
        """
        record = self.repository.update_conversation_status(session_id, "closed")
        if not record:
            raise ValueError("会话不存在")
        self.repository.commit()
        self.bus.publish(session_id, {"type": "status", "status": "closed", "message": "会话已结束，感谢您的咨询"})
        return record

    def handback(self, session_id: str) -> ChatSessionRecord:
        """交还机器人：状态置回 bot、清空坐席，并通知客户已切回智能助手。

        Args:
            session_id: 聊天会话 ID。
        """
        record = self.repository.update_conversation_status(session_id, "bot", mode="bot", clear_agent=True)
        if not record:
            raise ValueError("会话不存在")
        self.repository.commit()
        self.bus.publish(session_id, {"type": "status", "status": "bot", "message": "已为您切换回智能助手"})
        return record

    def rate(self, customer_id: int, session_id: str, rating: int, comment: str | None) -> ChatSessionRecord:
        """客户为自己的会话提交满意度评分。

        Args:
            customer_id: 当前客户 ID，用于校验会话归属。
            session_id: 聊天会话 ID。
            rating: 满意度评分。
            comment: 满意度评价文字，可为空。
        """
        record = self.repository.set_conversation_rating(customer_id, session_id, rating, comment)
        if not record:
            raise ValueError("会话不存在")
        self.repository.commit()
        return record

    def _customer(self, customer_id: int) -> CustomerRecord | None:
        """按 ID 查询客户信息，供队列与详情补充展示。

        Args:
            customer_id: 客户 ID。
        """
        return self.repository.get_customer_by_id(customer_id)
