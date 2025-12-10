#!/usr/bin/env python3
"""
AutoTrading Backend API Server
使用 FastAPI + WebSocket + Redis Pub/Sub 提供實時K線數據
支援多實例部署
"""

import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from core.okx_data_feed import OKXDataFeed, KlineData
from core.redis_manager import redis_manager, Channels
from api.trading_api import router as trading_router


# Pydantic 模型
class HistoricalDataRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "5m"
    limit: int = 100


class SubscribeRequest(BaseModel):
    symbols: List[str] = ["BTC/USDT", "ETH/USDT"]
    timeframe: str = "5m"


# 全局變量
okx_feed = OKXDataFeed()
current_subscriptions: Dict[str, Any] = {
    'symbols': [],
    'timeframe': '5m'
}


class ConnectionManager:
    """WebSocket 連接管理器（支持多實例）"""

    def __init__(self):
        self.local_connections: List[WebSocket] = []
        self.instance_id = str(uuid.uuid4())[:8]
        logger.info(f"ConnectionManager 實例 ID: {self.instance_id}")

    async def connect(self, websocket: WebSocket):
        """新客戶端連接"""
        await websocket.accept()
        self.local_connections.append(websocket)
        logger.info(f"[{self.instance_id}] 新連接，本地連接數: {len(self.local_connections)}")

    def disconnect(self, websocket: WebSocket):
        """客戶端斷開連接"""
        if websocket in self.local_connections:
            self.local_connections.remove(websocket)
        logger.info(f"[{self.instance_id}] 斷開連接，本地連接數: {len(self.local_connections)}")

    async def broadcast_local(self, message: Dict[str, Any]):
        """廣播到本地所有連接"""
        if not self.local_connections:
            return

        message_str = json.dumps(message, default=str)
        disconnect_list = []

        for connection in self.local_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"發送消息失敗: {e}")
                disconnect_list.append(connection)

        for connection in disconnect_list:
            self.disconnect(connection)

    async def broadcast_global(self, channel: str, message: Dict[str, Any]):
        """通過 Redis 廣播到所有實例"""
        if redis_manager.is_connected:
            await redis_manager.publish(channel, {
                "instance_id": self.instance_id,
                "message": message
            })
        # 同時本地廣播（減少延遲）
        await self.broadcast_local(message)

    async def handle_redis_message(self, data: Dict[str, Any]):
        """處理來自 Redis 的消息"""
        # 避免處理自己發出的消息
        if data.get("instance_id") == self.instance_id:
            return

        message = data.get("message", {})
        await self.broadcast_local(message)


# 連接管理器實例
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時執行
    logger.info("AutoTrading Backend 正在啟動...")

    # 連接 Redis
    redis_connected = await redis_manager.connect()
    if redis_connected:
        logger.info("✅ Redis 連接成功")
        # 訂閱 Redis 頻道
        await redis_manager.subscribe(Channels.KLINE_UPDATE, manager.handle_redis_message)
        await redis_manager.subscribe(Channels.TICKER_UPDATE, manager.handle_redis_message)
        # 啟動監聽器
        await redis_manager.start_listener()
    else:
        logger.warning("⚠️ Redis 未連接，使用本地模式")

    # 測試 OKX API 連接
    connection_ok = await okx_feed.test_connection()
    if connection_ok:
        logger.info("✅ OKX API 連接正常")
    else:
        logger.error("❌ OKX API 連接失敗")

    logger.info(f"🚀 AutoTrading Backend 啟動完成 (實例: {manager.instance_id})")

    yield

    # 關閉時執行
    logger.info("AutoTrading Backend 正在關閉...")
    okx_feed.stop_realtime_feed()
    await redis_manager.disconnect()
    logger.info("👋 AutoTrading Backend 已關閉")


# 初始化 FastAPI 應用
app = FastAPI(
    title="AutoTrading Backend",
    description="加密貨幣自動交易後端API (支援多實例)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊交易 API 路由
app.include_router(trading_router)


# API 端點
@app.get("/")
async def root():
    """API 根端點"""
    return {
        "message": "AutoTrading Backend API",
        "version": "2.0.0",
        "instance_id": manager.instance_id,
        "status": "running",
        "redis_connected": redis_manager.is_connected,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    connection_ok = await okx_feed.test_connection()

    return {
        "status": "healthy" if connection_ok else "unhealthy",
        "okx_api": "connected" if connection_ok else "disconnected",
        "redis": "connected" if redis_manager.is_connected else "disconnected",
        "instance_id": manager.instance_id,
        "active_connections": len(manager.local_connections),
        "subscriptions": current_subscriptions,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/historical")
async def get_historical_data(
    symbol: str = Query(default="BTC/USDT"),
    timeframe: str = Query(default="5m"),
    limit: int = Query(default=100, le=500)
):
    """獲取歷史K線數據（GET 方法，支援緩存）"""
    try:
        cache_key = f"historical:{symbol}:{timeframe}:{limit}"

        # 嘗試從緩存獲取
        if redis_manager.is_connected:
            cached = await redis_manager.get_cache(cache_key)
            if cached:
                logger.debug(f"從緩存獲取歷史數據: {symbol}")
                return cached

        logger.info(f"獲取歷史數據: {symbol} {timeframe} limit={limit}")

        klines = await okx_feed.get_historical_klines(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )

        chart_data = []
        for kline in klines:
            chart_data.append({
                "time": kline.timestamp // 1000,
                "open": kline.open,
                "high": kline.high,
                "low": kline.low,
                "close": kline.close,
                "volume": kline.volume
            })

        result = {
            "success": True,
            "data": chart_data,
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(chart_data)
        }

        # 緩存結果（根據時間框架設置不同的過期時間）
        if redis_manager.is_connected:
            expire_map = {'1m': 30, '5m': 60, '15m': 120, '1h': 300, '4h': 600, '1d': 1800}
            expire = expire_map.get(timeframe, 60)
            await redis_manager.set_cache(cache_key, result, expire)

        return result

    except Exception as e:
        logger.error(f"獲取歷史數據失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/historical")
async def post_historical_data(request: HistoricalDataRequest):
    """獲取歷史K線數據（POST 方法，向後兼容）"""
    return await get_historical_data(
        symbol=request.symbol,
        timeframe=request.timeframe,
        limit=request.limit
    )


@app.get("/api/price/{symbol}")
async def get_current_price(symbol: str):
    """獲取當前價格"""
    try:
        if "/" not in symbol:
            symbol = symbol.replace("-", "/").upper()

        price_data = await okx_feed.get_current_price(symbol)

        if not price_data:
            raise HTTPException(status_code=404, detail="Symbol not found")

        return {
            "success": True,
            "data": price_data
        }

    except Exception as e:
        logger.error(f"獲取價格失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subscribe")
async def subscribe_realtime(request: SubscribeRequest):
    """訂閱實時數據"""
    try:
        logger.info(f"訂閱實時數據: {request.symbols} {request.timeframe}")

        # 停止舊的訂閱
        if current_subscriptions['symbols']:
            okx_feed.stop_realtime_feed()

        # 更新當前訂閱
        current_subscriptions['symbols'] = request.symbols
        current_subscriptions['timeframe'] = request.timeframe

        # 設置回調函數
        def on_kline_update(kline: KlineData):
            """K線更新回調"""
            message = {
                "type": "KLINE_UPDATE",
                "data": {
                    "symbol": kline.symbol,
                    "timestamp": kline.timestamp,
                    "time": kline.timestamp // 1000,
                    "open": kline.open,
                    "high": kline.high,
                    "low": kline.low,
                    "close": kline.close,
                    "volume": kline.volume,
                    "timeframe": kline.timeframe
                }
            }

            # 通過 Redis 廣播（如果連接）或本地廣播
            asyncio.create_task(
                manager.broadcast_global(Channels.KLINE_UPDATE, message)
            )

        def on_ticker_update(ticker: Dict):
            """價格更新回調"""
            message = {
                "type": "TICKER_UPDATE",
                "data": ticker
            }

            asyncio.create_task(
                manager.broadcast_global(Channels.TICKER_UPDATE, message)
            )

        # 設置回調
        okx_feed.set_kline_callback(on_kline_update)
        okx_feed.set_ticker_callback(on_ticker_update)

        # 啟動實時數據推送
        okx_feed.start_realtime_feed(request.symbols, request.timeframe)

        return {
            "success": True,
            "message": f"已訂閱 {len(request.symbols)} 個交易對的實時數據",
            "subscriptions": current_subscriptions
        }

    except Exception as e:
        logger.error(f"訂閱實時數據失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/subscribe")
async def unsubscribe_realtime():
    """取消實時數據訂閱"""
    try:
        okx_feed.stop_realtime_feed()
        current_subscriptions['symbols'] = []

        return {
            "success": True,
            "message": "已取消所有實時數據訂閱"
        }

    except Exception as e:
        logger.error(f"取消訂閱失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點"""
    await manager.connect(websocket)

    try:
        # 發送連接成功消息
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_SUCCESS",
            "data": {
                "message": "WebSocket 連接已建立",
                "instance_id": manager.instance_id,
                "timestamp": datetime.now().isoformat(),
                "subscriptions": current_subscriptions
            }
        }))

        # 發送最近的歷史數據
        if current_subscriptions['symbols']:
            for symbol in current_subscriptions['symbols']:
                try:
                    klines = await okx_feed.get_historical_klines(
                        symbol=symbol,
                        timeframe=current_subscriptions['timeframe'],
                        limit=50
                    )

                    for kline in klines[-10:]:
                        message = {
                            "type": "KLINE_UPDATE",
                            "data": {
                                "symbol": kline.symbol,
                                "timestamp": kline.timestamp,
                                "time": kline.timestamp // 1000,
                                "open": kline.open,
                                "high": kline.high,
                                "low": kline.low,
                                "close": kline.close,
                                "volume": kline.volume,
                                "timeframe": kline.timeframe
                            }
                        }
                        await websocket.send_text(json.dumps(message))
                        await asyncio.sleep(0.01)

                except Exception as e:
                    logger.error(f"發送歷史數據失敗: {e}")

        # 等待客戶端消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))

                elif message.get('type') == 'subscribe':
                    # 處理訂閱請求
                    symbols = message.get('symbols', ['BTC/USDT'])
                    timeframe = message.get('timeframe', '5m')

                    current_subscriptions['symbols'] = symbols
                    current_subscriptions['timeframe'] = timeframe

                    await websocket.send_text(json.dumps({
                        "type": "SUBSCRIBED",
                        "data": {"symbols": symbols, "timeframe": timeframe}
                    }))

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket 消息處理錯誤: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket 連接錯誤: {e}")
    finally:
        manager.disconnect(websocket)


if __name__ == "__main__":
    # 配置日誌
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.add(
        os.path.join(log_dir, "backend_{time}.log"),
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    # 啟動服務器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
