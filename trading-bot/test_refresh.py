"""
測試數據刷新功能
"""

import time
import asyncio
from web.components.market_data_provider import MarketDataProvider, get_live_ticker_data

async def test_refresh_rate():
    """測試實際刷新頻率"""
    print("測試數據刷新頻率...")
    print("=" * 40)
    
    provider = MarketDataProvider()
    
    try:
        # 測試連續5次獲取，查看時間間隔
        for i in range(5):
            start_time = time.time()
            
            # 使用不同的_force_refresh值來強制更新
            ticker_data = get_live_ticker_data("BTC/USDT", _force_refresh=int(time.time()))
            
            end_time = time.time()
            elapsed = (end_time - start_time) * 1000  # 轉換為毫秒
            
            if ticker_data:
                print(f"第 {i+1} 次: BTC價格 ${ticker_data['last_price']:,.2f} - 耗時 {elapsed:.2f}ms")
            else:
                print(f"第 {i+1} 次: 獲取失敗 - 耗時 {elapsed:.2f}ms")
            
            # 等待1秒再進行下次測試
            if i < 4:  # 最後一次不需要等待
                time.sleep(1.0)
                
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        await provider.close_session()
    
    print("\n測試完成!")
    print("建議:")
    print("1. 如果每次獲取都很快(< 100ms)，說明數據刷新機制正常")
    print("2. 如果價格在每次獲取時都有變化，說明實時性良好")
    print("3. 啟動Web界面並啟用'自動刷新'來驗證實時更新")

if __name__ == "__main__":
    asyncio.run(test_refresh_rate())