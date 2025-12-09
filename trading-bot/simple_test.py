"""
Simple data refresh test - English only
"""

import asyncio
import sys
from pathlib import Path

# Add project path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.components.market_data_provider import MarketDataProvider

async def main():
    print("Starting data refresh test...")
    print("=" * 40)
    
    provider = MarketDataProvider()
    
    try:
        # Test OKX API
        print("Testing OKX API...")
        ticker = await provider.fetch_okx_ticker("BTC-USDT")
        
        if ticker:
            print(f"SUCCESS: BTC Price = ${ticker['last_price']:,.2f}")
            print(f"Change: {ticker['change_24h']:+.2f}%")
            print(f"Timestamp: {ticker['timestamp']}")
        else:
            print("FAILED: No ticker data received")
        
        print()
        
        # Test Klines
        print("Testing K-line data...")
        klines = await provider.fetch_okx_klines("BTC-USDT", "5m", 5)
        
        if klines is not None and not klines.empty:
            print(f"SUCCESS: Got {len(klines)} klines")
            print(f"Latest price: ${klines['close'].iloc[-1]:,.2f}")
        else:
            print("FAILED: No kline data")
        
        print()
        
        # Test multiple tickers
        print("Testing multiple tickers...")
        symbols = ['BTC/USDT', 'ETH/USDT']
        tickers = await provider.fetch_multiple_tickers(symbols)
        
        if tickers:
            print(f"SUCCESS: Got {len(tickers)} tickers")
            for symbol, data in tickers.items():
                print(f"  {symbol}: ${data['last_price']:,.2f}")
        else:
            print("FAILED: No multi-ticker data")
            
    except Exception as e:
        print(f"ERROR: {e}")
        
    finally:
        await provider.close_session()
    
    print("=" * 40)
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(main())