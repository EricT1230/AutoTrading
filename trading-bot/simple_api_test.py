"""
Simple OKX API test
"""

import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

def test_api():
    print("Testing OKX API...")
    
    api_key = os.getenv('OKX_API_KEY', '')
    secret_key = os.getenv('OKX_SECRET_KEY', '')
    passphrase = os.getenv('OKX_PASSPHRASE', '')
    
    if not all([api_key, secret_key, passphrase]):
        print("ERROR: Missing API credentials")
        return False
    
    try:
        exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,  # OKX uses 'password' for passphrase
            'sandbox': False,  # production
            'enableRateLimit': True,
        })
        
        # Test market data
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"SUCCESS: BTC/USDT = ${ticker['last']:.2f}")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    print(f"API Test: {'PASS' if success else 'FAIL'}")