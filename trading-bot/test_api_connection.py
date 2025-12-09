"""
測試 OKX API 連接狀態
"""

import os
from dotenv import load_dotenv
from core.exchange_okx import OKXExchange

# 載入環境變數
load_dotenv()

def test_okx_connection():
    """測試 OKX API 連接"""
    print("測試 OKX API 連接...")
    print("=" * 40)
    
    # 獲取環境變數
    api_key = os.getenv('OKX_API_KEY', '')
    secret_key = os.getenv('OKX_SECRET_KEY', '')
    passphrase = os.getenv('OKX_PASSPHRASE', '')
    testnet = os.getenv('OKX_TESTNET', 'false').lower() == 'true'
    
    print(f"API Key: {api_key[:8]}...{api_key[-8:] if len(api_key) > 16 else api_key}")
    print(f"Secret: {'***已設置***' if secret_key else '未設置'}")
    print(f"Passphrase: {'***已設置***' if passphrase else '未設置'}")
    print(f"測試網: {testnet}")
    print()
    
    if not all([api_key, secret_key, passphrase]):
        print("❌ API 憑證不完整")
        return False
    
    try:
        # 初始化交易所
        config = {
            'api_key': api_key,
            'secret_key': secret_key,
            'passphrase': passphrase,
            'testnet': testnet
        }
        
        print("正在初始化 OKX Exchange...")
        exchange = OKXExchange(config)
        print("✅ OKX Exchange 初始化成功")
        
        # 測試基本API調用
        print("正在測試 API 連接...")
        
        # 使用 ccxt 客戶端測試連接
        if hasattr(exchange, 'client'):
            try:
                # 測試獲取市場數據（不需要認證）
                tickers = exchange.client.fetch_ticker('BTC/USDT')
                if tickers:
                    print(f"✅ 市場數據獲取成功 - BTC/USDT: ${tickers['last']:,.2f}")
                    return True
                else:
                    print("❌ 市場數據為空")
                    return False
                    
            except Exception as e:
                print(f"❌ API 調用失敗: {e}")
                return False
        else:
            print("❌ ccxt 客戶端未初始化")
            return False
            
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_okx_connection()
    print()
    if success:
        print("🎉 API 連接測試通過！")
    else:
        print("💥 API 連接測試失敗")
        print("\n排除建議:")
        print("1. 檢查網路連接")
        print("2. 驗證 API 憑證是否正確")
        print("3. 確認 API 權限設置")
        print("4. 檢查是否超出API調用限制")