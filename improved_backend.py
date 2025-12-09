#!/usr/bin/env python3
"""
改進版後端服務
增強實時數據更新和調試功能
"""

import json
import asyncio
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import websocket
import ccxt
from loguru import logger

class ImprovedKlineServer:
    """改進版K線數據服務器"""
    
    def __init__(self):
        # 初始化 OKX 客戶端
        self.okx_client = ccxt.okx({
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # WebSocket 配置
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_connection = None
        self.latest_data = {}
        self.running = False
        self.connected_clients = []
        self.last_update_time = None
        self.update_count = 0
        
        # 測試用：定期更新模擬數據
        self.enable_mock_updates = True
        self.mock_price = 92000.0
        
        logger.info("ImprovedKlineServer 初始化完成")
    
    def get_historical_klines(self, symbol='BTC/USDT', timeframe='5m', limit=100):
        """獲取歷史 K線數據"""
        try:
            logger.info(f"獲取歷史數據: {symbol} {timeframe}")
            
            # 獲取數據
            ohlcv = self.okx_client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # 轉換為前端格式
            klines = []
            for candle in ohlcv:
                klines.append({
                    "time": int(candle[0] / 1000),  # 轉換為秒
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            
            logger.info(f"成功獲取 {len(klines)} 根K線")
            return klines
            
        except Exception as e:
            logger.error(f"獲取歷史數據失敗: {e}")
            return []
    
    def get_current_price(self, symbol='BTC/USDT'):
        """獲取當前價格"""
        try:
            ticker = self.okx_client.fetch_ticker(symbol)
            
            price_data = {
                'symbol': symbol,
                'price': float(ticker['last']),
                'bid': float(ticker['bid']) if ticker['bid'] else 0,
                'ask': float(ticker['ask']) if ticker['ask'] else 0,
                'high_24h': float(ticker['high']) if ticker['high'] else 0,
                'low_24h': float(ticker['low']) if ticker['low'] else 0,
                'volume_24h': float(ticker['baseVolume']) if ticker['baseVolume'] else 0,
                'change_percent_24h': float(ticker['percentage']) if ticker['percentage'] else 0,
                'timestamp': int(datetime.now().timestamp())
            }
            
            return price_data
            
        except Exception as e:
            logger.error(f"獲取價格失敗: {e}")
            return {}
    
    def start_mock_data_updates(self):
        """啟動模擬數據更新 (用於測試)"""
        if not self.enable_mock_updates:
            return
            
        def update_mock_data():
            while self.running:
                try:
                    # 模擬價格變化
                    import random
                    price_change = random.uniform(-50, 50)
                    self.mock_price += price_change
                    
                    # 創建模擬K線數據
                    current_time = int(time.time())
                    # 對齊到5分鐘邊界
                    aligned_time = (current_time // 300) * 300
                    
                    mock_kline = {
                        "symbol": "BTC/USDT",
                        "time": aligned_time,
                        "open": self.mock_price - 5,
                        "high": self.mock_price + random.uniform(0, 30),
                        "low": self.mock_price - random.uniform(0, 30),
                        "close": self.mock_price,
                        "volume": random.uniform(0.1, 2.0),
                        "timeframe": "5m"
                    }
                    
                    # 緩存數據
                    self.latest_data["BTC/USDT_5m"] = mock_kline
                    self.last_update_time = datetime.now()
                    self.update_count += 1
                    
                    # 廣播給所有連接的客戶端
                    self.broadcast_to_clients({
                        "type": "KLINE_UPDATE",
                        "data": mock_kline
                    })
                    
                    logger.info(f"模擬數據更新 #{self.update_count}: BTC價格 ${self.mock_price:.2f}")
                    
                    # 每30秒更新一次
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"模擬數據更新錯誤: {e}")
                    time.sleep(5)
        
        # 啟動模擬數據線程
        mock_thread = threading.Thread(target=update_mock_data, daemon=True)
        mock_thread.start()
        logger.info("✅ 模擬數據更新已啟動 (每30秒)")
    
    def start_realtime_data(self, symbols=['BTC/USDT'], timeframe='5m'):
        """啟動實時數據推送"""
        if self.running:
            return
            
        self.running = True
        logger.info(f"🚀 啟動實時數據推送: {symbols}")
        
        # 先嘗試啟動模擬數據更新
        if self.enable_mock_updates:
            self.start_mock_data_updates()
        
        # 然後嘗試 WebSocket 連接
        self.start_websocket_connection(symbols, timeframe)
    
    def start_websocket_connection(self, symbols, timeframe):
        """啟動 WebSocket 連接"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                logger.debug(f"收到WebSocket消息: {data}")
                
                if 'event' in data:
                    if data['event'] == 'subscribe':
                        logger.info(f"✅ WebSocket訂閱成功: {data.get('arg', {})}")
                    elif data['event'] == 'error':
                        logger.error(f"❌ WebSocket訂閱失敗: {data}")
                    return
                
                # 處理數據推送
                if 'data' in data and 'arg' in data:
                    channel = data['arg']['channel']
                    inst_id = data['arg']['instId']
                    symbol = inst_id.replace('-', '/')
                    
                    if channel.startswith('candle'):
                        # 處理K線數據
                        tf = channel.replace('candle', '')
                        
                        for candle_raw in data['data']:
                            kline_data = {
                                "symbol": symbol,
                                "time": int(candle_raw[0]) // 1000,
                                "open": float(candle_raw[1]),
                                "high": float(candle_raw[2]),
                                "low": float(candle_raw[3]),
                                "close": float(candle_raw[4]),
                                "volume": float(candle_raw[5]),
                                "timeframe": tf
                            }
                            
                            # 緩存最新數據
                            cache_key = f"{symbol}_{tf}"
                            self.latest_data[cache_key] = kline_data
                            self.last_update_time = datetime.now()
                            self.update_count += 1
                            
                            # 廣播數據
                            self.broadcast_to_clients({
                                "type": "KLINE_UPDATE",
                                "data": kline_data
                            })
                            
                            logger.info(f"🔄 真實K線更新: {symbol} - ${kline_data['close']:.2f}")
                            
                            # 真實數據到達時，禁用模擬數據
                            if self.enable_mock_updates:
                                self.enable_mock_updates = False
                                logger.info("🔄 切換到真實數據，停用模擬數據")
                            
            except Exception as e:
                logger.error(f"WebSocket消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"❌ WebSocket錯誤: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.warning("⚠️ WebSocket連接關閉，5秒後重連...")
            if self.running:
                time.sleep(5)
                self.start_websocket_connection(symbols, timeframe)
        
        def on_open(ws):
            logger.info("✅ WebSocket連接建立成功")
            
            # 訂閱數據
            subscriptions = []
            for symbol in symbols:
                okx_symbol = symbol.replace('/', '-')
                subscriptions.append({
                    "channel": f"candle{timeframe}",
                    "instId": okx_symbol
                })
            
            subscribe_msg = {
                "op": "subscribe",
                "args": subscriptions
            }
            
            ws.send(json.dumps(subscribe_msg))
            logger.info(f"📡 已發送訂閱請求: {subscriptions}")
        
        try:
            websocket.enableTrace(True)  # 啟用調試
            self.ws_connection = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # 在背景執行
            ws_thread = threading.Thread(target=self.ws_connection.run_forever, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"❌ WebSocket啟動失敗: {e}")
    
    def broadcast_to_clients(self, message):
        """廣播消息到所有客戶端 (模擬功能)"""
        # 在真實的WebSocket實現中，這裡會推送到所有連接的客戶端
        logger.debug(f"廣播消息: {message['type']}")
    
    def get_system_status(self):
        """獲取系統狀態"""
        return {
            "running": self.running,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "update_count": self.update_count,
            "cached_symbols": list(self.latest_data.keys()),
            "mock_mode": self.enable_mock_updates,
            "websocket_connected": self.ws_connection is not None
        }


# 全局服務器實例
improved_server = ImprovedKlineServer()


class ImprovedRequestHandler(BaseHTTPRequestHandler):
    """改進的HTTP請求處理器"""
    
    def log_message(self, format, *args):
        """自定義日誌"""
        logger.info(f"HTTP {self.command} {self.path}")
    
    def do_OPTIONS(self):
        """處理 CORS 預檢請求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """發送 CORS 標頭"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_GET(self):
        """處理 GET 請求"""
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)
            
            if path == '/health':
                # 健康檢查 + 系統狀態
                status = improved_server.get_system_status()
                self.send_json_response({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "AutoTrading Backend is running",
                    "system_status": status
                })
                
            elif path == '/api/historical':
                # 獲取歷史數據
                symbol = params.get('symbol', ['BTC/USDT'])[0]
                timeframe = params.get('timeframe', ['5m'])[0]
                limit = int(params.get('limit', ['100'])[0])
                
                klines = improved_server.get_historical_klines(symbol, timeframe, limit)
                
                self.send_json_response({
                    "success": True,
                    "data": klines,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(klines)
                })
                
            elif path.startswith('/api/price/'):
                # 獲取當前價格
                symbol_parts = path.replace('/api/price/', '').split('/')
                if len(symbol_parts) >= 2:
                    symbol = f"{symbol_parts[0]}/{symbol_parts[1]}"
                else:
                    symbol = 'BTC/USDT'
                
                price_data = improved_server.get_current_price(symbol)
                
                if price_data:
                    self.send_json_response({
                        "success": True,
                        "data": price_data
                    })
                else:
                    self.send_json_response({
                        "success": False,
                        "error": "Failed to fetch price data"
                    }, status_code=500)
            
            elif path == '/api/latest':
                # 獲取最新實時數據 + 系統狀態
                status = improved_server.get_system_status()
                self.send_json_response({
                    "success": True,
                    "data": improved_server.latest_data,
                    "system_status": status
                })
            
            elif path == '/api/status':
                # 詳細系統狀態
                status = improved_server.get_system_status()
                self.send_json_response({
                    "success": True,
                    "status": status
                })
            
            else:
                self.send_json_response({
                    "error": "Not found"
                }, status_code=404)
                
        except Exception as e:
            logger.error(f"GET 請求處理錯誤: {e}")
            self.send_json_response({
                "error": str(e)
            }, status_code=500)
    
    def do_POST(self):
        """處理 POST 請求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            if self.path == '/api/subscribe':
                # 訂閱實時數據
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    symbols = data.get('symbols', ['BTC/USDT'])
                    timeframe = data.get('timeframe', '5m')
                    
                    improved_server.start_realtime_data(symbols, timeframe)
                    
                    self.send_json_response({
                        "success": True,
                        "message": f"已訂閱 {len(symbols)} 個交易對的實時數據",
                        "note": "系統會先使用模擬數據，收到真實數據後自動切換"
                    })
                    
                except json.JSONDecodeError:
                    self.send_json_response({
                        "error": "Invalid JSON"
                    }, status_code=400)
            
            else:
                self.send_json_response({
                    "error": "Not found"
                }, status_code=404)
                
        except Exception as e:
            logger.error(f"POST 請求處理錯誤: {e}")
            self.send_json_response({
                "error": str(e)
            }, status_code=500)
    
    def send_json_response(self, data, status_code=200):
        """發送 JSON 回應"""
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))


def run_improved_server(port=8001):
    """運行改進版服務器"""
    server = HTTPServer(('0.0.0.0', port), ImprovedRequestHandler)
    logger.info(f"🚀 改進版 AutoTrading Backend 啟動於 http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 服務器關閉")
        improved_server.running = False
        if improved_server.ws_connection:
            improved_server.ws_connection.close()


if __name__ == "__main__":
    # 配置日誌
    logger.add("improved_backend.log", rotation="1 day", retention="3 days", level="DEBUG")
    
    # 測試 OKX API 連接
    try:
        ticker = improved_server.okx_client.fetch_ticker('BTC/USDT')
        logger.info(f"✅ OKX API 連接正常，BTC 當前價格: {ticker['last']}")
    except Exception as e:
        logger.error(f"❌ OKX API 連接失敗: {e}")
    
    # 啟動服務器
    run_improved_server(port=8001)