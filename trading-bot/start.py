"""
AutoTrading Bot 快速啟動腳本

提供簡單的命令行介面來運行各種功能
"""

import sys
import os
from pathlib import Path
import argparse

# 添加專案根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_environment():
    """測試環境設置"""
    print("執行環境測試...")
    from scripts.test_simple import main as test_main
    test_main()

def run_strategy_demo():
    """運行策略示範"""
    print("運行 ICT NY FVG 策略示範...")
    
    try:
        from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
        from core.strategy_base import TradingSignal, SignalType, BarData
        import pandas as pd
        import numpy as np
        from datetime import datetime
        
        # 建立策略配置
        config = {
            "name": "ICT_NY_FVG_Demo",
            "parameters": {
                "session_start": "09:30",
                "session_end": "11:30", 
                "timezone": "America/New_York",
                "min_fvg_size_pips": 10,
                "max_fvg_size_pips": 100,
                "risk_reward_ratio": 3.0,
                "lookback_bars": 5
            }
        }
        
        # 初始化策略
        strategy = ICTNYFVGStrategy(config)
        print(f"策略初始化成功: {strategy.name}")
        
        # 生成示例數據
        dates = pd.date_range('2024-01-01 09:30:00', periods=100, freq='5min')
        np.random.seed(42)
        
        prices = 50000 + np.cumsum(np.random.randn(100) * 10)
        volumes = np.random.randint(100, 1000, 100)
        
        history_data = []
        for i, date in enumerate(dates):
            high_offset = np.random.uniform(5, 20)
            low_offset = np.random.uniform(5, 20)
            
            history_data.append({
                'timestamp': date,
                'open': prices[i],
                'high': prices[i] + high_offset,
                'low': prices[i] - low_offset,
                'close': prices[i] + np.random.uniform(-10, 10),
                'volume': volumes[i]
            })
        
        history_df = pd.DataFrame(history_data)
        history_df.set_index('timestamp', inplace=True)
        
        print(f"生成示例數據: {len(history_df)} 根K線")
        print(f"價格範圍: {history_df['low'].min():.2f} - {history_df['high'].max():.2f}")
        
        # 測試策略狀態
        status = strategy.get_strategy_status()
        print(f"策略狀態: {status}")
        
        print("\n策略示範完成！")
        
    except Exception as e:
        print(f"錯誤: {e}")

def show_project_structure():
    """顯示專案結構"""
    print("AutoTrading Bot 專案結構:")
    print("=" * 40)
    
    structure = """
trading-bot/
├── README.md                 # 專案說明
├── requirements.txt          # Python 套件清單
├── .env.example             # 環境變數範本
├── start.py                 # 快速啟動腳本
├── config/
│   └── config.yaml          # 全域配置
├── core/                    # 核心邏輯模組
│   ├── strategy_base.py     # 策略基礎類別
│   ├── strategy_ict_ny_fvg.py  # ICT 策略實作
│   ├── exchange_base.py     # 交易所基礎類別
│   ├── risk.py              # 風險管理
│   └── utils_logging.py     # 日誌工具
├── data/                    # 數據目錄
├── notebooks/               # Jupyter 研究筆記
├── backtest/                # 回測引擎
├── live/                    # 實時交易
├── scripts/                 # 工具腳本
│   └── test_simple.py       # 環境測試
└── tests/                   # 測試文件
    """
    print(structure)

def show_next_steps():
    """顯示後續開發步驟"""
    print("後續開發步驟建議:")
    print("=" * 40)
    
    steps = """
1. 【環境配置】
   - 複製 .env.example 為 .env
   - 填入交易所 API 金鑰（建議先使用測試網）

2. 【策略驗證】
   - 在 TradingView 上實作 ICT Pine Script
   - 手動回測驗證策略邏輯

3. 【回測開發】
   - 實作 backtest/backtest_runner.py
   - 下載歷史數據進行回測

4. 【交易所整合】
   - 實作 core/exchange_binance.py
   - 實作模擬交易功能

5. 【實盤部署】
   - VPS 環境配置
   - 監控與告警系統

當前狀態：[OK] 環境設置完成，可以開始步驟 2
    """
    print(steps)

def run_web_ui():
    """啟動 Web UI"""
    print("啟動 Web UI...")
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "run_web_ui.py"
        ], cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        print(f"啟動 Web UI 失敗: {e}")
        return False

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="AutoTrading Bot 快速啟動工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        choices=['test', 'demo', 'structure', 'steps', 'web'],
        help='執行的命令:\n'
             'test - 環境測試\n'
             'demo - 策略示範\n'  
             'structure - 顯示專案結構\n'
             'steps - 顯示後續步驟\n'
             'web - 啟動 Web UI'
    )
    
    args = parser.parse_args()
    
    print("AutoTrading Bot - 自動交易機器人")
    print("=" * 40)
    
    if args.command == 'test':
        test_environment()
    elif args.command == 'demo':
        run_strategy_demo()
    elif args.command == 'structure':
        show_project_structure()
    elif args.command == 'steps':
        show_next_steps()
    elif args.command == 'web':
        run_web_ui()
    
    print("=" * 40)

if __name__ == "__main__":
    main()