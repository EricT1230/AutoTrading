#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 实时K线系统
简化的启动脚本，自动处理依赖和配置检查
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    required_packages = ['streamlit', 'pandas', 'plotly', 'websockets', 'ccxt']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing

def check_env_file():
    """检查环境配置文件"""
    env_file = Path('.env')
    if not env_file.exists():
        print("Warning: .env file not found")
        return False
    return True

def start_streamlit():
    """启动Streamlit应用"""
    try:
        # 使用subprocess启动streamlit
        cmd = [sys.executable, '-m', 'streamlit', 'run', 'web/main_app.py', '--server.headless', 'true']
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error starting application: {e}")

def main():
    """主函数"""
    print("AutoTrading Bot - Realtime K-line System")
    print("=" * 50)
    
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Please run: pip install " + " ".join(missing))
        return False
    
    print("✓ All dependencies available")
    
    # 检查环境配置
    if not check_env_file():
        print("✓ Using demo API configuration")
    else:
        print("✓ Environment configuration found")
    
    print("\nStarting application...")
    print("Access URL: http://localhost:8501")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # 启动应用
    start_streamlit()
    return True

if __name__ == "__main__":
    main()