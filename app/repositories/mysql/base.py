"""MySQL 仓储 mixin 基础能力。"""

from collections.abc import Iterable
from typing import Any

from sqlalchemy.engine import Result, ScalarResult
from sqlalchemy.orm import Session


class BaseMySQLMixin:
    """为 MySQL mixin 声明共享 Session，并封装常用 ORM 操作。"""

    session: Session

    def _execute(self, statement: Any) -> Result[Any]:
        """执行 SQLAlchemy 语句并返回原始结果。"""
        return self.session.execute(statement)

    def _scalars(self, statement: Any) -> ScalarResult[Any]:
        """执行查询并返回标量结果集。"""
        return self._execute(statement).scalars()

    def _scalar_one_or_none(self, statement: Any) -> Any | None:
        """执行查询并返回单条标量结果，查不到时返回 None。"""
        return self._execute(statement).scalar_one_or_none()

    def _all(self, statement: Any) -> list[Any]:
        """执行查询并返回全部行结果。"""
        return list(self._execute(statement).all())

    def _add(self, instance: object) -> None:
        """将 ORM 实例加入当前 Session。"""
        self.session.add(instance)

    def _add_all(self, instances: Iterable[object]) -> None:
        """批量将 ORM 实例加入当前 Session。"""
        self.session.add_all(instances)

    def _flush(self) -> None:
        """将当前 Session 的变更刷新到数据库连接。"""
        self.session.flush()

    def _refresh(self, instance: object) -> None:
        """刷新 ORM 实例，使其包含数据库生成字段。"""
        self.session.refresh(instance)
