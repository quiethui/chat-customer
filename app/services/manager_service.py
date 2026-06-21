"""管理员管理服务。"""

from __future__ import annotations

import secrets

from app.repositories.mysql.records import ManagerRecord
from app.repositories.mysql_repository import MySQLRepository
from app.services.auth_service import hash_password


class ManagerService:
    """管理员管理业务服务，负责管理员的增删改查与启停。"""

    def __init__(self, repository: MySQLRepository) -> None:
        """初始化管理员管理服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
        """
        self.repository = repository

    def list_managers(self, page: int = 1, page_size: int = 25) -> tuple[list[ManagerRecord], int]:
        """分页查询未删除管理员，返回列表和总数。

        Args:
            page: 分页页码。
            page_size: 每页返回的记录数量。
        """
        return self.repository.list_managers(max(page, 1), min(max(page_size, 1), 100))

    def create_manager(self, username: str, password: str, nickname: str | None, is_admin: bool) -> ManagerRecord:
        """创建管理员，先校验用户名唯一性再加盐哈希。

        Args:
            username: 管理员登录名。
            password: 初始明文密码。
            nickname: 管理员昵称。
            is_admin: 是否管理员。
        """
        username = username.strip()
        if self.repository.get_manager_by_username(username):
            raise ValueError("用户名已存在")
        salt = secrets.token_hex(16)
        return self.repository.create_managed_manager(
            username,
            hash_password(password, salt),
            salt,
            nickname.strip() if nickname else None,
            1 if is_admin else 0,
        )

    def update_manager(
        self,
        manager_id: int,
        nickname: str | None,
        is_admin: bool | None,
        password: str | None,
    ) -> ManagerRecord | None:
        """更新管理员信息，密码非空时重置密码。

        Args:
            manager_id: 管理员 ID。
            nickname: 新昵称；None 表示不修改。
            is_admin: 新管理员标记；None 表示不修改。
            password: 新密码；None 表示不修改。
        """
        password_hash: str | None = None
        salt: str | None = None
        if password:
            salt = secrets.token_hex(16)
            password_hash = hash_password(password, salt)
        return self.repository.update_manager(
            manager_id,
            nickname.strip() if nickname else None,
            None if is_admin is None else (1 if is_admin else 0),
            password_hash,
            salt,
        )

    def set_status(self, manager_id: int, manager_status: int) -> ManagerRecord | None:
        """设置管理员启用/禁用状态。

        Args:
            manager_id: 管理员 ID。
            manager_status: 目标状态，1=启用，0=禁用。
        """
        return self.repository.set_manager_status(manager_id, manager_status)

    def delete_manager(self, manager_id: int) -> ManagerRecord | None:
        """软删除管理员。

        Args:
            manager_id: 管理员 ID。
        """
        return self.repository.soft_delete_manager(manager_id)
