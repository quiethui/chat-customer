"""订单查询 Tool Calling 工具。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.repositories.mysql.records import OrderRecord
from app.repositories.mysql_repository import MySQLRepository
from app.tools.registry import ToolExecution


ORDER_STRONG_INTENT_KEYWORDS = ("订单", "订单号", "物流", "快递", "发货", "收货", "退款", "退货", "售后", "包裹", "运单")
"""可直接判定为订单查询意图的关键词。"""

ORDER_WEAK_INTENT_KEYWORDS = ("付款", "支付", "金额", "商品")
"""需要和订单语义同时出现才触发订单查询的弱关键词。"""

ORDER_EXCLUSION_KEYWORDS = ("支付密码", "付款密码", "忘记密码", "密码忘", "找回密码", "修改密码", "重置密码")
"""支付密码、账号密码等非订单查询场景的排除关键词。"""

ORDER_NO_PATTERN = re.compile(r"[A-Za-z]{2}\d{8,20}")  # 示例订单号格式：字母前缀 + 8 到 20 位数字。

ORDER_STATUS_TEXT = {
    "pending_payment": "待付款",
    "paid": "已付款",
    "shipped": "已发货",
    "completed": "已完成",
    "cancelled": "已取消",
    "refunded": "已退款",
}
"""订单状态编码到中文展示文案的映射。"""


class OrderQueryTool:
    """按当前用户查询订单信息的聊天工具。

    该工具只读取 `user_orders` 表中属于当前登录用户的数据，避免不同用户之间
    的订单信息串用；当问题没有明确订单号时，默认返回当前用户最近的订单。
    """

    name = "query_user_orders"
    schema: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": name,
            "description": (
                "查询当前登录用户可见的订单信息。用户询问订单状态、物流、发货、退款、"
                "售后或最近订单时使用；没有订单号时可以查询最近订单，禁止编造订单号。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {
                        "type": "string",
                        "description": "用户提供的订单号，例如 OD20260528001；没有提供时省略或传空字符串。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "未指定订单号时返回最近订单数量，默认 5，范围 1 到 5。",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, mysql_repository: MySQLRepository, limit: int = 5) -> None:
        """初始化订单工具。

        Args:
            mysql_repository: MySQL 数据仓储，用于执行订单查询。
            limit: 未指定订单号时最多返回的最近订单数量。
        """
        self.mysql_repository = mysql_repository
        self.limit = limit

    def can_handle(self, question: str) -> bool:
        """判断用户问题是否属于订单查询。

        Args:
            question: 用户本轮问题。

        Returns:
            包含订单相关关键词或明显订单号时返回 True，否则返回 False。
        """
        normalized_question = question.strip()
        if not normalized_question:
            return False
        if ORDER_NO_PATTERN.search(normalized_question):
            return True
        has_excluded_intent = any(keyword in normalized_question for keyword in ORDER_EXCLUSION_KEYWORDS)
        if has_excluded_intent:
            return False
        has_strong_intent = any(keyword in normalized_question for keyword in ORDER_STRONG_INTENT_KEYWORDS)
        if has_strong_intent:
            return True
        has_weak_intent = any(keyword in normalized_question for keyword in ORDER_WEAK_INTENT_KEYWORDS)
        return has_weak_intent and any(keyword in normalized_question for keyword in ("这单", "该订单", "订单"))

    def call(self, user_id: int, arguments: dict[str, Any]) -> ToolExecution:
        """查询当前用户订单并格式化为大模型可读文本。

        Args:
            user_id: 当前登录用户 ID，作为订单查询的强制过滤条件。
            arguments: 模型通过 Function Calling 生成的结构化查询参数。

        Returns:
            ToolExecution，content 中包含订单查询结果或未命中提示。
        """
        order_no = self._normalize_order_no(arguments.get("order_no"))
        limit = self._normalize_limit(arguments.get("limit"))
        orders = self.mysql_repository.list_user_orders(user_id=user_id, order_no=order_no, limit=limit)
        if not orders:
            content = self._build_empty_result(order_no)
        else:
            content = self._build_order_result(orders, order_no)
        return ToolExecution(name=self.name, content=content)

    def call_from_question(self, user_id: int, question: str) -> ToolExecution:
        """从问题文本中提取订单号并查询订单，用于本地 fallback。

        Args:
            user_id: 当前登录用户 ID，作为订单查询的强制过滤条件。
            question: 用户本轮问题，用于提取订单号。

        Returns:
            ToolExecution，content 中包含订单查询结果或未命中提示。
        """
        return self.call(user_id, {"order_no": self._extract_order_no(question), "limit": self.limit})

    def _extract_order_no(self, question: str) -> str | None:
        """从用户问题中提取订单号。

        Args:
            question: 用户本轮问题。

        Returns:
            识别到的订单号；未识别到时返回 None。
        """
        match = ORDER_NO_PATTERN.search(question)
        return match.group(0).upper() if match else None

    def _normalize_order_no(self, value: object) -> str | None:
        """规范化模型传入的订单号参数。

        Args:
            value: 模型生成的订单号参数，可能为空或非字符串。

        Returns:
            规范化后的订单号；没有有效订单号时返回 None。
        """
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        if not stripped:
            return None
        match = ORDER_NO_PATTERN.search(stripped)
        return match.group(0).upper() if match else stripped.upper()

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

    def _build_empty_result(self, order_no: str | None) -> str:
        """构建订单未命中的工具结果文本。

        Args:
            order_no: 用户问题中识别到的订单号，可能为空。

        Returns:
            可直接放入 Prompt 的中文结果说明。
        """
        if order_no:
            return f"订单查询结果：未查询到当前用户名下订单号为 {order_no} 的订单。"
        return "订单查询结果：未查询到当前用户名下的订单记录。"

    def _build_order_result(self, orders: list[OrderRecord], order_no: str | None) -> str:
        """构建订单命中的工具结果文本。

        Args:
            orders: 当前用户可访问的订单列表。
            order_no: 用户问题中识别到的订单号，可能为空。

        Returns:
            包含订单号、商品、金额、状态和创建时间的中文结果文本。
        """
        title = f"订单查询结果：已查询到订单号 {order_no}。" if order_no else f"订单查询结果：已查询到最近 {len(orders)} 个订单。"
        lines = [title]
        for index, order in enumerate(orders, start=1):
            lines.append(
                "\n".join(
                    [
                        f"{index}. 订单号：{order.order_no}",
                        f"   商品名称：{order.product_name}",
                        f"   商品数量：{order.product_quantity}",
                        f"   订单金额：{self._format_amount(order.order_amount, order.currency)}",
                        f"   订单状态：{ORDER_STATUS_TEXT.get(order.order_status, order.order_status)}",
                        f"   支付时间：{self._format_time(order.paid_at)}",
                        f"   发货时间：{self._format_time(order.shipped_at)}",
                        f"   创建时间：{order.created_at:%Y-%m-%d %H:%M:%S}",
                        f"   订单备注：{order.remark or '无'}",
                    ]
                )
            )
        return "\n".join(lines)

    def _format_time(self, value: object) -> str:
        """格式化订单时间。

        Args:
            value: 数据库返回的 datetime 值，未发生对应动作时可能为空。

        Returns:
            `YYYY-MM-DD HH:MM:SS` 格式的时间文本；为空时返回 `暂无`。
        """
        if not value:
            return "暂无"
        return f"{value:%Y-%m-%d %H:%M:%S}"

    def _format_amount(self, amount: Decimal, currency: str) -> str:
        """格式化订单金额。

        Args:
            amount: 数据库中的订单金额。
            currency: 数据库中的币种编码。

        Returns:
            人类可读的金额文本，例如 `¥199.00 CNY`。
        """
        prefix = "¥" if currency == "CNY" else ""
        return f"{prefix}{amount:.2f} {currency}"
