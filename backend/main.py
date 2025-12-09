#!/usr/bin/env python3
"""
AutoTrading Backend API Server
使用 FastAPI + WebSocket 提供實時K線數據
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from core.okx_data_feed import OKXDataFeed, KlineData


# Pydantic 模型
class HistoricalDataRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "5m"
    limit: int = 100


class SubscribeRequest(BaseModel):
    symbols: List[str] = ["BTC/USDT", "ETH/USDT"]
    timeframe: str = "5m"


# 初始化 FastAPI 應用
app = FastAPI(
    title="AutoTrading Backend",
    description="加密貨幣自動交易後端API",
    version="1.0.0"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局變量
okx_feed = OKXDataFeed()
connected_clients: List[WebSocket] = []
current_subscriptions = {
    'symbols': [],
    'timeframe': '5m'
}


class ConnectionManager:
    """WebSocket 連接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """新客戶端連接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"新客戶端連接，當前連接數: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """客戶端斷開連接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"客戶端斷開連接，當前連接數: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """廣播消息給所有連接的客戶端"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnect_list = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"發送消息失敗: {e}")
                disconnect_list.append(connection)
        
        # 清理斷開的連接
        for connection in disconnect_list:
            self.disconnect(connection)


# 連接管理器實例
manager = ConnectionManager()


# API 端點
@app.get("/")
async def root():
    """API 根端點"""
    return {
        "message": "AutoTrading Backend API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    # 測試 OKX API 連接
    connection_ok = await okx_feed.test_connection()
    
    return {
        "status": "healthy" if connection_ok else "unhealthy",
        "okx_api": "connected" if connection_ok else "disconnected",
        "active_connections": len(manager.active_connections),
        "subscriptions": current_subscriptions,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/historical")
async def get_historical_data(request: HistoricalDataRequest):
    """獲取歷史K線數據"""
    try:
        logger.info(f"獲取歷史數據請求: {request.symbol} {request.timeframe} limit={request.limit}")
        
        klines = await okx_feed.get_historical_klines(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=request.limit
        )
        
        # 轉換為前端所需格式
        chart_data = []
        for kline in klines:
            chart_data.append({
                "time": kline.timestamp // 1000,  # 轉換為秒
                "open": kline.open,
                "high": kline.high,
                "low": kline.low,
                "close": kline.close,
                "volume": kline.volume
            })
        
        return {
            "success": True,
            "data": chart_data,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "count": len(chart_data)
        }
        
    except Exception as e:
        logger.error(f"獲取歷史數據失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/price/{symbol}")
async def get_current_price(symbol: str):
    """獲取當前價格"""
    try:
        # 確保符號格式正確
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
                    "time": kline.timestamp // 1000,  # 前端需要秒級時間戳
                    "open": kline.open,
                    "high": kline.high,
                    "low": kline.low,
                    "close": kline.close,
                    "volume": kline.volume,
                    "timeframe": kline.timeframe
                }
            }
            
            # 使用 asyncio 在事件循環中廣播消息
            asyncio.create_task(manager.broadcast(message))
        
        def on_ticker_update(ticker: Dict):
            """價格更新回調"""
            message = {
                "type": "TICKER_UPDATE",
                "data": ticker
            }
            
            # 使用 asyncio 在事件循環中廣播消息
            asyncio.create_task(manager.broadcast(message))
        
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
    """WebSocket 端點，用於實時數據推送"""
    await manager.connect(websocket)
    
    try:
        # 發送連接成功消息
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_SUCCESS",
            "data": {
                "message": "WebSocket 連接已建立",
                "timestamp": datetime.now().isoformat(),
                "subscriptions": current_subscriptions
            }
        }))
        
        # 如果有歷史數據，發送給新連接的客戶端
        if current_subscriptions['symbols']:
            for symbol in current_subscriptions['symbols']:
                try:
                    # 發送少量歷史數據
                    klines = await okx_feed.get_historical_klines(
                        symbol=symbol,
                        timeframe=current_subscriptions['timeframe'],
                        limit=50
                    )
                    
                    for kline in klines[-10:]:  # 只發送最近10根
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
                        await asyncio.sleep(0.01)  # 避免發送過快
                        
                except Exception as e:
                    logger.error(f"發送歷史數據失敗: {e}")
        
        # 保持連接，等待客戶端消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 處理客戶端消息（如果需要）
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
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


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info("AutoTrading Backend 正在啟動...")
    
    # 測試 OKX API 連接
    connection_ok = await okx_feed.test_connection()
    if connection_ok:
        logger.info("✅ OKX API 連接正常")
    else:
        logger.error("❌ OKX API 連接失敗")
    
    logger.info("🚀 AutoTrading Backend 啟動完成")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("AutoTrading Backend 正在關閉...")
    
    # 停止實時數據推送
    okx_feed.stop_realtime_feed()
    
    logger.info("👋 AutoTrading Backend 已關閉")


if __name__ == "__main__":
    # 配置日誌
    logger.add(
        "logs/backend_{time}.log",
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