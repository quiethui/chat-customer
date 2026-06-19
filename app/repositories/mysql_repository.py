"""基于 SQLAlchemy ORM 的 MySQL 数据仓储。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.mysql.auth import AuthMySQLMixin
from app.repositories.mysql.chat import ChatMySQLMixin
from app.repositories.mysql.knowledge import KnowledgeMySQLMixin
from app.repositories.mysql.order import OrderMySQLMixin


class MySQLRepository(AuthMySQLMixin, ChatMySQLMixin, KnowledgeMySQLMixin, OrderMySQLMixin):
    """封装所有 MySQL 读写操作，业务层只能通过该类访问数据库。"""

    def __init__(self, settings: Settings, session: Session) -> None:
        """初始化 MySQL 仓储。

        Args:
            settings: 应用运行配置，提供 MySQL 连接参数。
            session: 当前请求或后台任务持有的 SQLAlchemy Session。
        """
        self.settings = settings
        self.session = session

    def commit(self) -> None:
        """提交当前数据库事务。"""
        self.session.commit()

    def rollback(self) -> None:
        """回滚当前数据库事务。"""
        self.session.rollback()

    def close(self) -> None:
        """关闭当前数据库 Session。"""
        self.session.close()
