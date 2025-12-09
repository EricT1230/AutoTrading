"""
運行實時K線系統 - 啟動腳本
快速啟動具有實時K線功能的交易機器人
"""

import streamlit as st
import sys
import os
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函數"""
    print("🚀 啟動 AutoTrading Bot 實時K線系統...")
    print("📊 功能特色:")
    print("  - ⚡ 每秒更新的實時K線圖")
    print("  - 🌐 WebSocket實時數據流")
    print("  - 📈 多交易對監控")
    print("  - 🎯 專業技術指標")
    print("  - ⚖️ 智能風險管理")
    print("  - 🔄 性能優化引擎")
    print("")
    print("💡 使用說明:")
    print("  1. 確保已設置 OKX API 環境變數")
    print("  2. 安裝依賴: pip install -r requirements.txt")
    print("  3. 點擊 '⚡ 實時K線' 標籤查看即時圖表")
    print("  4. 啟用自動刷新獲得最佳體驗")
    print("")
    print("🌐 Web界面將在瀏覽器中打開...")
    
    # 運行Streamlit應用
    from web.main_app import main as app_main
    app_main()

if __name__ == "__main__":
    # 檢查依賴
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'ccxt', 
        'websockets', 'loguru', 'aiohttp'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依賴包: {', '.join(missing_packages)}")
        print(f"請運行: pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    main()