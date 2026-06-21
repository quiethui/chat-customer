"""管理员认证 ORM 数据访问方法。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import Manager, ManagerSession
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_manager, map_manager_session
from app.repositories.mysql.records import ManagerRecord, ManagerSessionRecord


class AuthMySQLMixin(BaseMySQLMixin):
    """封装管理员认证和登录会话相关 MySQL 操作。"""

    def get_manager_by_username(self, username: str) -> ManagerRecord | None:
        """按用户名查询管理员。

        Args:
            username: 登录用户名。
        """
        manager = self._scalar_one_or_none(
            select(Manager).where(Manager.username == username).limit(1)
        )
        return map_manager(manager) if manager else None

    def get_manager_by_id(self, manager_id: int) -> ManagerRecord | None:
        """按管理员 ID 查询管理员。

        Args:
            manager_id: 管理员自增主键。
        """
        manager = self._scalar_one_or_none(select(Manager).where(Manager.id == manager_id).limit(1))
        return map_manager(manager) if manager else None

    def create_manager(
        self,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None = None,
    ) -> ManagerRecord:
        """创建管理员并返回管理员记录。

        Args:
            username: 登录用户名。
            password_hash: 加盐后生成的密码哈希值。
            salt: 密码哈希使用的随机盐值。
            nickname: 管理员昵称，空值时使用 username。
        """
        manager = Manager(username=username, password_hash=password_hash, salt=salt, nickname=nickname or username)
        self._add(manager)
        self._flush()
        self._refresh(manager)
        return map_manager(manager)

    def create_auth_session(self, manager_id: int, token: str, ttl_minutes: int) -> ManagerSessionRecord:
        """创建管理员登录会话。

        Args:
            manager_id: 会话所属管理员 ID。
            token: 登录凭证 Token。
            ttl_minutes: Token 有效期，单位分钟。
        """
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=ttl_minutes)
        auth_session = ManagerSession(manager_id=manager_id, token=token, expires_at=expires_at)
        self._add(auth_session)
        self._flush()
        self._refresh(auth_session)
        return map_manager_session(auth_session)

    def get_auth_session(self, token: str) -> ManagerSessionRecord | None:
        """查询未撤销且未过期的登录会话。

        Args:
            token: 登录凭证 Token。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        auth_session = self._scalar_one_or_none(
            select(ManagerSession)
            .where(ManagerSession.token == token, ManagerSession.revoked_at.is_(None), ManagerSession.expires_at > now)
            .limit(1)
        )
        return map_manager_session(auth_session) if auth_session else None

    def revoke_auth_session(self, token: str) -> None:
        """撤销登录会话。

        Args:
            token: 登录凭证 Token。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._execute(
            update(ManagerSession)
            .where(ManagerSession.token == token, ManagerSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
