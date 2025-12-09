"""
OKX Data Feed Service
整合 OKX API 提供實時K線數據和市場數據
"""

import asyncio
import json
import ccxt
import websocket
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger
from dataclasses import dataclass


@dataclass
class KlineData:
    """K線數據結構"""
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
    closed: bool = False


class OKXDataFeed:
    """
    OKX 數據饋送服務
    提供實時K線數據和歷史數據
    """
    
    def __init__(self):
        """初始化 OKX 數據服務"""
        # 初始化 CCXT 客戶端（無需API密鑰即可獲取公開數據）
        self.client = ccxt.okx({
            'sandbox': False,  # 使用正式環境
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # WebSocket 配置
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_connection = None
        self.ws_thread = None
        self.running = False
        
        # 數據回調函數
        self.on_kline_update: Optional[Callable[[KlineData], None]] = None
        self.on_ticker_update: Optional[Callable[[Dict], None]] = None
        
        # 訂閱管理
        self.subscriptions = []
        self.kline_cache = {}
        
        logger.info("OKX Data Feed 初始化完成")
    
    async def get_historical_klines(self, symbol: str, timeframe: str = '5m', 
                                    limit: int = 100) -> List[KlineData]:
        """
        獲取歷史K線數據
        
        Args:
            symbol: 交易對符號 (e.g., 'BTC/USDT')
            timeframe: 時間框架 (1m, 5m, 15m, 1h, 4h, 1d)
            limit: 返回數據筆數 (最多300)
            
        Returns:
            K線數據列表
        """
        try:
            logger.info(f"獲取 {symbol} {timeframe} 歷史數據，限制 {limit} 根")
            
            # 獲取數據
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_ohlcv,
                symbol, timeframe, None, limit
            )
            
            # 轉換為內部格式
            klines = []
            for candle in ohlcv:
                kline = KlineData(
                    symbol=symbol,
                    timestamp=int(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                    timeframe=timeframe,
                    closed=True
                )
                klines.append(kline)
            
            logger.info(f"成功獲取 {len(klines)} 根K線數據")
            return klines
            
        except Exception as e:
            logger.error(f"獲取歷史數據失敗 {symbol}: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> Dict:
        """獲取當前價格信息"""
        try:
            ticker = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_ticker,
                symbol
            )
            
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'volume_24h': ticker['baseVolume'],
                'change_24h': ticker['change'],
                'change_percent_24h': ticker['percentage'],
                'timestamp': ticker['timestamp']
            }
            
        except Exception as e:
            logger.error(f"獲取價格失敗 {symbol}: {e}")
            return {}
    
    def start_realtime_feed(self, symbols: List[str], timeframe: str = '5m'):
        """
        啟動實時數據推送
        
        Args:
            symbols: 交易對列表 ['BTC/USDT', 'ETH/USDT']
            timeframe: 時間框架
        """
        if self.running:
            logger.warning("實時數據推送已在運行中")
            return
        
        self.running = True
        self.subscriptions = []
        
        # 準備訂閱參數
        for symbol in symbols:
            # 轉換符號格式：BTC/USDT -> BTC-USDT
            okx_symbol = symbol.replace('/', '-')
            
            # K線訂閱
            self.subscriptions.append({
                "channel": f"candle{timeframe}",
                "instId": okx_symbol
            })
            
            # Ticker 訂閱
            self.subscriptions.append({
                "channel": "tickers",
                "instId": okx_symbol
            })
        
        # 啟動 WebSocket
        self._start_websocket()
        
        logger.info(f"實時數據推送已啟動: {symbols} ({timeframe})")
    
    def stop_realtime_feed(self):
        """停止實時數據推送"""
        self.running = False
        
        if self.ws_connection:
            self.ws_connection.close()
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
        
        logger.info("實時數據推送已停止")
    
    def _start_websocket(self):
        """啟動 WebSocket 連接"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                
                # 處理訂閱確認
                if 'event' in data:
                    if data['event'] == 'subscribe':
                        logger.info(f"訂閱成功: {data.get('arg', {})}")
                    elif data['event'] == 'error':
                        logger.error(f"訂閱失敗: {data}")
                    return
                
                # 處理數據推送
                if 'data' in data and 'arg' in data:
                    self._process_websocket_data(data)
                    
            except Exception as e:
                logger.error(f"WebSocket 消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket 錯誤: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket 連接已關閉")
            
            # 自動重連
            if self.running:
                logger.info("5秒後自動重連...")
                threading.Timer(5.0, self._start_websocket).start()
        
        def on_open(ws):
            logger.info("WebSocket 連接已建立")
            
            # 發送訂閱請求
            subscribe_msg = {
                "op": "subscribe",
                "args": self.subscriptions
            }
            
            ws.send(json.dumps(subscribe_msg))
            logger.info(f"已發送訂閱請求: {len(self.subscriptions)} 個頻道")
        
        # 創建 WebSocket 連接
        websocket.enableTrace(False)
        self.ws_connection = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # 在背景線程中運行
        self.ws_thread = threading.Thread(
            target=self.ws_connection.run_forever,
            daemon=True
        )
        self.ws_thread.start()
    
    def _process_websocket_data(self, data: Dict):
        """處理 WebSocket 推送的數據"""
        try:
            channel = data['arg']['channel']
            inst_id = data['arg']['instId']
            
            # 轉換符號格式：BTC-USDT -> BTC/USDT
            symbol = inst_id.replace('-', '/')
            
            if channel.startswith('candle'):
                # 處理K線數據
                timeframe = channel.replace('candle', '')
                
                for candle_raw in data['data']:
                    kline = KlineData(
                        symbol=symbol,
                        timestamp=int(candle_raw[0]),
                        open=float(candle_raw[1]),
                        high=float(candle_raw[2]),
                        low=float(candle_raw[3]),
                        close=float(candle_raw[4]),
                        volume=float(candle_raw[5]),
                        timeframe=timeframe,
                        closed=True  # OKX WebSocket 推送的都是已完成的K線
                    )
                    
                    # 緩存最新數據
                    cache_key = f"{symbol}_{timeframe}"
                    self.kline_cache[cache_key] = kline
                    
                    # 觸發回調
                    if self.on_kline_update:
                        self.on_kline_update(kline)
                    
                    logger.debug(f"K線更新: {symbol} {timeframe} - {kline.close}")
            
            elif channel == 'tickers':
                # 處理 Ticker 數據
                for ticker_raw in data['data']:
                    ticker_data = {
                        'symbol': symbol,
                        'price': float(ticker_raw['last']),
                        'bid': float(ticker_raw['bidPx']) if ticker_raw['bidPx'] else None,
                        'ask': float(ticker_raw['askPx']) if ticker_raw['askPx'] else None,
                        'high_24h': float(ticker_raw['high24h']),
                        'low_24h': float(ticker_raw['low24h']),
                        'volume_24h': float(ticker_raw['vol24h']),
                        'change_24h': float(ticker_raw['chgUtc']),
                        'change_percent_24h': float(ticker_raw['chgUtc']) * 100,
                        'timestamp': int(ticker_raw['ts'])
                    }
                    
                    # 觸發回調
                    if self.on_ticker_update:
                        self.on_ticker_update(ticker_data)
                    
                    logger.debug(f"價格更新: {symbol} - {ticker_data['price']}")
            
        except Exception as e:
            logger.error(f"數據處理錯誤: {e}")
    
    def set_kline_callback(self, callback: Callable[[KlineData], None]):
        """設置K線數據回調函數"""
        self.on_kline_update = callback
        logger.info("K線回調函數已設置")
    
    def set_ticker_callback(self, callback: Callable[[Dict], None]):
        """設置價格數據回調函數"""
        self.on_ticker_update = callback
        logger.info("價格回調函數已設置")
    
    def get_latest_kline(self, symbol: str, timeframe: str) -> Optional[KlineData]:
        """獲取最新的K線數據"""
        cache_key = f"{symbol}_{timeframe}"
        return self.kline_cache.get(cache_key)
    
    async def test_connection(self) -> bool:
        """測試 API 連接"""
        try:
            # 測試獲取BTC價格
            ticker = await self.get_current_price('BTC/USDT')
            if ticker and 'price' in ticker:
                logger.info(f"API 連接測試成功，BTC 當前價格: {ticker['price']}")
                return True
            else:
                logger.error("API 連接測試失敗")
                return False
                
        except Exception as e:
            logger.error(f"API 連接測試失敗: {e}")
            return False


# 單例實例
okx_data_feed = OKXDataFeed()