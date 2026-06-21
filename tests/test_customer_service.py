"""后台客户管理服务的单元测试。"""

from dataclasses import replace
from datetime import datetime

from app.repositories.mysql.records import CustomerRecord
from app.schemas.customer import CustomerListQuery
from app.services.customer_service import CustomerService


class FakeCustomerAdminRepository:
    """内存实现的客户仓储，覆盖 CustomerService 用到的方法。"""

    def __init__(self) -> None:
        self.customers: dict[int, CustomerRecord] = {}
        self._next_id = 1

    def get_customer_by_username(self, username: str) -> CustomerRecord | None:
        for customer in self.customers.values():
            if customer.username == username and customer.deleted_at is None:
                return customer
        return None

    def get_customer_by_id(self, customer_id: int) -> CustomerRecord | None:
        customer = self.customers.get(customer_id)
        if customer and customer.deleted_at is None:
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
            created_at=datetime(2026, 1, 1),
        )
        self.customers[customer.id] = customer
        self._next_id += 1
        return customer

    def _filtered(
        self,
        username: str | None,
        status: int | None,
        registered_from: datetime | None,
        registered_to: datetime | None,
        last_login_ip: str | None,
    ) -> list[CustomerRecord]:
        rows = [c for c in self.customers.values() if c.deleted_at is None]
        if username:
            rows = [c for c in rows if c.username and username in c.username]
        if status is not None:
            rows = [c for c in rows if c.status == status]
        if registered_from is not None:
            rows = [c for c in rows if c.created_at and c.created_at >= registered_from]
        if registered_to is not None:
            rows = [c for c in rows if c.created_at and c.created_at <= registered_to]
        if last_login_ip:
            rows = [c for c in rows if c.last_login_ip and last_login_ip in c.last_login_ip]
        return rows

    def list_customers(
        self,
        page: int,
        page_size: int,
        username: str | None = None,
        status: int | None = None,
        registered_from: datetime | None = None,
        registered_to: datetime | None = None,
        last_login_ip: str | None = None,
    ) -> list[CustomerRecord]:
        rows = self._filtered(username, status, registered_from, registered_to, last_login_ip)
        offset = max(page - 1, 0) * page_size
        return rows[offset : offset + page_size]

    def count_customers(
        self,
        username: str | None = None,
        status: int | None = None,
        registered_from: datetime | None = None,
        registered_to: datetime | None = None,
        last_login_ip: str | None = None,
    ) -> int:
        return len(self._filtered(username, status, registered_from, registered_to, last_login_ip))

    def update_customer(
        self,
        customer_id: int,
        nickname: str | None = None,
        avatar: str | None = None,
        status: int | None = None,
        password_hash: str | None = None,
        salt: str | None = None,
    ) -> CustomerRecord | None:
        customer = self.customers.get(customer_id)
        if not customer or customer.deleted_at is not None:
            return None
        updated = replace(
            customer,
            nickname=nickname if nickname is not None else customer.nickname,
            avatar=avatar if avatar is not None else customer.avatar,
            status=status if status is not None else customer.status,
            password_hash=password_hash if password_hash is not None else customer.password_hash,
            salt=salt if salt is not None else customer.salt,
        )
        self.customers[customer_id] = updated
        return updated

    def soft_delete_customer(self, customer_id: int) -> CustomerRecord | None:
        customer = self.customers.get(customer_id)
        if not customer or customer.deleted_at is not None:
            return None
        updated = replace(customer, deleted_at=datetime(2026, 6, 21))
        self.customers[customer_id] = updated
        return updated


def _service() -> tuple[CustomerService, FakeCustomerAdminRepository]:
    repo = FakeCustomerAdminRepository()
    return CustomerService(repo), repo  # type: ignore[arg-type]


def test_create_customer_persists_registered_customer() -> None:
    service, _ = _service()
    customer = service.create_customer("alice", "secret123", "爱丽丝", "http://avatar", 1)
    assert customer.username == "alice"
    assert customer.is_anonymous == 0
    assert customer.nickname == "爱丽丝"
    assert customer.avatar == "http://avatar"
    assert customer.password_hash and customer.salt


def test_create_customer_rejects_duplicate_username() -> None:
    service, _ = _service()
    service.create_customer("bob", "secret123", None, None, 1)
    try:
        service.create_customer("bob", "another123", None, None, 1)
        raise AssertionError("应当因账号重复抛出 ValueError")
    except ValueError as error:
        assert "已被注册" in str(error)


def test_list_customers_filters_by_username() -> None:
    service, _ = _service()
    service.create_customer("alice", "secret123", None, None, 1)
    service.create_customer("bob", "secret123", None, None, 1)
    items, total = service.list_customers(CustomerListQuery(current=1, pageSize=20, username="ali"))
    assert total == 1
    assert items[0].username == "alice"


def test_list_customers_filters_by_status() -> None:
    service, repo = _service()
    service.create_customer("alice", "secret123", None, None, 1)
    disabled = service.create_customer("bob", "secret123", None, None, 0)
    items, total = service.list_customers(CustomerListQuery(current=1, pageSize=20, status=0))
    assert total == 1
    assert items[0].id == disabled.id
    assert repo  # 引用以示意仓储被驱动


def test_list_customers_filters_by_registered_range() -> None:
    service, repo = _service()
    early = service.create_customer("alice", "secret123", None, None, 1)
    late = service.create_customer("bob", "secret123", None, None, 1)
    repo.customers[late.id] = replace(repo.customers[late.id], created_at=datetime(2026, 3, 1))
    repo.customers[early.id] = replace(repo.customers[early.id], created_at=datetime(2026, 1, 1))
    items, total = service.list_customers(
        CustomerListQuery(current=1, pageSize=20, registeredFrom="2026-02-01")
    )
    assert total == 1
    assert items[0].id == late.id


def test_update_customer_changes_fields() -> None:
    service, _ = _service()
    created = service.create_customer("carol", "secret123", "旧昵称", None, 1)
    updated = service.update_customer(created.id, "新昵称", None, None, None)
    assert updated is not None
    assert updated.nickname == "新昵称"


def test_set_status_disables_customer() -> None:
    service, _ = _service()
    created = service.create_customer("dave", "secret123", None, None, 1)
    updated = service.set_status(created.id, 0)
    assert updated is not None
    assert updated.status == 0


def test_delete_customer_soft_deletes() -> None:
    service, repo = _service()
    created = service.create_customer("erin", "secret123", None, None, 1)
    deleted = service.delete_customer(created.id)
    assert deleted is not None
    assert deleted.deleted_at is not None
    # 软删后不再出现在列表中。
    _, total = service.list_customers(CustomerListQuery(current=1, pageSize=20))
    assert total == 0
    assert repo.get_customer_by_id(created.id) is None
