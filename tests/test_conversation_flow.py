"""转人工状态机 ConversationService 的单元测试。

用内存假仓储 + 假事件总线覆盖「转人工 → 接管 → 回复 → 关闭 / 交还 / 评分」全流程，
并校验状态流转、坐席消息落库与事件推送，无需真实数据库或 Redis。
"""

from dataclasses import replace
from datetime import datetime

import pytest

from app.repositories.mysql.records import ChatMessageRecord, ChatSessionRecord, CustomerRecord
from app.services.conversation_service import ConversationService


class FakeBus:
    """记录发布事件的假事件总线。"""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self.broadcasts: list[dict] = []

    def publish(self, session_id: str, event: dict) -> None:
        self.published.append((session_id, event))

    def publish_broadcast(self, event: dict) -> None:
        self.broadcasts.append(event)


class FakeConversationRepository:
    """内存实现的会话仓储，覆盖 ConversationService 用到的方法。"""

    def __init__(self) -> None:
        self.sessions: dict[str, ChatSessionRecord] = {}
        self.customers: dict[int, CustomerRecord] = {}
        self.messages: list[ChatMessageRecord] = []
        self.commits = 0
        self._next_msg_id = 1

    def add_session(self, session_id: str, customer_id: int, status: str = "bot", mode: str = "bot") -> ChatSessionRecord:
        session = ChatSessionRecord(
            id=session_id,
            customer_id=customer_id,
            session_title="会话",
            session_content=None,
            remark=None,
            created_at=datetime(2026, 6, 1),
            updated_at=datetime(2026, 6, 1),
            status=status,
            mode=mode,
        )
        self.sessions[session_id] = session
        self.customers[customer_id] = CustomerRecord(
            id=customer_id,
            customer_no=f"VISITOR-{customer_id}",
            nickname=f"访客{customer_id}",
            phone=None,
            email=None,
            password_hash=None,
            salt=None,
            source="web",
            is_anonymous=1,
            status=1,
        )
        return session

    def get_chat_session(self, customer_id: int, session_id: str) -> ChatSessionRecord | None:
        session = self.sessions.get(session_id)
        return session if session and session.customer_id == customer_id else None

    def get_conversation(self, session_id: str) -> ChatSessionRecord | None:
        return self.sessions.get(session_id)

    def list_conversations(self, statuses: list[str] | None, page: int, page_size: int) -> list[ChatSessionRecord]:
        return [s for s in self.sessions.values() if not statuses or s.status in statuses]

    def list_conversation_messages(self, session_id: str) -> list[ChatMessageRecord]:
        return [m for m in self.messages if m.session_id == session_id]

    def list_chat_messages(self, customer_id: int, session_id: str) -> list[ChatMessageRecord]:
        return [m for m in self.messages if m.session_id == session_id and m.customer_id == customer_id]

    def claim_conversation(self, session_id: str, agent_id: int) -> ChatSessionRecord | None:
        session = self.sessions.get(session_id)
        if not session or session.status != "waiting":
            return None
        updated = replace(session, status="serving", mode="agent", assigned_agent_id=agent_id)
        self.sessions[session_id] = updated
        return updated

    def update_conversation_status(
        self, session_id: str, new_status: str, mode: str | None = None, clear_agent: bool = False
    ) -> ChatSessionRecord | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        updated = replace(
            session,
            status=new_status,
            mode=mode if mode is not None else session.mode,
            assigned_agent_id=None if clear_agent else session.assigned_agent_id,
        )
        self.sessions[session_id] = updated
        return updated

    def add_agent_message(self, session_id: str, agent_id: int, content: str) -> ChatMessageRecord | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        message = ChatMessageRecord(
            id=self._next_msg_id,
            session_id=session_id,
            customer_id=session.customer_id,
            role="assistant",
            content=content,
            model_name=None,
            total_tokens=0,
            references_text=None,
            created_at=datetime(2026, 6, 1),
            sender_type="agent",
            agent_id=agent_id,
        )
        self._next_msg_id += 1
        self.messages.append(message)
        return message

    def add_customer_message(self, session_id: str, customer_id: int, content: str) -> ChatMessageRecord | None:
        session = self.sessions.get(session_id)
        if not session or session.customer_id != customer_id:
            return None
        message = ChatMessageRecord(
            id=self._next_msg_id,
            session_id=session_id,
            customer_id=customer_id,
            role="user",
            content=content,
            model_name=None,
            total_tokens=0,
            references_text=None,
            created_at=datetime(2026, 6, 1),
            sender_type="customer",
            agent_id=None,
        )
        self._next_msg_id += 1
        self.messages.append(message)
        return message

    def set_conversation_rating(
        self, customer_id: int, session_id: str, rating: int, rating_comment: str | None
    ) -> ChatSessionRecord | None:
        session = self.sessions.get(session_id)
        if not session or session.customer_id != customer_id:
            return None
        updated = replace(session, rating=rating, rating_comment=rating_comment)
        self.sessions[session_id] = updated
        return updated

    def get_customer_by_id(self, customer_id: int) -> CustomerRecord | None:
        return self.customers.get(customer_id)

    def commit(self) -> None:
        self.commits += 1


def _service() -> tuple[ConversationService, FakeConversationRepository, FakeBus]:
    repo = FakeConversationRepository()
    bus = FakeBus()
    return ConversationService(repo, bus), repo, bus  # type: ignore[arg-type]


def test_full_handoff_to_close_flow() -> None:
    """走通：转人工 → 接管 → 坐席回复 → 关闭，并校验状态与事件推送。"""
    service, repo, bus = _service()
    repo.add_session("s1", customer_id=1, status="bot")

    handoff = service.request_handoff(1, "s1")
    assert handoff.status == "waiting"

    claimed = service.claim(agent_id=7, session_id="s1")
    assert claimed.status == "serving"
    assert claimed.assigned_agent_id == 7

    message = service.reply(agent_id=7, session_id="s1", content="您好，很高兴为您服务")
    assert message.sender_type == "agent"
    assert message.agent_id == 7

    closed = service.close("s1")
    assert closed.status == "closed"

    # 事件总线依次推送：waiting → serving → agent_message → closed。
    kinds = [event.get("status") or event.get("type") for _, event in bus.published]
    assert kinds == ["waiting", "serving", "agent_message", "closed"]


def test_claim_requires_waiting_status() -> None:
    """未处于等待状态的会话不可被接管。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="bot")
    with pytest.raises(ValueError):
        service.claim(agent_id=7, session_id="s1")


def test_reply_requires_serving_status() -> None:
    """未接管（非 serving）的会话不允许坐席回复。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="waiting")
    with pytest.raises(ValueError):
        service.reply(agent_id=7, session_id="s1", content="hi")


def test_handoff_rejects_other_customer_session() -> None:
    """客户不能对不属于自己的会话发起转人工。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="bot")
    with pytest.raises(ValueError):
        service.request_handoff(2, "s1")


def test_handback_resets_to_bot() -> None:
    """交还机器人后状态回到 bot、清空坐席。"""
    service, repo, bus = _service()
    repo.add_session("s1", customer_id=1, status="serving", mode="agent")
    record = service.handback("s1")
    assert record.status == "bot"
    assert record.mode == "bot"
    assert record.assigned_agent_id is None
    assert bus.published[-1][1]["status"] == "bot"


def test_rate_records_rating() -> None:
    """客户评分写入会话。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="closed")
    record = service.rate(1, "s1", rating=5, comment="很满意")
    assert record.rating == 5


def test_list_queue_enriches_customer_nickname() -> None:
    """坐席队列补充客户昵称。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="waiting")
    views = service.list_queue(["waiting"])
    assert len(views) == 1
    assert views[0].customer is not None
    assert views[0].customer.nickname == "访客1"


@pytest.mark.parametrize("session_status", ["waiting", "serving"])
def test_customer_message_in_human_session(session_status: str) -> None:
    """人工模式（waiting/serving）下客户消息落库为 customer 并推送会话频道。"""
    service, repo, bus = _service()
    repo.add_session("s1", customer_id=1, status=session_status, mode="agent")

    message = service.customer_message(1, "s1", "我的订单还没发货")
    assert message.sender_type == "customer"
    assert message.role == "user"
    assert message.content == "我的订单还没发货"
    assert repo.commits == 1
    assert bus.published[-1][1]["type"] == "customer_message"
    assert bus.published[-1][1]["customerId"] == 1


@pytest.mark.parametrize("session_status", ["bot", "closed"])
def test_customer_message_rejected_outside_human_session(session_status: str) -> None:
    """非人工模式（bot/closed）下客户不能通过人工消息接口发言。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status=session_status)
    with pytest.raises(ValueError):
        service.customer_message(1, "s1", "你好")


def test_customer_message_rejects_other_customer_session() -> None:
    """客户不能向不属于自己的会话发送消息。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="serving", mode="agent")
    with pytest.raises(ValueError):
        service.customer_message(2, "s1", "你好")


def test_customer_message_rejects_empty_content() -> None:
    """空白消息不允许发送。"""
    service, repo, _ = _service()
    repo.add_session("s1", customer_id=1, status="serving", mode="agent")
    with pytest.raises(ValueError):
        service.customer_message(1, "s1", "   ")
