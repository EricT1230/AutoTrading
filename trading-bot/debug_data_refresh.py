"""
數據刷新診斷腳本
直接測試市場數據提供者是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.components.market_data_provider import (
    MarketDataProvider, 
    get_live_ticker_data, 
    get_live_kline_data,
    realtime_manager
)

async def test_market_data():
    """測試市場數據功能"""
    print("[DEBUG] 開始診斷數據刷新問題...")
    print("=" * 50)
    
    provider = MarketDataProvider()
    
    try:
        # 測試 1: OKX API 連接
        print("[TEST 1] OKX API 連接")
        ticker = await provider.fetch_okx_ticker("BTC-USDT")
        if ticker:
            print(f"[OK] OKX API 正常 - BTC價格: ${ticker['last_price']:,.2f}")
            print(f"     變化: {ticker['change_24h']:+.2f}%")
            print(f"     時間戳: {ticker['timestamp']}")
        else:
            print("[ERROR] OKX API 連接失敗")
        
        print()
        
        # 測試 2: K線數據
        print("📈 測試 2: K線數據")
        klines = await provider.fetch_okx_klines("BTC-USDT", "5m", 5)
        if klines is not None and not klines.empty:
            print(f"✅ K線數據正常 - 獲取 {len(klines)} 條記錄")
            print(f"   最新價格: ${klines['close'].iloc[-1]:,.2f}")
            print(f"   最新時間: {klines.index[-1]}")
        else:
            print("❌ K線數據獲取失敗")
        
        print()
        
        # 測試 3: 多交易對
        print("💹 測試 3: 多交易對數據")
        symbols = ['BTC/USDT', 'ETH/USDT']
        tickers = await provider.fetch_multiple_tickers(symbols)
        if tickers:
            print(f"✅ 多交易對數據正常 - 獲取 {len(tickers)} 個交易對")
            for symbol, data in tickers.items():
                print(f"   {symbol}: ${data['last_price']:,.2f} ({data['change_24h']:+.2f}%)")
        else:
            print("❌ 多交易對數據獲取失敗")
        
        print()
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
    finally:
        await provider.close_session()
    
    print("=" * 50)
    
    # 測試 4: Streamlit 快取函數
    print("🔄 測試 4: Streamlit 快取函數")
    
    try:
        # 直接測試快取函數（不在Streamlit環境中）
        import time
        
        print("⏱️  測試數據獲取速度...")
        start_time = time.time()
        
        # 模擬調用（但這些函數需要Streamlit環境）
        print("   注意: 快取函數需要在Streamlit環境中運行")
        print("   在瀏覽器中應該能看到實際數據")
        
        elapsed = time.time() - start_time
        print(f"   測試完成，耗時: {elapsed:.2f}秒")
        
    except Exception as e:
        print(f"⚠️  快取函數測試警告: {e}")
    
    print()
    
    # 測試 5: WebSocket 狀態
    print("🌐 測試 5: WebSocket 狀態")
    try:
        if hasattr(realtime_manager, 'latest_data'):
            if realtime_manager.latest_data:
                print(f"✅ WebSocket 數據可用 - {len(realtime_manager.latest_data)} 個交易對")
                for symbol, data in realtime_manager.latest_data.items():
                    print(f"   {symbol}: ${data['last_price']:,.2f}")
            else:
                print("⚠️  WebSocket 已連接但暫無數據")
        else:
            print("❓ WebSocket 狀態未知")
    except Exception as e:
        print(f"❌ WebSocket 狀態檢查失敗: {e}")
    
    print()
    print("🎯 診斷建議:")
    print("1. 如果所有API測試都成功，問題可能在Streamlit快取或UI更新")
    print("2. 如果API失敗，檢查網路連接和API限制")
    print("3. 如果WebSocket無數據，檢查防火牆設定")
    print("4. 在瀏覽器中檢查控制台是否有錯誤信息")

if __name__ == "__main__":
    asyncio.run(test_market_data())