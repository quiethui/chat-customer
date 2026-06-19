"""商品查询工具的单元测试。"""

from datetime import datetime
from decimal import Decimal

from app.repositories.mysql.records import ProductRecord
from app.tools.product_tool import ProductQueryTool


class FakeProductRepository:
    """只实现 list_products 的假仓储，记录调用参数便于断言。"""

    def __init__(self, products: list[ProductRecord]) -> None:
        self._products = products
        self.last_call: dict | None = None

    def list_products(
        self,
        keyword: str | None = None,
        product_sku: str | None = None,
        limit: int = 5,
    ) -> list[ProductRecord]:
        self.last_call = {"keyword": keyword, "product_sku": product_sku, "limit": limit}
        if product_sku:
            return [p for p in self._products if p.product_sku == product_sku]
        if keyword:
            return [p for p in self._products if keyword in p.name or (p.category and keyword in p.category)]
        return self._products[:limit]


def _product(
    sku: str = "HEADSET-NC-002",
    name: str = "无线降噪耳机",
    stock: int = 56,
    status: str = "on_sale",
) -> ProductRecord:
    now = datetime(2026, 5, 1, 10, 0, 0)
    return ProductRecord(
        id=1,
        product_sku=sku,
        name=name,
        category="数码配件",
        price=Decimal("599.00"),
        currency="CNY",
        stock=stock,
        status=status,
        description="主动降噪，蓝牙 5.3。",
        created_at=now,
        updated_at=now,
    )


def _tool(products: list[ProductRecord]) -> ProductQueryTool:
    return ProductQueryTool(FakeProductRepository(products))  # type: ignore[arg-type]


def test_can_handle_strong_keyword() -> None:
    assert _tool([]).can_handle("这个耳机多少钱") is True


def test_can_handle_weak_keyword_with_trigger() -> None:
    assert _tool([]).can_handle("有没有推荐的商品") is True


def test_can_handle_irrelevant_question() -> None:
    assert _tool([]).can_handle("你们几点上班") is False


def test_can_handle_pure_order_question_is_false() -> None:
    # 纯订单问题不应被商品工具拦截（关键词不重合）。
    assert _tool([]).can_handle("我的订单到哪了") is False


def test_call_formats_hit_product() -> None:
    tool = _tool([_product()])
    execution = tool.call(user_id=1, arguments={"keyword": "耳机"})
    assert execution.name == "query_products"
    assert "无线降噪耳机" in execution.content
    assert "HEADSET-NC-002" in execution.content
    assert "¥599.00 CNY" in execution.content
    assert "有货（库存 56 件）" in execution.content


def test_call_sold_out_shows_no_stock() -> None:
    tool = _tool([_product(stock=0, status="sold_out")])
    execution = tool.call(user_id=1, arguments={"product_sku": "HEADSET-NC-002"})
    assert "无货" in execution.content
    assert "已售罄" in execution.content


def test_call_empty_result_by_sku() -> None:
    tool = _tool([])
    execution = tool.call(user_id=1, arguments={"product_sku": "NOT-EXIST-001"})
    assert "未查询到 SKU 为 NOT-EXIST-001" in execution.content


def test_call_normalizes_sku_and_limit() -> None:
    repo = FakeProductRepository([_product()])
    tool = ProductQueryTool(repo)  # type: ignore[arg-type]
    tool.call(user_id=1, arguments={"product_sku": "headset-nc-002", "limit": 99})
    assert repo.last_call is not None
    assert repo.last_call["product_sku"] == "HEADSET-NC-002"  # 大写归一化
    assert repo.last_call["limit"] <= 5  # 数量上限收敛


def test_call_from_question_extracts_sku() -> None:
    repo = FakeProductRepository([_product()])
    tool = ProductQueryTool(repo)  # type: ignore[arg-type]
    tool.call_from_question(user_id=1, question="帮我查 HEADSET-NC-002 还有货吗")
    assert repo.last_call is not None
    assert repo.last_call["product_sku"] == "HEADSET-NC-002"
