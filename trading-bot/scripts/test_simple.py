"""
簡化版本的環境測試腳本
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """測試基本套件導入"""
    print("Testing basic imports...")
    
    try:
        import pandas as pd
        import numpy as np
        import ccxt
        import yaml
        print("SUCCESS: All basic packages imported")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_core_modules():
    """測試核心模組"""
    print("Testing core modules...")
    
    try:
        from core.strategy_base import StrategyBase
        from core.exchange_base import ExchangeBase
        from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
        from core.risk import RiskManager
        print("SUCCESS: All core modules imported")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_strategy_creation():
    """測試策略創建"""
    print("Testing strategy creation...")
    
    try:
        from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
        
        config = {
            "name": "Test_Strategy",
            "parameters": {
                "session_start": "09:30",
                "session_end": "11:30",
                "risk_reward_ratio": 3.0
            }
        }
        
        strategy = ICTNYFVGStrategy(config)
        print(f"SUCCESS: Strategy created - {strategy.name}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """主測試函數"""
    print("AutoTrading Bot Environment Test")
    print("=" * 40)
    
    tests = [
        test_basic_imports,
        test_core_modules, 
        test_strategy_creation
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print("-" * 40)
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("All tests passed! Environment setup successful!")
    else:
        print("Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()