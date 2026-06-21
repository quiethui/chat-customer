"""客户认证服务的单元测试。"""

from dataclasses import replace
from datetime import datetime, timedelta

from app.repositories.mysql.records import ChatSessionRecord, CustomerRecord, CustomerSessionRecord
from app.services.auth_service import hash_password
from app.services.customer_auth_service import CustomerAuthService


class FakeCustomerRepository:
    """内存实现的客户仓储，覆盖 CustomerAuthService 用到的方法。"""

    def __init__(self) -> None:
        self.customers: dict[int, CustomerRecord] = {}
        self.sessions: dict[str, CustomerSessionRecord] = {}
        self.revoked: set[str] = set()
        self.chat_sessions: dict[str, int] = {}  # session_id -> customer_id
        self.last_login: dict[int, tuple[datetime, str | None]] = {}
        self.reassigned: list[tuple[str, int]] = []
        self._next_id = 1

    def create_customer(
        self,
        customer_no: str,
        nickname: str | None = None,
        source: str = "web",
        is_anonymous: int = 1,
        phone: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
        salt: str | None = None,
    ) -> CustomerRecord:
        customer = CustomerRecord(
            id=self._next_id,
            customer_no=customer_no,
            nickname=nickname,
            phone=phone,
            email=email,
            password_hash=password_hash,
            salt=salt,
            source=source,
            is_anonymous=is_anonymous,
            status=1,
        )
        self.customers[customer.id] = customer
        self._next_id += 1
        return customer

    def get_customer_by_id(self, customer_id: int) -> CustomerRecord | None:
        return self.customers.get(customer_id)

    def get_customer_by_username(self, username: str) -> CustomerRecord | None:
        for customer in self.customers.values():
            if customer.username == username and customer.deleted_at is None:
                return customer
        return None

    def create_registered_customer(
        self,
        customer_no: str,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None = None,
        source: str = "web",
        avatar: str | None = None,
        status: int = 1,
    ) -> CustomerRecord:
        customer = CustomerRecord(
            id=self._next_id,
            customer_no=customer_no,
            username=username,
            nickname=nickname,
            phone=None,
            email=None,
            password_hash=password_hash,
            salt=salt,
            source=source,
            is_anonymous=0,
            status=status,
            avatar=avatar,
        )
        self.customers[customer.id] = customer
        self._next_id += 1
        return customer

    def update_customer_credentials(
        self,
        customer_id: int,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None = None,
    ) -> CustomerRecord | None:
        customer = self.customers.get(customer_id)
        if not customer:
            return None
        updated = replace(
            customer,
            username=username,
            password_hash=password_hash,
            salt=salt,
            nickname=nickname if nickname is not None else customer.nickname,
            is_anonymous=0,
        )
        self.customers[customer_id] = updated
        return updated

    def update_last_login(self, customer_id: int, at: datetime, ip: str | None) -> None:
        self.last_login[customer_id] = (at, ip)

    def create_customer_session(self, customer_id: int, token: str, ttl_minutes: int) -> CustomerSessionRecord:
        record = CustomerSessionRecord(
            id=len(self.sessions) + 1,
            customer_id=customer_id,
            token=token,
            expires_at=datetime(2026, 1, 1) + timedelta(minutes=ttl_minutes),
        )
        self.sessions[token] = record
        return record

    def get_customer_session(self, token: str) -> CustomerSessionRecord | None:
        if token in self.revoked:
            return None
        return self.sessions.get(token)

    def revoke_customer_session(self, token: str) -> None:
        self.revoked.add(token)

    def list_customer_sessions(self, customer_id: int, limit: int = 50) -> list[ChatSessionRecord]:
        now = datetime(2026, 1, 1)
        return [
            ChatSessionRecord(
                id=session_id,
                customer_id=owner,
                session_title="历史会话",
                session_content=None,
                remark=None,
                created_at=now,
                updated_at=now,
            )
            for session_id, owner in self.chat_sessions.items()
            if owner == customer_id
        ][:limit]

    def reassign_session(self, session_id: str, new_customer_id: int) -> bool:
        if session_id not in self.chat_sessions:
            return False
        self.chat_sessions[session_id] = new_customer_id
        self.reassigned.append((session_id, new_customer_id))
        return True


def _service() -> tuple[CustomerAuthService, FakeCustomerRepository]:
    repo = FakeCustomerRepository()
    return CustomerAuthService(repo, session_ttl_minutes=60), repo  # type: ignore[arg-type]


def test_create_visitor_issues_token_and_anonymous_customer() -> None:
    service, repo = _service()
    result = service.create_visitor()
    assert result.customer.is_anonymous == 1
    assert result.customer.customer_no.startswith("VISITOR-")
    assert repo.get_customer_session(result.token) is not None


def test_authenticate_token_valid_returns_customer() -> None:
    service, _ = _service()
    result = service.create_visitor()
    authenticated = service.authenticate_token(result.token)
    assert authenticated is not None
    assert authenticated.id == result.customer.id


def test_authenticate_token_unknown_returns_none() -> None:
    service, _ = _service()
    assert service.authenticate_token("does-not-exist") is None


def test_authenticate_token_disabled_customer_returns_none() -> None:
    service, repo = _service()
    result = service.create_visitor()
    repo.customers[result.customer.id] = replace(repo.customers[result.customer.id], status=0)
    assert service.authenticate_token(result.token) is None


def test_create_visitor_records_source() -> None:
    service, _ = _service()
    result = service.create_visitor(source="widget")
    assert result.customer.source == "widget"


def test_register_upgrades_anonymous_in_place() -> None:
    service, repo = _service()
    visitor = service.create_visitor()
    result = service.register("alice", "secret123", "爱丽丝", visitor.customer, visitor.token)
    # 同一行就地升级：customer_id 不变，转为注册客户，token 复用。
    assert result.customer.id == visitor.customer.id
    assert result.customer.is_anonymous == 0
    assert result.customer.username == "alice"
    assert result.token == visitor.token
    assert repo.customers[visitor.customer.id].username == "alice"


def test_register_creates_new_when_no_current() -> None:
    service, _ = _service()
    result = service.register("bob", "secret123", None, None, None)
    assert result.customer.is_anonymous == 0
    assert result.customer.username == "bob"
    assert service.authenticate_token(result.token) is not None


def test_register_rejects_duplicate_username() -> None:
    service, _ = _service()
    service.register("carol", "secret123", None, None, None)
    try:
        service.register("carol", "another123", None, None, None)
        raise AssertionError("应当因账号重复抛出 ValueError")
    except ValueError as error:
        assert "已被注册" in str(error)


def test_login_success_records_last_login() -> None:
    service, repo = _service()
    service.register("dave", "secret123", None, None, None)
    result = service.login("dave", "secret123", None, "203.0.113.9")
    assert result.customer.username == "dave"
    assert result.customer.id in repo.last_login
    assert repo.last_login[result.customer.id][1] == "203.0.113.9"


def test_login_wrong_password_raises() -> None:
    service, _ = _service()
    service.register("erin", "secret123", None, None, None)
    try:
        service.login("erin", "wrongpass", None, None)
        raise AssertionError("应当因密码错误抛出 ValueError")
    except ValueError as error:
        assert "账号或密码错误" in str(error)


def test_login_merges_anonymous_sessions() -> None:
    service, repo = _service()
    account = service.register("frank", "secret123", None, None, None).customer
    visitor = service.create_visitor()
    repo.chat_sessions["sess-1"] = visitor.customer.id
    repo.chat_sessions["sess-2"] = visitor.customer.id
    service.login("frank", "secret123", visitor.customer, None)
    # 来访匿名身份的会话应被改挂到登录账号。
    assert ("sess-1", account.id) in repo.reassigned
    assert ("sess-2", account.id) in repo.reassigned
    assert repo.chat_sessions["sess-1"] == account.id


def test_logout_revokes_token() -> None:
    service, _ = _service()
    visitor = service.create_visitor()
    assert service.authenticate_token(visitor.token) is not None
    service.logout(visitor.token)
    assert service.authenticate_token(visitor.token) is None
