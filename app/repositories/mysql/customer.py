"""客户认证 ORM 数据访问方法（对外 AI 客服服务对象，含匿名访客）。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.models import Customer, CustomerSession
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_customer, map_customer_session
from app.repositories.mysql.records import CustomerRecord, CustomerSessionRecord


def _utc_now() -> datetime:
    """返回去掉时区信息的 UTC 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CustomerMySQLMixin(BaseMySQLMixin):
    """封装客户和客户登录会话相关 MySQL 操作。"""

    def get_customer_by_id(self, customer_id: int) -> CustomerRecord | None:
        """按客户 ID 查询未删除客户。

        Args:
            customer_id: 客户自增主键。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)).limit(1)
        )
        return map_customer(customer) if customer else None

    def get_customer_by_no(self, customer_no: str) -> CustomerRecord | None:
        """按客户编号查询未删除客户。

        Args:
            customer_no: 客户编号，全局唯一。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.customer_no == customer_no, Customer.deleted_at.is_(None)).limit(1)
        )
        return map_customer(customer) if customer else None

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
        """创建客户（默认匿名访客）并返回客户记录。

        Args:
            customer_no: 客户编号，全局唯一。
            nickname: 客户昵称，空值时由前端展示默认值。
            source: 客户来源渠道，例如 web、widget。
            is_anonymous: 是否匿名访客，1 表示匿名访客，0 表示已注册客户。
            phone: 客户手机号，可空。
            email: 客户邮箱，可空。
            password_hash: 加盐后生成的密码哈希值；匿名访客为空。
            salt: 密码哈希使用的随机盐值；匿名访客为空。
        """
        customer = Customer(
            customer_no=customer_no,
            nickname=nickname,
            source=source,
            is_anonymous=is_anonymous,
            phone=phone,
            email=email,
            password_hash=password_hash,
            salt=salt,
        )
        self._add(customer)
        self._flush()
        self._refresh(customer)
        return map_customer(customer)

    def create_customer_session(self, customer_id: int, token: str, ttl_minutes: int) -> CustomerSessionRecord:
        """创建客户登录会话。

        Args:
            customer_id: 会话所属客户 ID。
            token: 客户端登录凭证 Token。
            ttl_minutes: Token 有效期，单位分钟。
        """
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=ttl_minutes)
        customer_session = CustomerSession(customer_id=customer_id, token=token, expires_at=expires_at)
        self._add(customer_session)
        self._flush()
        self._refresh(customer_session)
        return map_customer_session(customer_session)

    def get_customer_session(self, token: str) -> CustomerSessionRecord | None:
        """查询未撤销且未过期的客户登录会话。

        Args:
            token: 客户端登录凭证 Token。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        customer_session = self._scalar_one_or_none(
            select(CustomerSession)
            .where(
                CustomerSession.token == token,
                CustomerSession.revoked_at.is_(None),
                CustomerSession.expires_at > now,
            )
            .limit(1)
        )
        return map_customer_session(customer_session) if customer_session else None

    def revoke_customer_session(self, token: str) -> None:
        """撤销客户登录会话（登出，写 revoked_at）。

        Args:
            token: 客户端登录凭证 Token。
        """
        self._execute(
            update(CustomerSession)
            .where(CustomerSession.token == token, CustomerSession.revoked_at.is_(None))
            .values(revoked_at=_utc_now())
        )

    def get_customer_by_username(self, username: str) -> CustomerRecord | None:
        """按登录账号查询未删除客户。

        Args:
            username: 客户登录账号，全局唯一。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.username == username, Customer.deleted_at.is_(None)).limit(1)
        )
        return map_customer(customer) if customer else None

    def update_customer_credentials(
        self,
        customer_id: int,
        username: str,
        password_hash: str,
        salt: str,
        nickname: str | None = None,
    ) -> CustomerRecord | None:
        """匿名访客就地升级为注册客户：写账号/密码/昵称并置 is_anonymous=0。

        Args:
            customer_id: 待升级的客户自增主键（保持不变，历史会话零迁移）。
            username: 登录账号，全局唯一。
            password_hash: 加盐后生成的密码哈希值。
            salt: 密码哈希使用的随机盐值。
            nickname: 客户昵称；为空时不更新原昵称。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)).limit(1)
        )
        if not customer:
            return None
        customer.username = username
        customer.password_hash = password_hash
        customer.salt = salt
        if nickname is not None:
            customer.nickname = nickname
        customer.is_anonymous = 0
        self._flush()
        self._refresh(customer)
        return map_customer(customer)

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
        """直接创建已注册客户（非匿名），用于无匿名身份时的注册与后台新建。

        Args:
            customer_no: 客户编号，全局唯一。
            username: 登录账号，全局唯一。
            password_hash: 加盐后生成的密码哈希值。
            salt: 密码哈希使用的随机盐值。
            nickname: 客户昵称，可空。
            source: 客户来源渠道，例如 web、widget、admin。
            avatar: 客户头像 URL，可空。
            status: 客户状态，1=正常，0=禁用。
        """
        customer = Customer(
            customer_no=customer_no,
            username=username,
            password_hash=password_hash,
            salt=salt,
            nickname=nickname,
            source=source,
            avatar=avatar,
            status=status,
            is_anonymous=0,
        )
        self._add(customer)
        self._flush()
        self._refresh(customer)
        return map_customer(customer)

    def update_last_login(self, customer_id: int, at: datetime, ip: str | None) -> None:
        """记录客户最近一次登录的时间与 IP。

        Args:
            customer_id: 客户自增主键。
            at: 本次登录时间。
            ip: 本次登录的真实 IP，可空。
        """
        self._execute(
            update(Customer).where(Customer.id == customer_id).values(last_login_at=at, last_login_ip=ip)
        )

    # ---- 后台客户管理（管理员操作，按筛选条件检索与增改删） ----

    def _admin_conditions(
        self,
        username: str | None,
        status: int | None,
        registered_from: datetime | None,
        registered_to: datetime | None,
        last_login_ip: str | None,
    ) -> list:
        """构造后台客户列表的筛选条件，供 list/count 复用。

        Args:
            username: 按登录账号模糊匹配；为空不过滤。
            status: 按状态精确匹配；为空不过滤。
            registered_from: 注册时间下界；为空不过滤。
            registered_to: 注册时间上界；为空不过滤。
            last_login_ip: 按登录 IP 模糊匹配；为空不过滤。
        """
        conditions = [Customer.deleted_at.is_(None)]
        if username:
            conditions.append(Customer.username.like(f"%{username}%"))
        if status is not None:
            conditions.append(Customer.status == status)
        if registered_from is not None:
            conditions.append(Customer.created_at >= registered_from)
        if registered_to is not None:
            conditions.append(Customer.created_at <= registered_to)
        if last_login_ip:
            conditions.append(Customer.last_login_ip.like(f"%{last_login_ip}%"))
        return conditions

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
        """分页查询后台客户列表，按创建时间倒序。

        Args:
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
            username: 按登录账号模糊匹配；为空不过滤。
            status: 按状态精确匹配；为空不过滤。
            registered_from: 注册时间下界；为空不过滤。
            registered_to: 注册时间上界；为空不过滤。
            last_login_ip: 按登录 IP 模糊匹配；为空不过滤。
        """
        offset = max(page - 1, 0) * page_size
        rows = self._scalars(
            select(Customer)
            .where(*self._admin_conditions(username, status, registered_from, registered_to, last_login_ip))
            .order_by(Customer.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_customer(row) for row in rows]

    def count_customers(
        self,
        username: str | None = None,
        status: int | None = None,
        registered_from: datetime | None = None,
        registered_to: datetime | None = None,
        last_login_ip: str | None = None,
    ) -> int:
        """统计符合筛选条件的后台客户总数，用于分页。

        Args:
            username: 按登录账号模糊匹配；为空不过滤。
            status: 按状态精确匹配；为空不过滤。
            registered_from: 注册时间下界；为空不过滤。
            registered_to: 注册时间上界；为空不过滤。
            last_login_ip: 按登录 IP 模糊匹配；为空不过滤。
        """
        total = self._scalar_one_or_none(
            select(func.count())
            .select_from(Customer)
            .where(*self._admin_conditions(username, status, registered_from, registered_to, last_login_ip))
        )
        return int(total or 0)

    def update_customer(
        self,
        customer_id: int,
        nickname: str | None = None,
        avatar: str | None = None,
        status: int | None = None,
        password_hash: str | None = None,
        salt: str | None = None,
    ) -> CustomerRecord | None:
        """后台更新客户信息，仅更新传入的非空字段。

        Args:
            customer_id: 客户自增主键。
            nickname: 新昵称；None 表示不更新。
            avatar: 新头像 URL；None 表示不更新。
            status: 新状态；None 表示不更新。
            password_hash: 新密码哈希；None 表示不改密。
            salt: 新密码盐值；需与 password_hash 同时传入。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)).limit(1)
        )
        if not customer:
            return None
        if nickname is not None:
            customer.nickname = nickname
        if avatar is not None:
            customer.avatar = avatar
        if status is not None:
            customer.status = status
        if password_hash is not None and salt is not None:
            customer.password_hash = password_hash
            customer.salt = salt
        self._flush()
        self._refresh(customer)
        return map_customer(customer)

    def soft_delete_customer(self, customer_id: int) -> CustomerRecord | None:
        """软删除客户（写入 deleted_at）。

        Args:
            customer_id: 客户自增主键。
        """
        customer = self._scalar_one_or_none(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)).limit(1)
        )
        if not customer:
            return None
        customer.deleted_at = _utc_now()
        self._flush()
        self._refresh(customer)
        return map_customer(customer)
