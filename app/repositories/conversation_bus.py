"""会话实时推送通道：基于 Redis 发布订阅，将坐席消息推送到客户 SSE。"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis
import redis.asyncio as aioredis

from app.core.config import Settings

logger = logging.getLogger(__name__)


AGENT_BROADCAST_CHANNEL = "agent:broadcast"


class ConversationBus:
    """基于 Redis Pub/Sub 的会话事件总线。

    - 每个会话频道 ``conv:{session_id}``：服务"客户端单会话流"（坐席回复→客户）。
    - 全局坐席广播频道 ``agent:broadcast``：服务"所有在线坐席的实时通知"
      （转人工请求、接管确认、客户消息提醒等需要让坐席侧看到的事件）。

    发布端使用同步 Redis 客户端（业务流程内调用），订阅端使用 redis.asyncio，
    供 SSE 端在异步生成器中实时消费事件。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化发布端 Redis 客户端并保存连接配置。

        Args:
            settings: 应用配置对象，提供 REDIS_URL。
        """
        self.redis_url = settings.redis_url
        self._publisher = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _channel(session_id: str) -> str:
        """生成会话事件频道名。

        Args:
            session_id: 聊天会话 ID。
        """
        return f"conv:{session_id}"

    def publish(self, session_id: str, event: dict[str, Any]) -> None:
        """向会话频道发布一条事件；发布失败只告警，不影响主流程。

        Args:
            session_id: 聊天会话 ID。
            event: 待发布的事件字典。
        """
        self._publish(self._channel(session_id), event, label=f"session_id={session_id}")

    def publish_broadcast(self, event: dict[str, Any]) -> None:
        """向坐席全局广播频道发布事件；发布失败只告警，不影响主流程。

        Args:
            event: 待广播的事件字典（建议带 ``type`` 字段供前端分发）。
        """
        self._publish(AGENT_BROADCAST_CHANNEL, event, label="agent_broadcast")

    def _publish(self, channel: str, event: dict[str, Any], *, label: str) -> None:
        """同步发布到指定频道，失败仅记录日志不抛出。

        Args:
            channel: 目标 Redis 频道名。
            event: 待发布事件字典。
            label: 失败日志中标识来源用的字符串。
        """
        try:
            self._publisher.publish(channel, json.dumps(event, ensure_ascii=False))
        except Exception:
            logger.warning("发布事件失败：%s", label, exc_info=True)

    async def subscribe(self, session_id: str, heartbeat_seconds: float = 15.0) -> AsyncIterator[dict[str, Any]]:
        """订阅会话频道，逐条产出事件；空闲时产出 ping 心跳维持连接。

        Args:
            session_id: 聊天会话 ID。
            heartbeat_seconds: 无消息时发送心跳的间隔秒数。

        Yields:
            会话事件字典；空闲时为 {"type": "ping"}。
        """
        async for event in self._subscribe_channel(self._channel(session_id), heartbeat_seconds):
            yield event

    async def subscribe_broadcast(self, heartbeat_seconds: float = 15.0) -> AsyncIterator[dict[str, Any]]:
        """订阅坐席全局广播频道，逐条产出事件；空闲时产出 ping 心跳。

        Args:
            heartbeat_seconds: 无消息时发送心跳的间隔秒数。

        Yields:
            广播事件字典；空闲时为 {"type": "ping"}。
        """
        async for event in self._subscribe_channel(AGENT_BROADCAST_CHANNEL, heartbeat_seconds):
            yield event

    async def _subscribe_channel(
        self, channel: str, heartbeat_seconds: float
    ) -> AsyncIterator[dict[str, Any]]:
        """订阅指定 Redis 频道并产出事件，空闲时产出 ping 心跳。

        Args:
            channel: 目标 Redis 频道名。
            heartbeat_seconds: 无消息时发送心跳的间隔秒数。
        """
        client = aioredis.from_url(self.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=heartbeat_seconds)
                if message is None:
                    yield {"type": "ping"}
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
                await client.aclose()
            except Exception:
                logger.warning("关闭订阅失败：channel=%s", channel, exc_info=True)
