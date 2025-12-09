#!/usr/bin/env python3
"""
快速 OKX 數據後端服務
優化更新頻率，支援不同時間框架的智能更新間隔
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

class FastOKXServer:
    """快速 OKX 數據服務器"""
    
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
        self.last_update_time = None
        self.update_count = 0
        
        # 智能更新間隔配置
        self.update_intervals = {
            '1m': 10,   # 1分鐘K線 - 每10秒更新
            '5m': 15,   # 5分鐘K線 - 每15秒更新  
            '15m': 30,  # 15分鐘K線 - 每30秒更新
            '1h': 60,   # 1小時K線 - 每60秒更新
            '4h': 120,  # 4小時K線 - 每2分鐘更新
            '1d': 300   # 1天K線 - 每5分鐘更新
        }
        
        self.current_symbols = []
        self.current_timeframe = '5m'
        
        logger.info("FastOKXServer 初始化完成 - 支援快速更新")
    
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
        """啟動快速實時數據推送"""
        if self.running:
            # 如果已在運行，停止舊的線程
            self.running = False
            time.sleep(2)
            
        self.running = True
        self.current_symbols = symbols
        self.current_timeframe = timeframe
        
        # 獲取對應時間框架的更新間隔
        update_interval = self.update_intervals.get(timeframe, 30)
        
        logger.info(f"🚀 啟動快速實時數據: {symbols} ({timeframe}) - 每 {update_interval} 秒更新")
        
        # 啟動快速輪詢
        self._start_fast_polling(symbols, timeframe, update_interval)
    
    def _start_fast_polling(self, symbols, timeframe, update_interval):
        """啟動快速輪詢機制"""
        
        def fast_polling_loop():
            logger.info(f"🔄 快速輪詢線程啟動 - 間隔 {update_interval} 秒")
            
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
                                "source": "fast_rest_polling",
                                "update_interval": update_interval
                            })
                            
                            # 緩存數據
                            cache_key = f"{symbol}_{timeframe}"
                            self.latest_data[cache_key] = latest_kline
                            self.last_update_time = datetime.now()
                            self.update_count += 1
                            
                            current_time = datetime.now().strftime("%H:%M:%S")
                            logger.info(f"⚡ 快速更新 #{self.update_count}: {symbol} - ${latest_kline['close']:.2f} [{current_time}]")
                    
                    # 根據時間框架決定更新間隔
                    time.sleep(update_interval)
                    
                except Exception as e:
                    logger.error(f"快速輪詢錯誤: {e}")
                    time.sleep(10)  # 錯誤時短暫等待
        
        # 啟動快速輪詢線程
        polling_thread = threading.Thread(target=fast_polling_loop, daemon=True)
        polling_thread.start()
        logger.info("✅ 快速輪詢線程已啟動")
    
    def get_system_status(self):
        """獲取系統狀態"""
        current_interval = self.update_intervals.get(self.current_timeframe, 30)
        
        return {
            "running": self.running,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "update_count": self.update_count,
            "cached_symbols": list(self.latest_data.keys()),
            "mock_mode": False,
            "data_source": "fast_okx_polling",
            "timeframe": self.current_timeframe,
            "update_interval_seconds": current_interval,
            "symbols": self.current_symbols,
            "performance": {
                "updates_per_minute": 60 / current_interval if current_interval > 0 else 0,
                "last_update_age_seconds": (datetime.now() - self.last_update_time).total_seconds() if self.last_update_time else None
            }
        }


# 全局服務器實例
fast_okx_server = FastOKXServer()


class FastRequestHandler(BaseHTTPRequestHandler):
    """快速數據HTTP請求處理器"""
    
    def log_message(self, format, *args):
        """簡化日誌，減少輸出"""
        if "GET /api/latest" not in self.path:  # 只記錄非輪詢請求
            logger.debug(f"HTTP {self.command} {self.path}")
    
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
                # 健康檢查 + 詳細狀態
                status = fast_okx_server.get_system_status()
                self.send_json_response({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Fast OKX Backend is running",
                    "system_status": status
                })
                
            elif path == '/api/historical':
                # 獲取歷史數據
                symbol = params.get('symbol', ['BTC/USDT'])[0]
                timeframe = params.get('timeframe', ['5m'])[0]
                limit = int(params.get('limit', ['100'])[0])
                
                klines = fast_okx_server.get_historical_klines(symbol, timeframe, limit)
                
                self.send_json_response({
                    "success": True,
                    "data": klines,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(klines),
                    "source": "fast_okx_rest"
                })
                
            elif path.startswith('/api/price/'):
                # 獲取當前價格
                symbol_parts = path.replace('/api/price/', '').split('/')
                if len(symbol_parts) >= 2:
                    symbol = f"{symbol_parts[0]}/{symbol_parts[1]}"
                else:
                    symbol = 'BTC/USDT'
                
                price_data = fast_okx_server.get_current_price(symbol)
                
                if price_data:
                    self.send_json_response({
                        "success": True,
                        "data": price_data,
                        "source": "fast_okx_ticker"
                    })
                else:
                    self.send_json_response({
                        "success": False,
                        "error": "Failed to fetch price data"
                    }, status_code=500)
            
            elif path == '/api/latest':
                # 獲取最新實時數據 (高頻調用，簡化日誌)
                status = fast_okx_server.get_system_status()
                self.send_json_response({
                    "success": True,
                    "data": fast_okx_server.latest_data,
                    "system_status": status
                })
            
            elif path == '/api/status':
                # 詳細系統狀態
                status = fast_okx_server.get_system_status()
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
                # 訂閱快速實時數據
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    symbols = data.get('symbols', ['BTC/USDT'])
                    timeframe = data.get('timeframe', '5m')
                    
                    # 重新啟動快速數據推送
                    fast_okx_server.start_realtime_data(symbols, timeframe)
                    
                    update_interval = fast_okx_server.update_intervals.get(timeframe, 30)
                    
                    self.send_json_response({
                        "success": True,
                        "message": f"已訂閱 {len(symbols)} 個交易對的快速數據",
                        "timeframe": timeframe,
                        "update_interval_seconds": update_interval,
                        "updates_per_minute": round(60 / update_interval, 1),
                        "note": f"快速模式：每 {update_interval} 秒更新"
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


def run_fast_server(port=8003):
    """運行快速OKX數據服務器"""
    server = HTTPServer(('0.0.0.0', port), FastRequestHandler)
    logger.info(f"⚡ 快速 OKX Backend 啟動於 http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 快速OKX服務器關閉")
        fast_okx_server.running = False


if __name__ == "__main__":
    # 配置日誌
    logger.add("fast_okx_backend.log", rotation="1 day", retention="3 days", level="INFO")
    
    # 顯示更新頻率設定
    print("⚡ 快速更新頻率設定:")
    for tf, interval in fast_okx_server.update_intervals.items():
        updates_per_min = round(60 / interval, 1)
        print(f"   {tf:>3} : 每 {interval:>2} 秒更新 ({updates_per_min:>3.1f} 次/分鐘)")
    
    # 測試 OKX API 連接
    try:
        ticker = fast_okx_server.okx_client.fetch_ticker('BTC/USDT')
        logger.info(f"✅ 快速OKX API 連接正常，BTC 當前價格: {ticker['last']}")
        print(f"✅ OKX API 連接正常，BTC 當前價格: ${ticker['last']}")
    except Exception as e:
        logger.error(f"❌ 快速OKX API 連接失敗: {e}")
        print(f"❌ OKX API 連接失敗: {e}")
    
    print(f"\n🚀 啟動快速後端服務於 http://localhost:8003")
    print("💡 不同時間框架會使用不同的更新頻率以優化性能")
    
    # 啟動服務器
    run_fast_server(port=8003)