"""商品查询 Tool Calling 工具。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.repositories.mysql.records import ProductRecord
from app.repositories.mysql_repository import MySQLRepository
from app.tools.registry import ToolExecution


PRODUCT_STRONG_INTENT_KEYWORDS = (
    "价格", "多少钱", "售价", "报价", "什么价", "库存", "现货", "有货", "缺货", "断货",
    "规格", "参数", "型号", "上架", "下架", "在售", "卖多少",
)
"""可直接判定为商品查询意图的关键词。"""

PRODUCT_WEAK_INTENT_KEYWORDS = ("商品", "产品", "这款", "那款", "哪款", "推荐", "买", "卖")
"""需要和价格、库存等语义同时出现才触发商品查询的弱关键词。"""

PRODUCT_WEAK_TRIGGER_KEYWORDS = ("价", "钱", "库存", "型号", "规格", "参数", "推荐", "有货", "现货")
"""配合弱关键词触发商品查询的辅助词。"""

PRODUCT_SKU_PATTERN = re.compile(r"[A-Za-z]{2,}[A-Za-z0-9-]*-[A-Za-z0-9-]+")  # 示例 SKU：HEADSET-NC-002。

PRODUCT_STATUS_TEXT = {
    "on_sale": "在售",
    "off_shelf": "已下架",
    "sold_out": "已售罄",
}
"""商品状态编码到中文展示文案的映射。"""


class ProductQueryTool:
    """查询全局商品目录的聊天工具。

    商品目录对所有用户可见，不做用户隔离；支持按名称/类目关键词或 SKU 查询，
    返回商品价格、库存、状态等信息，供客服回答商品咨询。
    """

    name = "query_products"
    schema: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": name,
            "description": (
                "查询商城商品目录信息。用户询问商品价格、库存、是否有货、规格参数、"
                "型号或需要商品推荐时使用；可按商品名称/类目关键词或商品 SKU 查询，禁止编造商品。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "商品名称或类目关键词，例如 耳机、数码配件；没有则省略。",
                    },
                    "product_sku": {
                        "type": "string",
                        "description": "商品 SKU 编码，例如 HEADSET-NC-002；没有则省略或传空字符串。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回商品数量，默认 5，范围 1 到 5。",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, mysql_repository: MySQLRepository, limit: int = 5) -> None:
        """初始化商品工具。

        Args:
            mysql_repository: MySQL 数据仓储，用于执行商品查询。
            limit: 未指定数量时最多返回的商品数量。
        """
        self.mysql_repository = mysql_repository
        self.limit = limit

    def can_handle(self, question: str) -> bool:
        """判断用户问题是否属于商品查询。

        Args:
            question: 用户本轮问题。

        Returns:
            命中商品查询关键词时返回 True，否则返回 False。
        """
        normalized_question = question.strip()
        if not normalized_question:
            return False
        if any(keyword in normalized_question for keyword in PRODUCT_STRONG_INTENT_KEYWORDS):
            return True
        has_weak_intent = any(keyword in normalized_question for keyword in PRODUCT_WEAK_INTENT_KEYWORDS)
        has_trigger = any(keyword in normalized_question for keyword in PRODUCT_WEAK_TRIGGER_KEYWORDS)
        return has_weak_intent and has_trigger

    def call(self, user_id: int, arguments: dict[str, Any]) -> ToolExecution:
        """按关键词或 SKU 查询商品并格式化为大模型可读文本。

        Args:
            user_id: 当前登录用户 ID；商品目录为全局数据，此参数仅用于接口一致。
            arguments: 模型通过 Function Calling 生成的结构化查询参数。

        Returns:
            ToolExecution，content 中包含商品查询结果或未命中提示。
        """
        _ = user_id
        keyword = self._normalize_text(arguments.get("keyword"))
        product_sku = self._normalize_sku(arguments.get("product_sku"))
        limit = self._normalize_limit(arguments.get("limit"))
        products = self.mysql_repository.list_products(keyword=keyword, product_sku=product_sku, limit=limit)
        if not products:
            content = self._build_empty_result(keyword, product_sku)
        else:
            content = self._build_product_result(products)
        return ToolExecution(name=self.name, content=content)

    def call_from_question(self, user_id: int, question: str) -> ToolExecution:
        """从问题文本中提取关键词并查询商品，用于本地 fallback。

        Args:
            user_id: 当前登录用户 ID；商品目录为全局数据，此参数仅用于接口一致。
            question: 用户本轮问题，用于提取查询关键词或 SKU。

        Returns:
            ToolExecution，content 中包含商品查询结果或未命中提示。
        """
        sku = self._extract_sku(question)
        return self.call(user_id, {"keyword": None if sku else question.strip(), "product_sku": sku, "limit": self.limit})

    def _extract_sku(self, question: str) -> str | None:
        """从用户问题中提取商品 SKU。

        Args:
            question: 用户本轮问题。

        Returns:
            识别到的 SKU；未识别到时返回 None。
        """
        match = PRODUCT_SKU_PATTERN.search(question)
        return match.group(0).upper() if match else None

    def _normalize_text(self, value: object) -> str | None:
        """规范化模型传入的文本参数。

        Args:
            value: 模型生成的关键词参数，可能为空或非字符串。

        Returns:
            去空白后的文本；为空时返回 None。
        """
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _normalize_sku(self, value: object) -> str | None:
        """规范化模型传入的 SKU 参数。

        Args:
            value: 模型生成的 SKU 参数，可能为空或非字符串。

        Returns:
            规范化为大写后的 SKU；为空时返回 None。
        """
        text = self._normalize_text(value)
        return text.upper() if text else None

    def _normalize_limit(self, value: object) -> int:
        """规范化模型传入的数量参数。

        Args:
            value: 模型生成的 limit 参数。

        Returns:
            限制在 1 到默认 limit 之间的整数。
        """
        try:
            limit = int(value) if value is not None else self.limit
        except (TypeError, ValueError):
            limit = self.limit
        return min(max(limit, 1), self.limit)

    def _build_empty_result(self, keyword: str | None, product_sku: str | None) -> str:
        """构建商品未命中的工具结果文本。

        Args:
            keyword: 查询关键词，可能为空。
            product_sku: 查询 SKU，可能为空。

        Returns:
            可直接放入 Prompt 的中文结果说明。
        """
        if product_sku:
            return f"商品查询结果：未查询到 SKU 为 {product_sku} 的商品。"
        if keyword:
            return f"商品查询结果：未查询到与“{keyword}”相关的商品。"
        return "商品查询结果：暂无可展示的商品。"

    def _build_product_result(self, products: list[ProductRecord]) -> str:
        """构建商品命中的工具结果文本。

        Args:
            products: 查询到的商品列表。

        Returns:
            包含名称、SKU、价格、库存和状态的中文结果文本。
        """
        lines = [f"商品查询结果：已查询到 {len(products)} 个商品。"]
        for index, product in enumerate(products, start=1):
            lines.append(
                "\n".join(
                    [
                        f"{index}. 商品名称：{product.name}",
                        f"   商品SKU：{product.product_sku}",
                        f"   商品类目：{product.category or '未分类'}",
                        f"   商品售价：{self._format_amount(product.price, product.currency)}",
                        f"   库存情况：{self._format_stock(product.stock, product.status)}",
                        f"   商品状态：{PRODUCT_STATUS_TEXT.get(product.status, product.status)}",
                        f"   商品简介：{product.description or '无'}",
                    ]
                )
            )
        return "\n".join(lines)

    def _format_stock(self, stock: int, status: str) -> str:
        """格式化库存展示文案。

        Args:
            stock: 商品库存数量。
            status: 商品状态编码。

        Returns:
            人类可读的库存文案。
        """
        if status == "sold_out" or stock <= 0:
            return "无货"
        return f"有货（库存 {stock} 件）"

    def _format_amount(self, amount: Decimal, currency: str) -> str:
        """格式化商品金额。

        Args:
            amount: 商品售价。
            currency: 币种编码。

        Returns:
            人类可读的金额文本，例如 `¥199.00 CNY`。
        """
        prefix = "¥" if currency == "CNY" else ""
        return f"{prefix}{amount:.2f} {currency}"
