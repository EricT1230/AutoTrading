#!/usr/bin/env python3
"""
OKX API K線數據測試腳本
測試K線數據獲取和實時更新功能
"""

import asyncio
import pandas as pd
import ccxt
import json
import websocket
import threading
from datetime import datetime
import time
from loguru import logger

class OKXKlineTest:
    """OKX K線數據測試類"""
    
    def __init__(self):
        """初始化測試環境"""
        # 使用無需API KEY的公開數據
        self.client = ccxt.okx({
            'sandbox': False,  # 使用正式環境的公開數據
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # WebSocket 配置
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_connection = None
        
        logger.info("OKX K線數據測試初始化完成")
    
    def test_rest_api_kline(self):
        """測試 REST API 獲取K線數據"""
        logger.info("=== 測試 REST API K線數據獲取 ===")
        
        try:
            # 測試參數
            symbol = 'BTC/USDT'
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
            limit = 10
            
            for timeframe in timeframes:
                logger.info(f"獲取 {symbol} {timeframe} K線數據...")
                
                # 獲取數據
                ohlcv = self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                # 轉換為 DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                
                # 時間戳轉換
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['datetime'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                logger.info(f"獲取到 {len(df)} 根K線")
                logger.info(f"最新數據: {df.iloc[-1]['datetime']} - 收盤價: {df.iloc[-1]['close']}")
                
                # 顯示數據樣本
                print(f"\n{timeframe} K線數據 (最近5根):")
                print(df[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail().to_string(index=False))
                print("-" * 80)
                
                time.sleep(0.5)  # 避免請求過於頻繁
                
        except Exception as e:
            logger.error(f"REST API測試失敗: {e}")
            return False
            
        return True
    
    def test_websocket_kline(self, duration_seconds=30):
        """測試 WebSocket 實時K線數據"""
        logger.info("=== 測試 WebSocket 實時K線數據 ===")
        
        self.ws_data_count = 0
        self.ws_running = True
        
        def on_message(ws, message):
            """處理 WebSocket 消息"""
            try:
                data = json.loads(message)
                
                # 檢查是否是K線數據
                if 'data' in data and 'arg' in data:
                    channel = data['arg'].get('channel', '')
                    if 'candle' in channel:
                        self.ws_data_count += 1
                        
                        # 解析K線數據
                        for candle_data in data['data']:
                            timestamp = int(candle_data[0])
                            dt = datetime.fromtimestamp(timestamp / 1000)
                            
                            kline_info = {
                                'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'open': float(candle_data[1]),
                                'high': float(candle_data[2]),
                                'low': float(candle_data[3]),
                                'close': float(candle_data[4]),
                                'volume': float(candle_data[5]),
                                'symbol': data['arg'].get('instId', ''),
                                'timeframe': channel.replace('candle', '')
                            }
                            
                            logger.info(f"實時K線: {kline_info['symbol']} {kline_info['timeframe']} - "
                                      f"{kline_info['time']} - 收盤價: {kline_info['close']}")
                            
            except Exception as e:
                logger.error(f"WebSocket消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket錯誤: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket連接關閉")
        
        def on_open(ws):
            logger.info("WebSocket連接已建立")
            
            # 訂閱多個K線頻道
            subscriptions = [
                {
                    "op": "subscribe",
                    "args": [
                        {"channel": "candle1m", "instId": "BTC-USDT"},
                        {"channel": "candle5m", "instId": "BTC-USDT"},
                        {"channel": "candle1m", "instId": "ETH-USDT"}
                    ]
                }
            ]
            
            for sub in subscriptions:
                ws.send(json.dumps(sub))
                logger.info(f"訂閱頻道: {sub['args']}")
        
        try:
            # 創建 WebSocket 連接
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # 在背景執行
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            logger.info(f"WebSocket測試運行 {duration_seconds} 秒...")
            time.sleep(duration_seconds)
            
            # 停止連接
            self.ws_running = False
            ws.close()
            
            logger.info(f"WebSocket測試完成，共接收到 {self.ws_data_count} 筆數據")
            
            return self.ws_data_count > 0
            
        except Exception as e:
            logger.error(f"WebSocket測試失敗: {e}")
            return False
    
    def test_market_data_complete(self):
        """完整的市場數據測試"""
        logger.info("=== 完整市場數據功能測試 ===")
        
        try:
            symbol = 'BTC/USDT'
            
            # 1. 獲取Ticker數據
            logger.info("1. 測試Ticker數據...")
            ticker = self.client.fetch_ticker(symbol)
            logger.info(f"當前價格: {ticker['last']}, 24h漲跌: {ticker['percentage']:.2f}%")
            
            # 2. 獲取訂單薄
            logger.info("2. 測試訂單薄數據...")
            orderbook = self.client.fetch_order_book(symbol, limit=5)
            logger.info(f"最佳買價: {orderbook['bids'][0][0]}, 最佳賣價: {orderbook['asks'][0][0]}")
            
            # 3. 獲取最近成交
            logger.info("3. 測試成交記錄...")
            trades = self.client.fetch_trades(symbol, limit=5)
            logger.info(f"最近成交價: {trades[-1]['price']}, 成交量: {trades[-1]['amount']}")
            
            # 4. 測試多種時間框架K線
            logger.info("4. 測試多時間框架K線...")
            timeframes = ['1m', '5m', '1h']
            for tf in timeframes:
                ohlcv = self.client.fetch_ohlcv(symbol, tf, limit=1)
                latest = ohlcv[-1]
                dt = datetime.fromtimestamp(latest[0] / 1000)
                logger.info(f"{tf} K線: {dt.strftime('%H:%M:%S')} - OHLC: {latest[1]:.1f}/{latest[2]:.1f}/{latest[3]:.1f}/{latest[4]:.1f}")
            
            return True
            
        except Exception as e:
            logger.error(f"市場數據測試失敗: {e}")
            return False
    
    def run_all_tests(self):
        """執行所有測試"""
        logger.info("開始 OKX API K線數據測試")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. REST API 測試
        results['rest_api'] = self.test_rest_api_kline()
        
        # 2. 市場數據完整測試
        results['market_data'] = self.test_market_data_complete()
        
        # 3. WebSocket 測試
        results['websocket'] = self.test_websocket_kline(duration_seconds=20)
        
        # 總結報告
        logger.info("=" * 60)
        logger.info("測試結果總結:")
        for test_name, result in results.items():
            status = "✅ 成功" if result else "❌ 失敗"
            logger.info(f"  {test_name}: {status}")
        
        all_passed = all(results.values())
        if all_passed:
            logger.info("🎉 所有測試通過！OKX API K線功能正常")
        else:
            logger.error("⚠️  部分測試失敗，請檢查網路連接和API配置")
        
        return all_passed


if __name__ == "__main__":
    # 配置日誌
    logger.add("okx_test.log", rotation="1 MB")
    
    # 執行測試
    tester = OKXKlineTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ OKX API 測試完成，K線數據功能正常！")
        print("接下來可以整合到前端顯示K線圖表。")
    else:
        print("\n❌ 測試過程中遇到問題，請檢查網路連接。")