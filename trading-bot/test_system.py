"""
系統測試腳本
測試實時K線系統的各個組件功能
"""

import sys
import os
from pathlib import Path
import asyncio
import time

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_dependencies():
    """測試依賴包"""
    print("🔍 測試依賴包...")
    
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'ccxt', 
        'loguru', 'aiohttp', 'requests', 'numpy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少依賴包: {', '.join(missing_packages)}")
        return False
    
    print("✅ 所有核心依賴包已安裝")
    return True

def test_websocket_packages():
    """測試WebSocket相關包"""
    print("\n🌐 測試WebSocket包...")
    
    try:
        import websockets
        print("✅ websockets 包可用")
        return True
    except ImportError:
        print("⚠️ websockets 包未安裝，嘗試備用方案...")
        
        try:
            import websocket
            print("✅ websocket-client 包可用 (備用)")
            return True
        except ImportError:
            print("❌ 所有WebSocket包都未安裝")
            return False

def test_api_connection():
    """測試API連接"""
    print("\n📡 測試API連接...")
    
    try:
        from web.components.market_data_provider import MarketDataProvider
        
        async def test_okx_api():
            provider = MarketDataProvider()
            try:
                ticker = await provider.fetch_okx_ticker("BTC-USDT")
                await provider.close_session()
                
                if ticker and 'last_price' in ticker:
                    print(f"✅ OKX API連接成功，BTC價格: ${ticker['last_price']:,.2f}")
                    return True
                else:
                    print("❌ OKX API響應無效")
                    return False
                    
            except Exception as e:
                print(f"❌ OKX API連接失敗: {e}")
                await provider.close_session()
                return False
        
        # 運行異步測試
        result = asyncio.run(test_okx_api())
        return result
        
    except Exception as e:
        print(f"❌ API測試初始化失敗: {e}")
        return False

def test_kline_data():
    """測試K線數據獲取"""
    print("\n📊 測試K線數據獲取...")
    
    try:
        from web.components.market_data_provider import MarketDataProvider
        
        async def test_kline_fetch():
            provider = MarketDataProvider()
            try:
                klines = await provider.fetch_okx_klines("BTC-USDT", "5m", 10)
                await provider.close_session()
                
                if klines is not None and not klines.empty:
                    print(f"✅ 成功獲取K線數據，{len(klines)}條記錄")
                    latest = klines.iloc[-1]
                    print(f"   最新價格: ${latest['close']:,.2f}")
                    return True
                else:
                    print("❌ K線數據為空")
                    return False
                    
            except Exception as e:
                print(f"❌ K線數據獲取失敗: {e}")
                await provider.close_session()
                return False
        
        result = asyncio.run(test_kline_fetch())
        return result
        
    except Exception as e:
        print(f"❌ K線測試初始化失敗: {e}")
        return False

def test_realtime_engine():
    """測試實時K線引擎"""
    print("\n⚡ 測試實時K線引擎...")
    
    try:
        from web.components.realtime_kline_engine import RealtimeKlineEngine
        
        engine = RealtimeKlineEngine()
        print("✅ 實時K線引擎初始化成功")
        
        # 測試數據存儲
        test_kline = {
            'timestamp': pd.Timestamp.now(),
            'open': 45000.0,
            'high': 45100.0,
            'low': 44900.0,
            'close': 45050.0,
            'volume': 100.0,
            'is_confirmed': True
        }
        
        # 模擬數據更新
        asyncio.run(engine._update_kline_dataframe('BTC/USDT', '5m', test_kline))
        
        # 檢查數據是否正確存儲
        data = engine.get_latest_klines('BTC/USDT', '5m', 1)
        if data is not None and not data.empty:
            print("✅ 數據存儲和檢索功能正常")
            return True
        else:
            print("❌ 數據存儲測試失敗")
            return False
            
    except Exception as e:
        print(f"❌ 實時引擎測試失敗: {e}")
        return False

def test_chart_components():
    """測試圖表組件"""
    print("\n📈 測試圖表組件...")
    
    try:
        import plotly.graph_objects as go
        import pandas as pd
        
        # 創建測試數據
        dates = pd.date_range('2024-01-01', periods=10, freq='5min')
        test_data = pd.DataFrame({
            'open': range(100, 110),
            'high': range(101, 111),
            'low': range(99, 109),
            'close': range(100, 110),
            'volume': range(50, 60)
        }, index=dates)
        
        # 創建圖表
        fig = go.Figure(data=[
            go.Candlestick(
                x=test_data.index,
                open=test_data['open'],
                high=test_data['high'],
                low=test_data['low'],
                close=test_data['close']
            )
        ])
        
        if fig and fig.data:
            print("✅ 圖表組件功能正常")
            return True
        else:
            print("❌ 圖表創建失敗")
            return False
            
    except Exception as e:
        print(f"❌ 圖表測試失敗: {e}")
        return False

def test_error_handling():
    """測試錯誤處理"""
    print("\n🛡️ 測試錯誤處理...")
    
    try:
        from web.components.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # 測試錯誤記錄
        test_error = Exception("Test error")
        result = handler.handle_error(test_error, "Test Context", show_user=False)
        
        # 檢查錯誤是否被記錄
        stats = handler.get_error_stats()
        if "Test Context:Exception" in stats:
            print("✅ 錯誤處理和記錄功能正常")
            return True
        else:
            print("❌ 錯誤記錄測試失敗")
            return False
            
    except Exception as e:
        print(f"❌ 錯誤處理測試失敗: {e}")
        return False

def test_environment_config():
    """測試環境配置"""
    print("\n⚙️ 測試環境配置...")
    
    try:
        # 檢查 .env 文件
        env_file = project_root / '.env'
        if env_file.exists():
            print("✅ .env 配置文件存在")
            
            # 檢查必要的環境變數
            import os
            from dotenv import load_dotenv
            
            load_dotenv(env_file)
            
            required_vars = ['OKX_API_KEY', 'OKX_SECRET_KEY', 'OKX_PASSPHRASE']
            missing_vars = []
            
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"⚠️ 缺少環境變數: {', '.join(missing_vars)}")
                return False
            else:
                print("✅ 所有必要環境變數已配置")
                return True
        else:
            print("❌ .env 配置文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ 環境配置測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始系統測試...")
    print("=" * 50)
    
    test_results = {
        "依賴包": test_dependencies(),
        "WebSocket包": test_websocket_packages(),
        "環境配置": test_environment_config(),
        "API連接": test_api_connection(),
        "K線數據": test_kline_data(),
        "實時引擎": test_realtime_engine(),
        "圖表組件": test_chart_components(),
        "錯誤處理": test_error_handling()
    }
    
    print("\n" + "=" * 50)
    print("📋 測試結果總結:")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results.items():
        if result:
            print(f"✅ {test_name}: 通過")
            passed += 1
        else:
            print(f"❌ {test_name}: 失敗")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 總計: {passed} 通過, {failed} 失敗")
    
    if failed == 0:
        print("🎉 所有測試通過！系統準備就緒！")
        print("\n🚀 下一步:")
        print("1. 運行: python run_realtime_kline.py")
        print("2. 或運行: streamlit run web/main_app.py")
        print("3. 訪問: http://localhost:8501")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查上述錯誤信息")
        print("\n🔧 建議:")
        if not test_results["依賴包"]:
            print("- 運行: python install_dependencies.py")
        if not test_results["環境配置"]:
            print("- 檢查 .env 文件配置")
        if not test_results["API連接"]:
            print("- 檢查網路連接和API密鑰")
        return False

if __name__ == "__main__":
    # 確保能導入pandas（實時引擎測試需要）
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas 未安裝，無法運行完整測試")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1)