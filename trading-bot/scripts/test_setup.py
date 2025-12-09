"""
測試腳本：驗證環境設置和核心模組

這個腳本會測試：
1. 所有依賴套件是否正確安裝
2. 核心模組是否可以正常導入
3. 基本功能是否運作
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """測試所有重要的套件導入"""
    print("🔍 測試套件導入...")
    
    try:
        import pandas as pd
        print("✅ pandas")
        
        import numpy as np  
        print("✅ numpy")
        
        import ccxt
        print("✅ ccxt")
        
        import yaml
        print("✅ PyYAML")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv")
        
        from loguru import logger
        print("✅ loguru")
        
        import matplotlib.pyplot as plt
        print("✅ matplotlib")
        
        import seaborn as sns
        print("✅ seaborn")
        
        import plotly.express as px
        print("✅ plotly")
        
        print("✅ 所有核心套件導入成功！")
        return True
        
    except ImportError as e:
        print(f"❌ 套件導入失敗: {e}")
        return False

def test_core_modules():
    """測試核心模組"""
    print("\n🔍 測試核心模組...")
    
    try:
        from core.strategy_base import StrategyBase, TradingSignal, SignalType
        print("✅ strategy_base")
        
        from core.exchange_base import ExchangeBase, OrderType, OrderSide
        print("✅ exchange_base")
        
        from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
        print("✅ strategy_ict_ny_fvg")
        
        from core.risk import RiskManager, RiskLimits
        print("✅ risk")
        
        from core.utils_logging import setup_logging, get_logger
        print("✅ utils_logging")
        
        print("✅ 所有核心模組導入成功！")
        return True
        
    except ImportError as e:
        print(f"❌ 核心模組導入失敗: {e}")
        return False

def test_config_files():
    """測試配置文件"""
    print("\n🔍 測試配置文件...")
    
    try:
        import yaml
        
        # 測試 config.yaml
        config_path = project_root / "config" / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✅ config.yaml 載入成功 - 包含 {len(config)} 個主要設定")
        else:
            print("❌ config.yaml 不存在")
            return False
            
        # 測試 .env.example
        env_example_path = project_root / ".env.example"
        if env_example_path.exists():
            print("✅ .env.example 存在")
        else:
            print("❌ .env.example 不存在")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置文件測試失敗: {e}")
        return False

def test_strategy_initialization():
    """測試策略初始化"""
    print("\n🔍 測試策略初始化...")
    
    try:
        from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
        
        # 建立測試配置
        test_config = {
            "name": "ICT_NY_FVG_Test",
            "parameters": {
                "session_start": "09:30",
                "session_end": "11:30",
                "timezone": "America/New_York",
                "min_fvg_size_pips": 10,
                "risk_reward_ratio": 3.0
            }
        }
        
        # 初始化策略
        strategy = ICTNYFVGStrategy(test_config)
        print(f"✅ 策略初始化成功: {strategy.name}")
        
        # 測試策略資訊
        info = strategy.get_strategy_info()
        print(f"✅ 策略資訊: {info['name']} v{info['version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略初始化失敗: {e}")
        return False

def test_risk_manager():
    """測試風險管理器"""
    print("\n🔍 測試風險管理器...")
    
    try:
        from core.risk import RiskManager, RiskLimits, AccountState
        from core.strategy_base import TradingSignal, SignalType
        
        # 建立風險限制
        limits = RiskLimits(
            max_risk_per_trade=0.02,
            max_daily_loss=0.05,
            max_positions=3
        )
        
        # 初始化風險管理器
        risk_manager = RiskManager(limits)
        print("✅ 風險管理器初始化成功")
        
        # 測試倉位計算
        test_signal = TradingSignal(
            signal_type=SignalType.LONG,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=106.0
        )
        
        position_size = risk_manager.calculate_position_size(
            test_signal, account_balance=10000.0
        )
        print(f"✅ 倉位計算成功: {position_size:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 風險管理器測試失敗: {e}")
        return False

def test_logging():
    """測試日誌系統"""
    print("\n🔍 測試日誌系統...")
    
    try:
        from core.utils_logging import setup_logging, get_logger, log_trade_event
        
        # 設置日誌（僅控制台輸出）
        setup_logging(log_level="INFO")
        print("✅ 日誌系統初始化成功")
        
        # 測試日誌記錄
        logger = get_logger("test")
        logger.info("測試日誌訊息")
        
        # 測試交易事件記錄
        log_trade_event("TEST", {"message": "測試交易事件"})
        
        print("✅ 日誌功能測試成功")
        return True
        
    except Exception as e:
        print(f"❌ 日誌系統測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print(">> 自動交易機器人環境測試開始\n")
    print("=" * 50)
    
    tests = [
        ("套件導入", test_imports),
        ("核心模組", test_core_modules),
        ("配置文件", test_config_files),
        ("策略初始化", test_strategy_initialization),
        ("風險管理", test_risk_manager),
        ("日誌系統", test_logging)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} 測試 ---")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！環境設置成功！")
        print("\n🚀 下一步建議：")
        print("1. 複製 .env.example 為 .env 並填入真實的 API 金鑰")
        print("2. 開始開發回測引擎")
        print("3. 在 Jupyter Notebook 中進行策略研究")
    else:
        print("❌ 部分測試失敗，請檢查錯誤訊息並修正")
        
    return passed == total

if __name__ == "__main__":
    main()