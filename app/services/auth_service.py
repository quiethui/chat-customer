"""用户认证服务。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from app.repositories.mysql_records import UserRecord
from app.repositories.mysql_repository import MySQLRepository


@dataclass(frozen=True)
class LoginResult:
    """登录成功后的服务层结果。"""

    token: str  # 新创建的登录 token，前端后续请求会放到 Authorization 头。
    user: UserRecord  # 登录成功的用户记录。


class AuthService:
    """用户注册、登录、token 校验和退出登录的业务服务。"""

    def __init__(self, repository: MySQLRepository, session_ttl_minutes: int) -> None:
        """初始化认证服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
            session_ttl_minutes: 登录会话有效期，单位分钟。
        """
        self.repository = repository
        self.session_ttl_minutes = session_ttl_minutes

    def login(self, username: str, password: str) -> LoginResult:
        """校验用户名密码，成功后写入登录会话并返回 token。

        Args:
            username: 登录用户名。
            password: 用户明文密码。
        """
        user = self.repository.get_user_by_username(username.strip())
        if not user or user.status != 1 or not _verify_password(password, user.salt, user.password_hash):
            raise ValueError("用户名或密码错误")
        token = secrets.token_urlsafe(32)
        self.repository.create_auth_session(user.id, token, self.session_ttl_minutes)
        return LoginResult(token=token, user=user)

    def register(self, username: str, password: str, confirm_password: str | None = None) -> UserRecord:
        """创建新用户，保存前会校验确认密码和用户名唯一性。

        Args:
            username: 登录用户名。
            password: 用户明文密码。
            confirm_password: 注册时的确认密码。
        """
        username = username.strip()
        if confirm_password is not None and password != confirm_password:
            raise ValueError("两次输入的密码不一致")
        if self.repository.get_user_by_username(username):
            raise ValueError("用户名已存在")
        salt = secrets.token_hex(16)
        return self.repository.create_user(username, hash_password(password, salt), salt, username)

    def authenticate_token(self, token: str) -> UserRecord | None:
        """根据 token 查询当前有效登录用户。

        Args:
            token: 认证访问令牌。
        """
        session = self.repository.get_auth_session(token)
        if not session:
            return None
        user = self.repository.get_user_by_id(session.user_id)
        if not user or user.status != 1:
            return None
        return user

    def logout(self, token: str) -> None:
        """退出登录，将 token 对应会话撤销。

        Args:
            token: 认证访问令牌。
        """
        self.repository.revoke_auth_session(token)


def hash_password(password: str, salt: str) -> str:
    """使用 PBKDF2 对密码加盐哈希，数据库只保存哈希值。

    Args:
        password: 用户明文密码。
        salt: 密码哈希使用的随机盐值。
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    """用常量时间比较验证用户输入密码是否正确。

    Args:
        password: 用户明文密码。
        salt: 密码哈希使用的随机盐值。
        password_hash: 加盐后生成的密码哈希值。
    """
    return hmac.compare_digest(hash_password(password, salt), password_hash)
