#!/usr/bin/env python3
"""
真實 OKX 數據後端服務
使用正確的 WebSocket 訂閱格式獲取真實數據
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

class RealOKXServer:
    """真實 OKX 數據服務器"""
    
    def __init__(self):
        # 初始化 OKX 客戶端
        self.okx_client = ccxt.okx({
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # WebSocket 配置（使用正確的OKX端點）
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_connection = None
        self.latest_data = {}
        self.running = False
        self.last_update_time = None
        self.update_count = 0
        
        # 關閉模擬數據
        self.enable_mock_updates = False
        
        logger.info("RealOKXServer 初始化完成")
    
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
    
    def start_realtime_data(self, symbols=['BTC/USDT'], timeframe='5m'):
        """啟動真實實時數據推送"""
        if self.running:
            logger.info("實時數據已在運行中")
            return
            
        self.running = True
        logger.info(f"🚀 啟動真實 OKX 實時數據: {symbols}")
        
        # 啟動 WebSocket 連接
        self.start_websocket_connection(symbols, timeframe)
    
    def start_websocket_connection(self, symbols, timeframe):
        """啟動真實的 WebSocket 連接"""
        
        # OKX 時間框架映射
        timeframe_map = {
            '1m': '1m',
            '5m': '1m',    # OKX 沒有5m，使用1m代替
            '15m': '15m',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                logger.debug(f"收到WebSocket消息: {data}")
                
                # 處理訂閱確認
                if 'event' in data:
                    if data['event'] == 'subscribe':
                        logger.info(f"✅ 真實數據訂閱成功: {data.get('arg', {})}")
                    elif data['event'] == 'error':
                        logger.error(f"❌ 真實數據訂閱失敗: {data}")
                        # 如果訂閱失敗，我們仍使用REST API輪詢
                        self._fallback_to_polling(symbols, timeframe)
                    return
                
                # 處理K線數據推送
                if 'data' in data and 'arg' in data:
                    channel = data['arg']['channel']
                    inst_id = data['arg']['instId']
                    symbol = inst_id.replace('-', '/')
                    
                    if 'candle' in channel:
                        # 處理真實K線數據
                        tf = channel.replace('candle', '').replace('m', 'min').replace('H', 'h').replace('D', 'd')
                        
                        for candle_raw in data['data']:
                            kline_data = {
                                "symbol": symbol,
                                "time": int(candle_raw[0]) // 1000,
                                "open": float(candle_raw[1]),
                                "high": float(candle_raw[2]),
                                "low": float(candle_raw[3]),
                                "close": float(candle_raw[4]),
                                "volume": float(candle_raw[5]),
                                "timeframe": tf,
                                "source": "real_okx_ws"
                            }
                            
                            # 緩存最新數據
                            cache_key = f"{symbol}_{timeframe}"
                            self.latest_data[cache_key] = kline_data
                            self.last_update_time = datetime.now()
                            self.update_count += 1
                            
                            logger.info(f"🔄 真實K線更新: {symbol} - ${kline_data['close']:.2f} (來源: OKX WebSocket)")
                            
            except Exception as e:
                logger.error(f"真實WebSocket消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"❌ 真實WebSocket錯誤: {error}")
            # 錯誤時啟動輪詢備用方案
            self._fallback_to_polling(symbols, timeframe)
        
        def on_close(ws, close_status_code, close_msg):
            logger.warning("⚠️ 真實WebSocket連接關閉，5秒後重連...")
            if self.running:
                time.sleep(5)
                self.start_websocket_connection(symbols, timeframe)
        
        def on_open(ws):
            logger.info("✅ 真實WebSocket連接建立成功")
            
            try:
                # 使用正確的OKX訂閱格式
                okx_timeframe = timeframe_map.get(timeframe, '1m')
                
                for symbol in symbols:
                    okx_symbol = symbol.replace('/', '-')
                    
                    # 正確的OKX訂閱格式
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [
                            {
                                "channel": f"candle{okx_timeframe}",
                                "instId": okx_symbol
                            }
                        ]
                    }
                    
                    ws.send(json.dumps(subscribe_msg))
                    logger.info(f"📡 發送真實數據訂閱: candle{okx_timeframe} for {okx_symbol}")
                    
            except Exception as e:
                logger.error(f"發送訂閱消息失敗: {e}")
        
        try:
            websocket.enableTrace(True)
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
            
            logger.info("🔄 真實WebSocket線程已啟動")
            
        except Exception as e:
            logger.error(f"❌ 真實WebSocket啟動失敗: {e}")
            # 失敗時使用輪詢
            self._fallback_to_polling(symbols, timeframe)
    
    def _fallback_to_polling(self, symbols, timeframe):
        """WebSocket失敗時的REST API輪詢備用方案"""
        logger.info("🔄 啟動REST API輪詢作為備用方案")
        
        def polling_loop():
            while self.running:
                try:
                    for symbol in symbols:
                        # 使用REST API獲取最新數據
                        klines = self.get_historical_klines(symbol, timeframe, 1)
                        
                        if klines:
                            latest_kline = klines[-1]
                            latest_kline.update({
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "source": "rest_api_polling"
                            })
                            
                            # 緩存數據
                            cache_key = f"{symbol}_{timeframe}"
                            self.latest_data[cache_key] = latest_kline
                            self.last_update_time = datetime.now()
                            self.update_count += 1
                            
                            logger.info(f"🔄 REST輪詢更新: {symbol} - ${latest_kline['close']:.2f}")
                    
                    # 每60秒輪詢一次（比WebSocket慢，但穩定）
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"REST輪詢錯誤: {e}")
                    time.sleep(30)
        
        # 啟動輪詢線程
        polling_thread = threading.Thread(target=polling_loop, daemon=True)
        polling_thread.start()
    
    def get_system_status(self):
        """獲取系統狀態"""
        return {
            "running": self.running,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "update_count": self.update_count,
            "cached_symbols": list(self.latest_data.keys()),
            "mock_mode": False,  # 真實數據模式
            "websocket_connected": self.ws_connection is not None,
            "data_source": "real_okx"
        }


# 全局服務器實例
real_okx_server = RealOKXServer()


class RealRequestHandler(BaseHTTPRequestHandler):
    """真實數據HTTP請求處理器"""
    
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
                # 健康檢查
                status = real_okx_server.get_system_status()
                self.send_json_response({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Real OKX Backend is running",
                    "system_status": status
                })
                
            elif path == '/api/historical':
                # 獲取歷史數據
                symbol = params.get('symbol', ['BTC/USDT'])[0]
                timeframe = params.get('timeframe', ['5m'])[0]
                limit = int(params.get('limit', ['100'])[0])
                
                klines = real_okx_server.get_historical_klines(symbol, timeframe, limit)
                
                self.send_json_response({
                    "success": True,
                    "data": klines,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(klines),
                    "source": "real_okx_rest"
                })
                
            elif path.startswith('/api/price/'):
                # 獲取當前價格
                symbol_parts = path.replace('/api/price/', '').split('/')
                if len(symbol_parts) >= 2:
                    symbol = f"{symbol_parts[0]}/{symbol_parts[1]}"
                else:
                    symbol = 'BTC/USDT'
                
                price_data = real_okx_server.get_current_price(symbol)
                
                if price_data:
                    self.send_json_response({
                        "success": True,
                        "data": price_data,
                        "source": "real_okx_ticker"
                    })
                else:
                    self.send_json_response({
                        "success": False,
                        "error": "Failed to fetch real price data"
                    }, status_code=500)
            
            elif path == '/api/latest':
                # 獲取最新實時數據
                status = real_okx_server.get_system_status()
                self.send_json_response({
                    "success": True,
                    "data": real_okx_server.latest_data,
                    "system_status": status
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
                # 訂閱真實數據
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    symbols = data.get('symbols', ['BTC/USDT'])
                    timeframe = data.get('timeframe', '5m')
                    
                    real_okx_server.start_realtime_data(symbols, timeframe)
                    
                    self.send_json_response({
                        "success": True,
                        "message": f"已訂閱 {len(symbols)} 個交易對的真實OKX數據",
                        "note": "使用真實OKX WebSocket + REST API輪詢備用"
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


def run_real_server(port=8002):
    """運行真實OKX數據服務器"""
    server = HTTPServer(('0.0.0.0', port), RealRequestHandler)
    logger.info(f"🚀 真實 OKX Backend 啟動於 http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 真實OKX服務器關閉")
        real_okx_server.running = False
        if real_okx_server.ws_connection:
            real_okx_server.ws_connection.close()


if __name__ == "__main__":
    # 配置日誌
    logger.add("real_okx_backend.log", rotation="1 day", retention="3 days", level="INFO")
    
    # 測試 OKX API 連接
    try:
        ticker = real_okx_server.okx_client.fetch_ticker('BTC/USDT')
        logger.info(f"✅ 真實OKX API 連接正常，BTC 當前價格: {ticker['last']}")
    except Exception as e:
        logger.error(f"❌ 真實OKX API 連接失敗: {e}")
    
    # 啟動服務器
    run_real_server(port=8002)