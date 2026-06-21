"""客户端（对外 AI 客服）认证服务。"""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.mysql.records import CustomerRecord
from app.repositories.mysql_repository import MySQLRepository
from app.services.auth_service import hash_password


@dataclass(frozen=True)
class VisitorResult:
    """领取匿名访客身份后的服务层结果。"""

    token: str  # 新建的客户端登录 token，前端后续请求放入 Authorization 头。
    customer: CustomerRecord  # 新建的匿名访客记录。


@dataclass(frozen=True)
class AuthResult:
    """注册或登录成功后的服务层结果。"""

    token: str  # 客户端登录 token，前端后续请求放入 Authorization 头。
    customer: CustomerRecord  # 注册或登录命中的客户记录。


def _utc_now() -> datetime:
    """返回去掉时区信息的 UTC 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CustomerAuthService:
    """客户身份（匿名访客优先）领取与 token 校验的业务服务。"""

    def __init__(self, repository: MySQLRepository, session_ttl_minutes: int) -> None:
        """初始化客户认证服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
            session_ttl_minutes: 客户端会话 token 有效期，单位分钟。
        """
        self.repository = repository
        self.session_ttl_minutes = session_ttl_minutes

    def create_visitor(self, source: str = "web") -> VisitorResult:
        """创建匿名访客并签发客户端 token。

        Args:
            source: 客户来源渠道，例如 web、widget。
        """
        suffix = secrets.token_hex(8)
        customer_no = f"VISITOR-{suffix}"
        nickname = f"访客{suffix[:4].upper()}"
        customer = self.repository.create_customer(
            customer_no=customer_no,
            nickname=nickname,
            source=source,
            is_anonymous=1,
        )
        token = secrets.token_urlsafe(32)
        self.repository.create_customer_session(customer.id, token, self.session_ttl_minutes)
        return VisitorResult(token=token, customer=customer)

    def authenticate_token(self, token: str) -> CustomerRecord | None:
        """根据 token 查询当前有效的客户。

        Args:
            token: 客户端登录凭证 token。
        """
        session = self.repository.get_customer_session(token)
        if not session:
            return None
        customer = self.repository.get_customer_by_id(session.customer_id)
        if not customer or customer.deleted_at is not None or customer.status != 1:
            return None
        return customer

    def register(
        self,
        username: str,
        password: str,
        nickname: str | None,
        current: CustomerRecord | None,
        current_token: str | None,
    ) -> AuthResult:
        """注册客户：携匿名身份则就地升级该行，否则新建注册客户。

        Args:
            username: 登录账号，全局唯一。
            password: 明文密码，服务层加盐哈希后保存。
            nickname: 客户昵称，可空。
            current: 来访的当前客户（可能为匿名访客或 None）。
            current_token: 来访携带的客户端 token，可空；就地升级时复用。
        """
        username = (username or "").strip()
        if not username or not password:
            raise ValueError("账号和密码不能为空")
        if self.repository.get_customer_by_username(username):
            raise ValueError("该账号已被注册")
        nickname = nickname.strip() if nickname else None
        # 携匿名身份注册：就地升级同一行，customer_id 不变，历史聊天零迁移。
        if current is not None and current.is_anonymous == 1:
            customer = self.upgrade_visitor(current.id, username, password, nickname)
            token = current_token or self._issue_token(customer.id)
            return AuthResult(token=token, customer=customer)
        # 无匿名身份：直接新建注册客户并签发 token。
        salt = secrets.token_hex(16)
        customer = self.repository.create_registered_customer(
            customer_no=f"CUST-{secrets.token_hex(8)}",
            username=username,
            password_hash=hash_password(password, salt),
            salt=salt,
            nickname=nickname,
        )
        return AuthResult(token=self._issue_token(customer.id), customer=customer)

    def upgrade_visitor(
        self,
        customer_id: int,
        username: str,
        password: str,
        nickname: str | None,
    ) -> CustomerRecord:
        """把匿名访客就地升级为注册客户（写账号/密码/昵称、置 is_anonymous=0）。

        Args:
            customer_id: 待升级的匿名访客 ID（保持不变）。
            username: 登录账号，全局唯一。
            password: 明文密码，服务层加盐哈希后保存。
            nickname: 客户昵称，可空。
        """
        salt = secrets.token_hex(16)
        customer = self.repository.update_customer_credentials(
            customer_id, username, hash_password(password, salt), salt, nickname
        )
        if not customer:
            raise ValueError("访客身份已失效，请重新进入后再注册")
        return customer

    def login(
        self,
        username: str,
        password: str,
        current: CustomerRecord | None,
        client_ip: str | None,
    ) -> AuthResult:
        """登录已有账号：校验密码，携匿名身份时合并当前会话，再签发新 token。

        Args:
            username: 登录账号。
            password: 明文密码。
            current: 来访的当前客户（可能为匿名访客或 None）。
            client_ip: 来访真实 IP，记录到 last_login_ip。
        """
        account = self.repository.get_customer_by_username((username or "").strip())
        if (
            not account
            or account.deleted_at is not None
            or account.status != 1
            or not account.password_hash
            or not account.salt
            or not hmac.compare_digest(hash_password(password, account.salt), account.password_hash)
        ):
            raise ValueError("账号或密码错误")
        # 合并：把来访匿名身份名下的会话改挂到登录账号，呈现连续对话。
        # 这些会话均出自匿名身份自己的 token，归属可信，不存在越权。
        if current is not None and current.is_anonymous == 1 and current.id != account.id:
            for session in self.repository.list_customer_sessions(current.id, 100):
                self.repository.reassign_session(session.id, account.id)
        token = self._issue_token(account.id)
        self.repository.update_last_login(account.id, _utc_now(), client_ip)
        return AuthResult(token=token, customer=self.repository.get_customer_by_id(account.id) or account)

    def logout(self, token: str) -> None:
        """登出：撤销当前 token，前端随后回落匿名身份。

        Args:
            token: 客户端登录凭证 token。
        """
        self.repository.revoke_customer_session(token)

    def _issue_token(self, customer_id: int) -> str:
        """为客户签发新的客户端 token 并落库登录会话。

        Args:
            customer_id: 客户自增主键。
        """
        token = secrets.token_urlsafe(32)
        self.repository.create_customer_session(customer_id, token, self.session_ttl_minutes)
        return token
