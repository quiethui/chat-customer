"""订单 ORM 数据访问方法。"""

from sqlalchemy import select

from app.models import UserOrder
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_order
from app.repositories.mysql.records import OrderRecord


class OrderMySQLMixin(BaseMySQLMixin):
    """封装订单相关 MySQL 查询操作。"""

    def list_user_orders(self, user_id: int, order_no: str | None = None, limit: int = 5) -> list[OrderRecord]:
        """查询当前用户的订单列表。

        Args:
            user_id: 当前用户 ID，用于数据隔离。
            order_no: 可选订单号；为空时查询最近订单。
            limit: 最大返回数量，会被限制在 1 到 20 之间。
        """
        safe_limit = min(max(limit, 1), 20)
        conditions = [UserOrder.user_id == user_id, UserOrder.deleted_at.is_(None)]
        if order_no:
            conditions.append(UserOrder.order_no == order_no)
        rows = self._scalars(
            select(UserOrder)
            .where(*conditions)
            .order_by(UserOrder.created_at.desc())
            .limit(safe_limit)
        )
        return [map_order(row) for row in rows]
