"""订单查询工具的单元测试。"""

from datetime import datetime
from decimal import Decimal

from app.repositories.mysql.records import OrderRecord
from app.tools.order_tool import OrderQueryTool


class FakeOrderRepository:
    """只实现 list_user_orders 的假仓储，记录调用参数便于断言。"""

    def __init__(self, orders: list[OrderRecord]) -> None:
        self._orders = orders
        self.last_call: dict | None = None

    def list_user_orders(self, customer_id: int, order_no: str | None = None, limit: int = 5) -> list[OrderRecord]:
        self.last_call = {"customer_id": customer_id, "order_no": order_no, "limit": limit}
        if order_no:
            return [order for order in self._orders if order.order_no == order_no]
        return self._orders[:limit]


def _order(order_no: str = "OD20260528001") -> OrderRecord:
    now = datetime(2026, 5, 28, 10, 0, 0)
    return OrderRecord(
        id=1,
        customer_id=42,
        order_no=order_no,
        product_name="无线耳机",
        product_quantity=1,
        order_amount=Decimal("199.00"),
        currency="CNY",
        order_status="shipped",
        paid_at=now,
        shipped_at=now,
        remark=None,
        created_at=now,
        updated_at=now,
    )


def _tool(orders: list[OrderRecord]) -> OrderQueryTool:
    return OrderQueryTool(FakeOrderRepository(orders))  # type: ignore[arg-type]


def test_can_handle_strong_keyword() -> None:
    assert _tool([]).can_handle("我的订单到哪了") is True


def test_can_handle_order_number_pattern() -> None:
    assert _tool([]).can_handle("帮我查 OD20260528001") is True


def test_can_handle_excludes_password_intent() -> None:
    assert _tool([]).can_handle("我的支付密码忘了怎么办") is False


def test_can_handle_irrelevant_question() -> None:
    assert _tool([]).can_handle("你们几点上班") is False


def test_call_formats_hit_order() -> None:
    tool = _tool([_order()])
    execution = tool.call(customer_id=42, arguments={"order_no": "OD20260528001"})
    assert execution.name == "query_user_orders"
    assert "OD20260528001" in execution.content
    assert "已发货" in execution.content  # 状态编码被翻译成中文
    assert "¥199.00 CNY" in execution.content


def test_call_empty_result_message() -> None:
    tool = _tool([])
    execution = tool.call(customer_id=42, arguments={"order_no": "OD20260528999"})
    assert "未查询到" in execution.content


def test_call_enforces_user_isolation_and_limit() -> None:
    repo = FakeOrderRepository([_order()])
    tool = OrderQueryTool(repo)  # type: ignore[arg-type]
    tool.call(customer_id=7, arguments={"limit": 99})
    assert repo.last_call is not None
    assert repo.last_call["customer_id"] == 7
    # limit 被规范化到工具默认上限 5 以内。
    assert repo.last_call["limit"] <= 5
