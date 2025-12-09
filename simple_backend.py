#!/usr/bin/env python3
"""
簡化版後端服務
使用基本的 HTTP 服務器提供 K線數據
"""

import json
import asyncio
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import websocket
import ccxt
from loguru import logger

class KlineServer:
    """K線數據服務器"""
    
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
        
        logger.info("KlineServer 初始化完成")
    
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
        """啟動實時數據推送"""
        if self.running:
            return
            
        self.running = True
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                
                if 'data' in data and 'arg' in data:
                    channel = data['arg']['channel']
                    inst_id = data['arg']['instId']
                    symbol = inst_id.replace('-', '/')
                    
                    if channel.startswith('candle'):
                        # 處理K線數據
                        for candle_raw in data['data']:
                            kline_data = {
                                "symbol": symbol,
                                "time": int(candle_raw[0]) // 1000,
                                "open": float(candle_raw[1]),
                                "high": float(candle_raw[2]),
                                "low": float(candle_raw[3]),
                                "close": float(candle_raw[4]),
                                "volume": float(candle_raw[5]),
                                "timeframe": channel.replace('candle', '')
                            }
                            
                            # 緩存最新數據
                            self.latest_data[f"{symbol}_{timeframe}"] = kline_data
                            logger.info(f"實時K線: {symbol} - 價格: {kline_data['close']}")
                            
            except Exception as e:
                logger.error(f"WebSocket 消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket 錯誤: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket 連接關閉")
            if self.running:
                logger.info("3秒後重連...")
                threading.Timer(3.0, self.start_realtime_data, args=[symbols, timeframe]).start()
        
        def on_open(ws):
            logger.info("WebSocket 連接建立")
            
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
            logger.info(f"已訂閱 {len(subscriptions)} 個K線頻道")
        
        try:
            websocket.enableTrace(False)
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
            
            logger.info("實時數據推送已啟動")
            
        except Exception as e:
            logger.error(f"啟動WebSocket失敗: {e}")


# 全局 K線服務器實例
kline_server = KlineServer()


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP 請求處理器"""
    
    def log_message(self, format, *args):
        """禁用默認日誌"""
        pass
    
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
                self.send_json_response({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "AutoTrading Backend is running"
                })
                
            elif path == '/api/historical':
                # 獲取歷史數據
                symbol = params.get('symbol', ['BTC/USDT'])[0]
                timeframe = params.get('timeframe', ['5m'])[0]
                limit = int(params.get('limit', ['100'])[0])
                
                klines = kline_server.get_historical_klines(symbol, timeframe, limit)
                
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
                
                price_data = kline_server.get_current_price(symbol)
                
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
                # 獲取最新實時數據
                self.send_json_response({
                    "success": True,
                    "data": kline_server.latest_data
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
                    
                    kline_server.start_realtime_data(symbols, timeframe)
                    
                    self.send_json_response({
                        "success": True,
                        "message": f"已訂閱 {len(symbols)} 個交易對的實時數據"
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
        json_data = json.dumps(data, ensure_ascii=False)
        
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))


def run_server(port=8000):
    """運行服務器"""
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    logger.info(f"🚀 AutoTrading Backend 啟動於 http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 服務器關閉")
        kline_server.running = False
        if kline_server.ws_connection:
            kline_server.ws_connection.close()


if __name__ == "__main__":
    # 配置日誌
    logger.add("backend.log", rotation="1 day", retention="3 days")
    
    # 測試 OKX API 連接
    try:
        ticker = kline_server.okx_client.fetch_ticker('BTC/USDT')
        logger.info(f"✅ OKX API 連接正常，BTC 當前價格: {ticker['last']}")
    except Exception as e:
        logger.error(f"❌ OKX API 連接失敗: {e}")
    
    # 啟動服務器
    run_server(port=8000)