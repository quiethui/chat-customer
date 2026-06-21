"""大模型请求日志服务。"""

from __future__ import annotations

from app.repositories.mysql.records import LLMRequestLogRecord
from app.repositories.mysql_repository import MySQLRepository


class LLMLogService:
    """大模型请求日志业务服务，负责日志的分页查询与详情查询。"""

    def __init__(self, repository: MySQLRepository) -> None:
        """初始化请求日志服务依赖。

        Args:
            repository: 当前服务使用的数据仓储实例。
        """
        self.repository = repository

    def list_logs(self, page: int = 1, page_size: int = 20) -> tuple[list[LLMRequestLogRecord], int]:
        """分页查询请求日志并返回总条数，页大小做上限保护。

        Args:
            page: 分页页码。
            page_size: 每页返回的记录数量。
        """
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        logs = self.repository.list_llm_request_logs(page, page_size)
        total = self.repository.count_llm_request_logs()
        return logs, total

    def get_log(self, log_id: int) -> LLMRequestLogRecord | None:
        """按 ID 查询请求日志详情，查不到返回 None。

        Args:
            log_id: 日志 ID。
        """
        return self.repository.get_llm_request_log(log_id)
