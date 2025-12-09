#!/usr/bin/env python3
"""
完整系統測試腳本
測試 OKX API -> 後端 -> 前端 的完整數據流
"""

import asyncio
import json
import time
import requests
import websocket
import threading
from loguru import logger

class FullSystemTest:
    """完整系統測試類"""
    
    def __init__(self):
        """初始化測試環境"""
        self.backend_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.ws_connection = None
        self.received_messages = []
        self.test_running = True
        
        logger.info("系統測試初始化完成")
    
    def test_rest_endpoints(self):
        """測試 REST API 端點"""
        logger.info("=== 測試 REST API 端點 ===")
        
        try:
            # 1. 測試健康檢查
            logger.info("1. 測試健康檢查...")
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ 健康檢查: {health_data['status']}")
                logger.info(f"   OKX API: {health_data['okx_api']}")
            else:
                logger.error(f"❌ 健康檢查失敗: {response.status_code}")
                return False
            
            # 2. 測試獲取歷史數據
            logger.info("2. 測試獲取歷史數據...")
            payload = {
                "symbol": "BTC/USDT",
                "timeframe": "5m",
                "limit": 20
            }
            response = requests.post(
                f"{self.backend_url}/api/historical",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success'] and data['data']:
                    logger.info(f"✅ 歷史數據: 獲取到 {data['count']} 根K線")
                    # 顯示最新的數據
                    latest = data['data'][-1]
                    logger.info(f"   最新K線: 時間={latest['time']}, 收盤價={latest['close']}")
                else:
                    logger.error("❌ 歷史數據: 數據為空")
                    return False
            else:
                logger.error(f"❌ 歷史數據失敗: {response.status_code}")
                return False
            
            # 3. 測試獲取當前價格
            logger.info("3. 測試獲取當前價格...")
            response = requests.get(f"{self.backend_url}/api/price/BTC/USDT", timeout=10)
            if response.status_code == 200:
                price_data = response.json()
                if price_data['success']:
                    data = price_data['data']
                    logger.info(f"✅ 當前價格: {data['price']} USDT")
                    logger.info(f"   24h變化: {data['change_percent_24h']:.2f}%")
                else:
                    logger.error("❌ 價格數據: 獲取失敗")
                    return False
            else:
                logger.error(f"❌ 價格數據失敗: {response.status_code}")
                return False
            
            # 4. 測試訂閱實時數據
            logger.info("4. 測試訂閱實時數據...")
            payload = {
                "symbols": ["BTC/USDT", "ETH/USDT"],
                "timeframe": "1m"
            }
            response = requests.post(
                f"{self.backend_url}/api/subscribe",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                sub_data = response.json()
                if sub_data['success']:
                    logger.info("✅ 實時數據訂閱成功")
                else:
                    logger.error("❌ 實時數據訂閱失敗")
                    return False
            else:
                logger.error(f"❌ 實時數據訂閱失敗: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"REST API 測試失敗: {e}")
            return False
    
    def test_websocket_connection(self, duration_seconds=30):
        """測試 WebSocket 連接和實時數據"""
        logger.info("=== 測試 WebSocket 實時數據 ===")
        
        self.received_messages = []
        self.test_running = True
        
        def on_message(ws, message):
            """處理 WebSocket 消息"""
            try:
                data = json.loads(message)
                self.received_messages.append(data)
                
                msg_type = data.get('type', 'UNKNOWN')
                
                if msg_type == 'CONNECTION_SUCCESS':
                    logger.info("✅ WebSocket 連接成功")
                elif msg_type == 'KLINE_UPDATE':
                    kline_data = data['data']
                    logger.info(f"📊 K線更新: {kline_data['symbol']} - 價格: {kline_data['close']}")
                elif msg_type == 'TICKER_UPDATE':
                    ticker_data = data['data']
                    logger.info(f"💰 價格更新: {ticker_data['symbol']} - 價格: {ticker_data['price']}")
                else:
                    logger.info(f"📨 收到消息: {msg_type}")
                    
            except Exception as e:
                logger.error(f"WebSocket 消息處理錯誤: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket 錯誤: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket 連接已關閉")
        
        def on_open(ws):
            logger.info("WebSocket 連接已建立，等待數據...")
            
            # 發送心跳
            def send_ping():
                while self.test_running:
                    try:
                        ws.send(json.dumps({"type": "ping"}))
                        time.sleep(10)
                    except:
                        break
            
            ping_thread = threading.Thread(target=send_ping, daemon=True)
            ping_thread.start()
        
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
            ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
            ws_thread.start()
            
            logger.info(f"WebSocket 測試運行 {duration_seconds} 秒...")
            
            # 等待指定時間
            start_time = time.time()
            while (time.time() - start_time) < duration_seconds and self.test_running:
                time.sleep(1)
            
            # 停止測試
            self.test_running = False
            ws.close()
            
            # 統計結果
            connection_msgs = len([msg for msg in self.received_messages if msg.get('type') == 'CONNECTION_SUCCESS'])
            kline_msgs = len([msg for msg in self.received_messages if msg.get('type') == 'KLINE_UPDATE'])
            ticker_msgs = len([msg for msg in self.received_messages if msg.get('type') == 'TICKER_UPDATE'])
            
            logger.info(f"WebSocket 測試完成:")
            logger.info(f"  📡 連接消息: {connection_msgs}")
            logger.info(f"  📊 K線消息: {kline_msgs}")
            logger.info(f"  💰 價格消息: {ticker_msgs}")
            logger.info(f"  📨 總消息數: {len(self.received_messages)}")
            
            # 成功條件：至少收到連接確認
            return connection_msgs > 0
            
        except Exception as e:
            logger.error(f"WebSocket 測試失敗: {e}")
            return False
    
    def run_full_test(self):
        """運行完整系統測試"""
        logger.info("🚀 開始完整系統測試")
        logger.info("=" * 60)
        
        results = {}
        
        # 測試 REST API
        logger.info("第一階段：REST API 功能測試")
        results['rest_api'] = self.test_rest_endpoints()
        
        if not results['rest_api']:
            logger.error("REST API 測試失敗，跳過後續測試")
            return False
        
        # 等待一下讓訂閱生效
        logger.info("等待 5 秒讓實時數據訂閱生效...")
        time.sleep(5)
        
        # 測試 WebSocket
        logger.info("第二階段：WebSocket 實時數據測試")
        results['websocket'] = self.test_websocket_connection(duration_seconds=30)
        
        # 總結報告
        logger.info("=" * 60)
        logger.info("📋 測試結果總結:")
        for test_name, result in results.items():
            status = "✅ 通過" if result else "❌ 失敗"
            logger.info(f"  {test_name}: {status}")
        
        all_passed = all(results.values())
        if all_passed:
            logger.info("🎉 完整系統測試通過！")
            logger.info("💡 系統已就緒，可以啟動前端進行完整演示")
        else:
            logger.error("⚠️  部分測試失敗，請檢查系統配置")
        
        return all_passed


def check_backend_status():
    """檢查後端是否運行"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    # 配置日誌
    logger.add("system_test.log", rotation="1 MB")
    
    print("🔍 AutoTrading 完整系統測試")
    print("=" * 50)
    
    # 檢查後端狀態
    if not check_backend_status():
        print("❌ 後端服務未運行，請先啟動後端:")
        print("   cd backend && python main.py")
        exit(1)
    
    # 執行測試
    tester = FullSystemTest()
    success = tester.run_full_test()
    
    if success:
        print("\n✅ 完整系統測試通過！")
        print("🎯 接下來可以:")
        print("   1. 啟動前端: cd frontend && npm run dev")
        print("   2. 打開瀏覽器查看 K線圖表")
        print("   3. 觀察實時數據更新")
    else:
        print("\n❌ 系統測試失敗，請檢查配置")
    
    print(f"\n📝 詳細測試日誌請查看: system_test.log")