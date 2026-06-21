"""后台客户管理服务。"""

from __future__ import annotations

import secrets
from datetime import datetime

from app.repositories.mysql.records import CustomerRecord
from app.repositories.mysql_repository import MySQLRepository
from app.schemas.customer import CustomerListQuery
from app.services.auth_service import hash_password


def _parse_date(value: str | None, end_of_day: bool = False) -> datetime | None:
    """把 YYYY-MM-DD（或带时间）日期字符串解析为 datetime；为空或非法返回 None。

    Args:
        value: 待解析的日期字符串。
        end_of_day: 仅日期粒度时是否补到当天 23:59:59（用于时间上界）。
    """
    if not value or not value.strip():
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m-%d" and end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59)
        return parsed
    return None


class CustomerService:
    """后台客户管理业务服务，负责客户的分页筛选与增删改启停。"""

    def __init__(self, repository: MySQLRepository) -> None:
        """初始化后台客户管理服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
        """
        self.repository = repository

    def list_customers(self, query: CustomerListQuery) -> tuple[list[CustomerRecord], int]:
        """按筛选条件分页查询客户，返回当前页记录与匹配总数。

        Args:
            query: 后台客户列表查询参数。
        """
        username = query.username.strip() if query.username else None
        last_login_ip = query.lastLoginIp.strip() if query.lastLoginIp else None
        registered_from = _parse_date(query.registeredFrom)
        registered_to = _parse_date(query.registeredTo, end_of_day=True)
        page = max(query.current, 1)
        page_size = min(max(query.pageSize, 1), 100)
        items = self.repository.list_customers(
            page, page_size, username, query.status, registered_from, registered_to, last_login_ip
        )
        total = self.repository.count_customers(
            username, query.status, registered_from, registered_to, last_login_ip
        )
        return items, total

    def get_customer(self, customer_id: int) -> CustomerRecord | None:
        """按 ID 查询单个未删除客户。

        Args:
            customer_id: 客户 ID。
        """
        return self.repository.get_customer_by_id(customer_id)

    def create_customer(
        self,
        username: str,
        password: str,
        nickname: str | None,
        avatar: str | None,
        status: int,
    ) -> CustomerRecord:
        """后台新建客户，先校验账号唯一性再加盐哈希。

        Args:
            username: 登录账号，全局唯一。
            password: 初始明文密码。
            nickname: 客户昵称，可空。
            avatar: 客户头像 URL，可空。
            status: 客户状态，1=正常，0=禁用。
        """
        username = username.strip()
        if self.repository.get_customer_by_username(username):
            raise ValueError("该账号已被注册")
        salt = secrets.token_hex(16)
        return self.repository.create_registered_customer(
            customer_no=f"CUST-{secrets.token_hex(8)}",
            username=username,
            password_hash=hash_password(password, salt),
            salt=salt,
            nickname=nickname.strip() if nickname else None,
            source="admin",
            avatar=avatar.strip() if avatar else None,
            status=status,
        )

    def update_customer(
        self,
        customer_id: int,
        nickname: str | None,
        avatar: str | None,
        status: int | None,
        password: str | None,
    ) -> CustomerRecord | None:
        """后台更新客户信息，密码非空时重置密码。

        Args:
            customer_id: 客户 ID。
            nickname: 新昵称；None 表示不修改。
            avatar: 新头像 URL；None 表示不修改。
            status: 新状态；None 表示不修改。
            password: 新密码；None 表示不修改。
        """
        password_hash: str | None = None
        salt: str | None = None
        if password:
            salt = secrets.token_hex(16)
            password_hash = hash_password(password, salt)
        return self.repository.update_customer(
            customer_id,
            nickname.strip() if nickname else None,
            avatar.strip() if avatar else None,
            status,
            password_hash,
            salt,
        )

    def set_status(self, customer_id: int, status: int) -> CustomerRecord | None:
        """启用/禁用客户。

        Args:
            customer_id: 客户 ID。
            status: 目标状态，1=启用，0=禁用。
        """
        return self.repository.update_customer(customer_id, status=status)

    def delete_customer(self, customer_id: int) -> CustomerRecord | None:
        """软删除客户。

        Args:
            customer_id: 客户 ID。
        """
        return self.repository.soft_delete_customer(customer_id)
