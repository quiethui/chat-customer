"""测试坐席权限隔离：非管理员越权操作他人会话应抛 PermissionError。"""

import pytest

from app.dependencies import create_conversation_bus, create_mysql_repository
from app.repositories.mysql.records import ManagerRecord
from app.services.conversation_service import ConversationService


@pytest.fixture
def service() -> ConversationService:
    """创建 ConversationService 实例。"""
    repo = create_mysql_repository()
    bus = create_conversation_bus()
    service = ConversationService(repo, bus)
    yield service
    repo.rollback()
    repo.close()


@pytest.fixture
def admin_agent() -> ManagerRecord:
    """模拟管理员坐席。"""
    return ManagerRecord(
        id=1,
        username="admin",
        password_hash="hash",
        salt="salt",
        nickname="管理员",
        avatar=None,
        status=1,
        is_admin=1,
    )


@pytest.fixture
def agent_a() -> ManagerRecord:
    """模拟普通坐席 A。"""
    return ManagerRecord(
        id=2,
        username="agent_a",
        password_hash="hash",
        salt="salt",
        nickname="客服 A",
        avatar=None,
        status=1,
        is_admin=0,
    )


@pytest.fixture
def agent_b() -> ManagerRecord:
    """模拟普通坐席 B。"""
    return ManagerRecord(
        id=3,
        username="agent_b",
        password_hash="hash",
        salt="salt",
        nickname="客服 B",
        avatar=None,
        status=1,
        is_admin=0,
    )


def test_agent_cannot_reply_others_session(service: ConversationService, agent_a: ManagerRecord, agent_b: ManagerRecord) -> None:
    """非管理员坐席 B 无权回复坐席 A 持有的会话。"""
    # 创建测试会话并由坐席 A 接管
    customer_id = 100
    session = service.repository.create_chat_session("test-session-1", customer_id, "测试会话", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 坐席 B 尝试回复 → 应抛 PermissionError
    with pytest.raises(PermissionError, match="您没有权限回复此会话"):
        service.reply(agent_b, session.id, "尝试越权回复")


def test_agent_cannot_close_others_session(service: ConversationService, agent_a: ManagerRecord, agent_b: ManagerRecord) -> None:
    """非管理员坐席 B 无权结束坐席 A 持有的会话。"""
    customer_id = 101
    session = service.repository.create_chat_session("test-session-2", customer_id, "测试会话", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 坐席 B 尝试结束 → 应抛 PermissionError
    with pytest.raises(PermissionError, match="您没有权限关闭此会话"):
        service.close(agent_b, session.id)


def test_agent_cannot_handback_others_session(service: ConversationService, agent_a: ManagerRecord, agent_b: ManagerRecord) -> None:
    """非管理员坐席 B 无权交还坐席 A 持有的会话。"""
    customer_id = 102
    session = service.repository.create_chat_session("test-session-3", customer_id, "测试会话", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 坐席 B 尝试交还 → 应抛 PermissionError
    with pytest.raises(PermissionError, match="您没有权限交还此会话"):
        service.handback(agent_b, session.id)


def test_admin_can_operate_any_session(service: ConversationService, admin_agent: ManagerRecord, agent_a: ManagerRecord) -> None:
    """管理员可以操作任何坐席的会话。"""
    customer_id = 103
    session = service.repository.create_chat_session("test-session-4", customer_id, "测试会话", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 管理员回复 → 应成功
    message = service.reply(admin_agent, session.id, "管理员介入")
    assert message.content == "管理员介入"
    assert message.agent_id == admin_agent.id

    # 管理员结束 → 应成功
    result = service.close(admin_agent, session.id)
    assert result.status == "closed"
