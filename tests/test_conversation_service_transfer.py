"""测试会话转接功能：正常转接、转给不存在的坐席、转给自己、非 serving 状态转接。"""

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
def agent_a() -> ManagerRecord:
    """模拟普通坐席 A。"""
    return ManagerRecord(
        id=10,
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
        id=11,
        username="agent_b",
        password_hash="hash",
        salt="salt",
        nickname="客服 B",
        avatar=None,
        status=1,
        is_admin=0,
    )


def test_transfer_success(service: ConversationService, agent_a: ManagerRecord, agent_b: ManagerRecord) -> None:
    """正常转接：坐席 A 持有的 serving 会话转给坐席 B。"""
    # 准备：创建坐席 A 和 B，创建会话并由 A 接管
    service.repository.create_manager("agent_a", "hash", "salt", "客服 A")
    service.repository.create_manager("agent_b", "hash", "salt", "客服 B")
    service.repository.commit()

    customer_id = 200
    session = service.repository.create_chat_session("transfer-session-1", customer_id, "转接测试", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 执行转接
    result = service.transfer(agent_a, session.id, agent_b.id, "工作交接")
    assert result.assigned_agent_id == agent_b.id
    assert result.status == "serving"


def test_transfer_to_nonexistent_agent(service: ConversationService, agent_a: ManagerRecord) -> None:
    """转接给不存在的坐席 → ValueError。"""
    service.repository.create_manager("agent_a", "hash", "salt", "客服 A")
    service.repository.commit()

    customer_id = 201
    session = service.repository.create_chat_session("transfer-session-2", customer_id, "转接测试", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 转接给不存在的坐席
    with pytest.raises(ValueError, match="目标坐席不存在或不可用"):
        service.transfer(agent_a, session.id, 9999, "测试")


def test_transfer_to_self(service: ConversationService, agent_a: ManagerRecord) -> None:
    """转接给自己 → ValueError。"""
    service.repository.create_manager("agent_a", "hash", "salt", "客服 A")
    service.repository.commit()

    customer_id = 202
    session = service.repository.create_chat_session("transfer-session-3", customer_id, "转接测试", None, None)
    service.repository.update_conversation_status(session.id, "serving")
    service.repository.update_conversation_assigned_agent(session.id, agent_a.id)
    service.repository.commit()

    # 转给自己
    with pytest.raises(ValueError, match="不能转接给当前坐席"):
        service.transfer(agent_a, session.id, agent_a.id, "测试")


def test_transfer_non_serving_session(service: ConversationService, agent_a: ManagerRecord, agent_b: ManagerRecord) -> None:
    """非 serving 状态的会话无法转接 → ValueError。"""
    service.repository.create_manager("agent_a", "hash", "salt", "客服 A")
    service.repository.create_manager("agent_b", "hash", "salt", "客服 B")
    service.repository.commit()

    customer_id = 203
    session = service.repository.create_chat_session("transfer-session-4", customer_id, "转接测试", None, None)
    service.repository.update_conversation_status(session.id, "waiting")  # 状态为 waiting
    service.repository.commit()

    # 尝试转接 waiting 状态的会话
    with pytest.raises(ValueError, match="只能转接服务中的会话"):
        service.transfer(agent_a, session.id, agent_b.id, "测试")
