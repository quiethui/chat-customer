"""Redis 消息上下文仓储。"""

from __future__ import annotations

import json
from typing import Any

import redis

from app.core.config import Settings


class RedisContextRepository:
    """使用 Redis List 保存每个客户每个会话的短期聊天上下文。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Redis 客户端和上下文缓存参数。

        Args:
            settings: 应用配置对象。
        """
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.ttl_seconds = settings.redis_context_ttl_seconds
        self.context_limit = settings.chat_context_limit

    def get_messages(self, customer_id: int, session_id: str) -> list[dict[str, str]]:
        """读取指定客户、指定会话的历史消息。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        values = self.client.lrange(self._key(customer_id, session_id), 0, -1)
        messages: list[dict[str, str]] = []
        for value in values:
            try:
                item = json.loads(value)
            except json.JSONDecodeError:
                continue
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str):
                messages.append({"role": role, "content": content})
        return messages

    def append_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        """向会话上下文尾部追加消息，并裁剪到配置的最大条数。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            messages: 待写入或覆盖的聊天消息列表。
        """
        if not messages:
            return
        key = self._key(customer_id, session_id)
        payloads = [json.dumps(message, ensure_ascii=False) for message in messages]
        pipe = self.client.pipeline()
        pipe.rpush(key, *payloads)
        pipe.ltrim(key, -self.context_limit, -1)
        pipe.expire(key, self.ttl_seconds)
        pipe.execute()

    def replace_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        """用给定消息覆盖 Redis 上下文，常用于缓存缺失后从 MySQL 回填。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            messages: 待写入或覆盖的聊天消息列表。
        """
        key = self._key(customer_id, session_id)
        payloads = [json.dumps(message, ensure_ascii=False) for message in messages[-self.context_limit :]]
        pipe = self.client.pipeline()
        pipe.delete(key)
        if payloads:
            pipe.rpush(key, *payloads)
            pipe.expire(key, self.ttl_seconds)
        pipe.execute()

    def delete_session(self, customer_id: int, session_id: str) -> None:
        """删除某个会话的 Redis 上下文。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        self.client.delete(self._key(customer_id, session_id))

    @staticmethod
    def _key(customer_id: int, session_id: str) -> str:
        """生成 Redis key，包含 customer 命名空间避免不同客户会话串数据。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        return f"chat:context:customer:{customer_id}:{session_id}"


class NullContextRepository:
    """空上下文仓储，用于 Redis 不可用时的兼容实现。"""

    def get_messages(self, customer_id: int, session_id: str) -> list[dict[str, str]]:
        """始终返回空历史消息。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        _ = customer_id, session_id
        return []

    def append_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        """忽略追加上下文操作。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            messages: 待写入或覆盖的聊天消息列表。
        """
        _ = customer_id, session_id, messages

    def replace_messages(self, customer_id: int, session_id: str, messages: list[dict[str, str]]) -> None:
        """忽略覆盖上下文操作。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
            messages: 待写入或覆盖的聊天消息列表。
        """
        _ = customer_id, session_id, messages

    def delete_session(self, customer_id: int, session_id: str) -> None:
        """忽略删除上下文操作。

        Args:
            customer_id: 当前客户 ID，用于数据隔离。
            session_id: 聊天会话 ID。
        """
        _ = customer_id, session_id


ContextRepository = RedisContextRepository | NullContextRepository
