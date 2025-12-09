"""
AutoTrading Bot Web UI 啟動腳本

快速啟動 Streamlit Web 應用程式
"""

import subprocess
import sys
import os
from pathlib import Path
import streamlit as st


def check_dependencies():
    """檢查依賴套件"""
    required_packages = [
        'streamlit', 'plotly', 'pandas', 'numpy', 
        'ccxt', 'loguru', 'pyyaml', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依賴套件: {', '.join(missing_packages)}")
        print("請執行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依賴套件已安裝")
    return True


def setup_environment():
    """設置環境變數"""
    project_root = Path(__file__).parent
    
    # 檢查 .env 文件
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("📋 .env 文件不存在，正在創建...")
        env_file.write_text(env_example.read_text(encoding='utf-8'))
        print("✅ .env 文件已創建，請編輯並填入真實的 API 金鑰")
    
    # 設置 Python 路徑
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    return True


def start_streamlit():
    """啟動 Streamlit 應用"""
    project_root = Path(__file__).parent
    main_app_path = project_root / "web" / "main_app.py"
    
    if not main_app_path.exists():
        print(f"❌ 找不到主應用文件: {main_app_path}")
        return False
    
    print(">> Starting AutoTrading Bot Web UI...")
    print(f">> App Path: {main_app_path}")
    print(">> Browser will open automatically, if not please visit: http://localhost:8501")
    print(">> Press Ctrl+C to stop service")
    print("-" * 60)
    
    try:
        # 設置 Streamlit 配置
        config_args = [
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false",
            "--server.enableXsrfProtection", "false"
        ]
        
        # 啟動命令
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(main_app_path)
        ] + config_args
        
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n>> Web UI stopped")
        return True
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        return False


def main():
    """主函數"""
    print("AutoTrading Bot Web UI Launcher")
    print("=" * 50)
    
    # 檢查依賴
    if not check_dependencies():
        return False
    
    # 設置環境
    if not setup_environment():
        return False
    
    # 啟動 Web UI
    return start_streamlit()


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)