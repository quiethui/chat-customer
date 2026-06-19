"""商品 ORM 数据访问方法。"""

from sqlalchemy import or_, select

from app.models import Product
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_product
from app.repositories.mysql.records import ProductRecord


class ProductMySQLMixin(BaseMySQLMixin):
    """封装商品相关 MySQL 查询操作（全局商品目录，不区分用户）。"""

    def list_products(
        self,
        keyword: str | None = None,
        product_sku: str | None = None,
        limit: int = 5,
    ) -> list[ProductRecord]:
        """按关键词或 SKU 查询商品列表。

        Args:
            keyword: 可选商品名称或类目关键词；为空且未指定 SKU 时返回在售热门商品。
            product_sku: 可选商品 SKU，精确匹配。
            limit: 最大返回数量，会被限制在 1 到 20 之间。
        """
        safe_limit = min(max(limit, 1), 20)
        conditions = [Product.deleted_at.is_(None)]
        if product_sku:
            conditions.append(Product.product_sku == product_sku)
        elif keyword:
            like = f"%{keyword}%"
            conditions.append(
                or_(
                    Product.name.like(like),
                    Product.category.like(like),
                    Product.product_sku.like(like),
                )
            )
        rows = self._scalars(
            select(Product)
            .where(*conditions)
            # 在售商品优先，其次按库存从多到少，便于客服优先推荐有货商品。
            .order_by((Product.status == "on_sale").desc(), Product.stock.desc(), Product.id.asc())
            .limit(safe_limit)
        )
        return [map_product(row) for row in rows]
