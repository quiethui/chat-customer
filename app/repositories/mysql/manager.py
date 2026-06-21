"""管理员管理 ORM 数据访问方法（管理员后台操作）。"""

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import Manager
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_manager
from app.repositories.mysql.records import ManagerRecord


def _utc_now() -> datetime:
    """返回去掉时区信息的 UTC 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ManagerManageMixin(BaseMySQLMixin):
    """封装管理员管理相关 MySQL 操作。"""

    def list_managers(self, page: int = 1, page_size: int = 25) -> tuple[list[ManagerRecord], int]:
        """分页查询未删除管理员，按创建时间倒序，同时返回总数。

        Args:
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
        """
        base = Manager.deleted_at.is_(None)
        total: int = self._execute(select(func.count()).select_from(Manager).where(base)).scalar_one()
        offset = max(page - 1, 0) * page_size
        rows = self._scalars(
            select(Manager)
            .where(base)
            .order_by(Manager.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_manager(row) for row in rows], total

    def create_managed_manager(
        self,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None,
        is_admin: int,
    ) -> ManagerRecord:
        """管理员后台创建管理员。

        Args:
            username: 管理员登录名。
            password_hash: 加盐后生成的密码哈希值。
            salt: 密码哈希使用的随机盐值。
            nickname: 管理员昵称，空值时使用 username。
            is_admin: 是否管理员，1 表示管理员。
        """
        manager = Manager(
            username=username,
            password_hash=password_hash,
            salt=salt,
            nickname=nickname or username,
            is_admin=is_admin,
        )
        self._add(manager)
        self._flush()
        self._refresh(manager)
        return map_manager(manager)

    def update_manager(
        self,
        manager_id: int,
        nickname: str | None = None,
        is_admin: int | None = None,
        password_hash: str | None = None,
        salt: str | None = None,
        avatar: str | None = None,
    ) -> ManagerRecord | None:
        """更新管理员信息，仅更新传入的非空字段。

        Args:
            manager_id: 管理员自增主键。
            nickname: 新昵称；None 表示不更新。
            is_admin: 新管理员标记；None 表示不更新。
            password_hash: 新密码哈希；None 表示不修改密码。
            salt: 新密码盐值；需与 password_hash 同时传入。
            avatar: 新头像 URL；None 表示不更新，空字符串表示清空。
        """
        manager = self._scalar_one_or_none(
            select(Manager).where(Manager.id == manager_id, Manager.deleted_at.is_(None)).limit(1)
        )
        if not manager:
            return None
        if nickname is not None:
            manager.nickname = nickname
        if is_admin is not None:
            manager.is_admin = is_admin
        if avatar is not None:
            manager.avatar = avatar or None
        if password_hash is not None and salt is not None:
            manager.password_hash = password_hash
            manager.salt = salt
        self._flush()
        self._refresh(manager)
        return map_manager(manager)

    def set_manager_status(self, manager_id: int, manager_status: int) -> ManagerRecord | None:
        """设置管理员启用/禁用状态。

        Args:
            manager_id: 管理员自增主键。
            manager_status: 目标状态，1=启用，0=禁用。
        """
        manager = self._scalar_one_or_none(
            select(Manager).where(Manager.id == manager_id, Manager.deleted_at.is_(None)).limit(1)
        )
        if not manager:
            return None
        manager.status = manager_status
        self._flush()
        self._refresh(manager)
        return map_manager(manager)

    def soft_delete_manager(self, manager_id: int) -> ManagerRecord | None:
        """软删除管理员（写入 deleted_at）。

        Args:
            manager_id: 管理员自增主键。
        """
        manager = self._scalar_one_or_none(
            select(Manager).where(Manager.id == manager_id, Manager.deleted_at.is_(None)).limit(1)
        )
        if not manager:
            return None
        manager.deleted_at = _utc_now()
        self._flush()
        self._refresh(manager)
        return map_manager(manager)
