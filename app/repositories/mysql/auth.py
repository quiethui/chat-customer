"""用户认证 ORM 数据访问方法。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import User, UserSession
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_auth_session, map_user
from app.repositories.mysql.records import AuthSessionRecord, UserRecord


class AuthMySQLMixin(BaseMySQLMixin):
    """封装用户和登录会话相关 MySQL 操作。"""

    def get_user_by_username(self, username: str) -> UserRecord | None:
        """按用户名查询用户。

        Args:
            username: 登录用户名。
        """
        user = self._scalar_one_or_none(
            select(User).where(User.username == username).limit(1)
        )
        return map_user(user) if user else None

    def get_user_by_id(self, user_id: int) -> UserRecord | None:
        """按用户 ID 查询用户。

        Args:
            user_id: 用户自增主键。
        """
        user = self._scalar_one_or_none(select(User).where(User.id == user_id).limit(1))
        return map_user(user) if user else None

    def create_user(
        self,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None = None,
    ) -> UserRecord:
        """创建用户并返回用户记录。

        Args:
            username: 登录用户名。
            password_hash: 加盐后生成的密码哈希值。
            salt: 密码哈希使用的随机盐值。
            nickname: 用户昵称，空值时使用 username。
        """
        user = User(username=username, password_hash=password_hash, salt=salt, nickname=nickname or username)
        self._add(user)
        self._flush()
        self._refresh(user)
        return map_user(user)

    def create_auth_session(self, user_id: int, token: str, ttl_minutes: int) -> AuthSessionRecord:
        """创建用户登录会话。

        Args:
            user_id: 会话所属用户 ID。
            token: 登录凭证 Token。
            ttl_minutes: Token 有效期，单位分钟。
        """
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=ttl_minutes)
        auth_session = UserSession(user_id=user_id, token=token, expires_at=expires_at)
        self._add(auth_session)
        self._flush()
        self._refresh(auth_session)
        return map_auth_session(auth_session)

    def get_auth_session(self, token: str) -> AuthSessionRecord | None:
        """查询未撤销且未过期的登录会话。

        Args:
            token: 登录凭证 Token。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        auth_session = self._scalar_one_or_none(
            select(UserSession)
            .where(UserSession.token == token, UserSession.revoked_at.is_(None), UserSession.expires_at > now)
            .limit(1)
        )
        return map_auth_session(auth_session) if auth_session else None

    def revoke_auth_session(self, token: str) -> None:
        """撤销登录会话。

        Args:
            token: 登录凭证 Token。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._execute(
            update(UserSession)
            .where(UserSession.token == token, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
