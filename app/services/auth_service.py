"""管理员认证服务。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from app.repositories.mysql.records import ManagerRecord
from app.repositories.mysql_repository import MySQLRepository


@dataclass(frozen=True)
class LoginResult:
    """登录成功后的服务层结果。"""

    token: str  # 新创建的登录 token，前端后续请求会放到 Authorization 头。
    manager: ManagerRecord  # 登录成功的管理员记录。


class AuthService:
    """管理员注册、登录、token 校验和退出登录的业务服务。"""

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
            password: 管理员明文密码。
        """
        manager = self.repository.get_manager_by_username(username.strip())
        if (
            not manager
            or manager.deleted_at is not None
            or manager.status != 1
            or not _verify_password(password, manager.salt, manager.password_hash)
        ):
            raise ValueError("用户名或密码错误")
        token = secrets.token_urlsafe(32)
        self.repository.create_auth_session(manager.id, token, self.session_ttl_minutes)
        return LoginResult(token=token, manager=manager)

    def register(self, username: str, password: str, confirm_password: str | None = None) -> ManagerRecord:
        """创建新管理员，保存前会校验确认密码和用户名唯一性。

        Args:
            username: 登录用户名。
            password: 管理员明文密码。
            confirm_password: 注册时的确认密码。
        """
        username = username.strip()
        if confirm_password is not None and password != confirm_password:
            raise ValueError("两次输入的密码不一致")
        if self.repository.get_manager_by_username(username):
            raise ValueError("用户名已存在")
        salt = secrets.token_hex(16)
        return self.repository.create_manager(username, hash_password(password, salt), salt, username)

    def authenticate_token(self, token: str) -> ManagerRecord | None:
        """根据 token 查询当前有效登录管理员。

        Args:
            token: 认证访问令牌。
        """
        session = self.repository.get_auth_session(token)
        if not session:
            return None
        manager = self.repository.get_manager_by_id(session.manager_id)
        if not manager or manager.deleted_at is not None or manager.status != 1:
            return None
        return manager

    def logout(self, token: str) -> None:
        """退出登录，将 token 对应会话撤销。

        Args:
            token: 认证访问令牌。
        """
        self.repository.revoke_auth_session(token)

    def update_profile(self, manager_id: int, nickname: str | None, avatar: str | None) -> ManagerRecord:
        """自助更新当前管理员的昵称与头像。

        Args:
            manager_id: 当前登录管理员主键 ID。
            nickname: 新昵称；为空（或仅空白）时回退为不修改，避免清空成 NULL。
            avatar: 新头像 URL；None 表示不修改，空字符串表示清空头像。
        """
        nickname_clean = nickname.strip() if nickname and nickname.strip() else None
        record = self.repository.update_manager(manager_id, nickname=nickname_clean, avatar=avatar)
        if not record:
            raise ValueError("账号不存在")
        return record

    def change_password(self, manager_id: int, old_password: str, new_password: str) -> None:
        """校验旧密码后修改当前管理员密码。

        Args:
            manager_id: 当前登录管理员主键 ID。
            old_password: 当前密码，用于校验身份。
            new_password: 新密码，加盐哈希后保存。
        """
        manager = self.repository.get_manager_by_id(manager_id)
        if not manager or manager.deleted_at is not None:
            raise ValueError("账号不存在")
        if not _verify_password(old_password, manager.salt, manager.password_hash):
            raise ValueError("当前密码不正确")
        salt = secrets.token_hex(16)
        self.repository.update_manager(manager_id, password_hash=hash_password(new_password, salt), salt=salt)


def hash_password(password: str, salt: str) -> str:
    """使用 PBKDF2 对密码加盐哈希，数据库只保存哈希值。

    Args:
        password: 管理员明文密码。
        salt: 密码哈希使用的随机盐值。
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    """用常量时间比较验证用户输入密码是否正确。

    Args:
        password: 管理员明文密码。
        salt: 密码哈希使用的随机盐值。
        password_hash: 加盐后生成的密码哈希值。
    """
    return hmac.compare_digest(hash_password(password, salt), password_hash)
