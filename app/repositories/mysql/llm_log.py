"""大模型请求日志 ORM 数据访问方法。"""

from sqlalchemy import func, select

from app.models import LLMRequestLog
from app.repositories.mysql.base import BaseMySQLMixin
from app.repositories.mysql.mappers import map_llm_request_log
from app.repositories.mysql.records import LLMRequestLogRecord


class LLMLogMySQLMixin(BaseMySQLMixin):
    """封装大模型请求日志相关 MySQL 读写操作。"""

    def list_llm_request_logs(self, page: int, page_size: int) -> list[LLMRequestLogRecord]:
        """分页查询大模型请求日志，按创建时间倒序。

        Args:
            page: 分页页码，从 1 开始。
            page_size: 每页返回的记录数量。
        """
        offset = max(page - 1, 0) * page_size
        rows = self._scalars(
            select(LLMRequestLog)
            .order_by(LLMRequestLog.created_at.desc(), LLMRequestLog.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [map_llm_request_log(row) for row in rows]

    def count_llm_request_logs(self) -> int:
        """统计大模型请求日志总条数，用于分页。"""
        total = self._scalar_one_or_none(select(func.count()).select_from(LLMRequestLog))
        return int(total or 0)

    def get_llm_request_log(self, log_id: int) -> LLMRequestLogRecord | None:
        """按主键查询单条大模型请求日志详情，查不到返回 None。

        Args:
            log_id: 日志自增主键。
        """
        row = self._scalar_one_or_none(select(LLMRequestLog).where(LLMRequestLog.id == log_id).limit(1))
        return map_llm_request_log(row) if row else None

    def add_llm_request_log(
        self,
        model: str,
        base_url: str | None,
        request_payload: str,
        response_payload: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        latency_ms: int | None,
        status: str,
        error_message: str | None,
    ) -> None:
        """记录一次大模型请求的参数与响应。

        Args:
            model: 本次请求使用的模型名称。
            base_url: OpenAI 兼容接口基础地址，未配置时为空。
            request_payload: 完整请求参数 JSON 文本。
            response_payload: 完整响应数据 JSON 文本；请求失败时为空。
            prompt_tokens: 提示词消耗 token 数，缺失时为空。
            completion_tokens: 补全消耗 token 数，缺失时为空。
            total_tokens: 本次请求总消耗 token 数，缺失时为空。
            latency_ms: 请求往返耗时（毫秒），缺失时为空。
            status: 请求结果状态，success 或 error。
            error_message: 请求失败时的错误摘要；成功时为空。
        """
        log = LLMRequestLog(
            model=model,
            base_url=base_url,
            request_payload=request_payload,
            response_payload=response_payload,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self._add(log)
        self._flush()
