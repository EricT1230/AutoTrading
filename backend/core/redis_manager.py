"""
Redis Pub/Sub 管理器
用於多實例部署時的狀態同步
"""

import asyncio
import json
import os
from typing import Callable, Dict, Optional, Set, Any
from loguru import logger

try:
    import redis.asyncio as aioredis
except ImportError:
    import redis as aioredis


class Channels:
    """Redis 頻道常量"""
    KLINE_UPDATE = "autotrading:kline:update"
    TICKER_UPDATE = "autotrading:ticker:update"
    ORDER_UPDATE = "autotrading:order:update"
    SIGNAL_UPDATE = "autotrading:signal:update"
    SYSTEM_STATUS = "autotrading:system:status"


class RedisManager:
    """Redis 連接和 Pub/Sub 管理器"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.subscribers: Dict[str, Set[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.redis is not None

    async def connect(self) -> bool:
        """建立 Redis 連接"""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 測試連接
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            self._connected = True
            logger.info(f"Redis 連接成功: {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Redis 連接失敗 (將使用本地模式): {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """關閉 Redis 連接"""
        self._running = False
        self._connected = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()

        if self.redis:
            await self.redis.close()

        logger.info("Redis 連接已關閉")

    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """發布消息到頻道"""
        if not self.is_connected:
            return False

        try:
            message_str = json.dumps(message, default=str)
            await self.redis.publish(channel, message_str)
            logger.debug(f"發布消息到 {channel}")
            return True
        except Exception as e:
            logger.error(f"發布消息失敗: {e}")
            return False

    async def subscribe(self, channel: str, callback: Callable):
        """訂閱頻道"""
        if not self.is_connected:
            logger.warning("Redis 未連接，無法訂閱")
            return

        if channel not in self.subscribers:
            self.subscribers[channel] = set()
            await self.pubsub.subscribe(channel)
            logger.info(f"已訂閱頻道: {channel}")

        self.subscribers[channel].add(callback)

    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        """取消訂閱頻道"""
        if channel not in self.subscribers:
            return

        if callback:
            self.subscribers[channel].discard(callback)
            if not self.subscribers[channel]:
                if self.pubsub:
                    await self.pubsub.unsubscribe(channel)
                del self.subscribers[channel]
        else:
            if self.pubsub:
                await self.pubsub.unsubscribe(channel)
            del self.subscribers[channel]

    async def start_listener(self):
        """啟動消息監聽器"""
        if self._running or not self.is_connected:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("Redis 消息監聽器已啟動")

    async def _listen(self):
        """監聽消息的內部方法"""
        while self._running and self.is_connected:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message and message['type'] == 'message':
                    channel = message['channel']
                    try:
                        data = json.loads(message['data'])
                    except json.JSONDecodeError:
                        data = message['data']

                    if channel in self.subscribers:
                        for callback in list(self.subscribers[channel]):
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"回調處理錯誤: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"監聽消息錯誤: {e}")
                await asyncio.sleep(1)

    # 緩存操作
    async def set_cache(self, key: str, value: Dict[str, Any], expire: int = 3600) -> bool:
        """設置緩存"""
        if not self.is_connected:
            return False

        try:
            await self.redis.setex(key, expire, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.error(f"設置緩存失敗: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """獲取緩存"""
        if not self.is_connected:
            return None

        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"獲取緩存失敗: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        """刪除緩存"""
        if not self.is_connected:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"刪除緩存失敗: {e}")
            return False

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        expire: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """獲取緩存，如果不存在則設置"""
        cached = await self.get_cache(key)
        if cached:
            return cached

        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        if value:
            await self.set_cache(key, value, expire)
        return value


# 全域實例
redis_manager = RedisManager()
