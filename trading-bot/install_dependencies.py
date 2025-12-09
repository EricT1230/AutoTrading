"""
依賴包安裝腳本
自動安裝實時K線系統所需的所有依賴包
"""

import subprocess
import sys
import os

def install_package(package):
    """安裝單個包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安裝成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安裝失敗: {e}")
        return False

def check_package(package_name):
    """檢查包是否已安裝"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    """主安裝函數"""
    print("🚀 開始安裝 AutoTrading Bot 實時K線系統依賴...")
    
    # 核心依賴列表
    core_dependencies = [
        "streamlit>=1.28.0",
        "pandas>=2.1.0", 
        "numpy>=1.25.0",
        "plotly>=5.17.0",
        "ccxt>=4.1.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "aiohttp>=3.9.0",
        "websockets>=11.0",  # 實時WebSocket支援
        "websocket-client>=1.6.0",  # WebSocket客戶端
        "pytz>=2023.3"
    ]
    
    # 可選依賴
    optional_dependencies = [
        "matplotlib>=3.8.0",
        "seaborn>=0.12.0", 
        "scipy>=1.11.0",
        "pytest>=7.4.0",
        "black>=23.0.0"
    ]
    
    failed_packages = []
    
    print("📦 安裝核心依賴包...")
    for package in core_dependencies:
        if not install_package(package):
            failed_packages.append(package)
    
    print("\n📦 安裝可選依賴包...")
    for package in optional_dependencies:
        if not install_package(package):
            print(f"⚠️  可選包 {package} 安裝失敗，將跳過")
    
    print("\n🔍 驗證關鍵包安裝狀態...")
    critical_imports = {
        'streamlit': 'streamlit',
        'pandas': 'pandas', 
        'plotly': 'plotly',
        'websockets': 'websockets',
        'ccxt': 'ccxt',
        'loguru': 'loguru',
        'aiohttp': 'aiohttp'
    }
    
    for import_name, package_name in critical_imports.items():
        if check_package(import_name):
            print(f"✅ {package_name} 已正確安裝")
        else:
            print(f"❌ {package_name} 安裝驗證失敗")
            failed_packages.append(package_name)
    
    if failed_packages:
        print(f"\n❌ 以下包安裝失敗: {', '.join(failed_packages)}")
        print("🔧 請手動安裝:")
        for pkg in failed_packages:
            print(f"   pip install {pkg}")
        return False
    else:
        print("\n🎉 所有依賴包安裝成功!")
        print("🚀 可以開始使用實時K線系統了!")
        
        # 檢查環境變數
        if os.path.exists('.env'):
            print("✅ .env 配置文件已存在")
        else:
            print("⚠️  未找到 .env 文件，請確保OKX API配置正確")
        
        return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 下一步:")
        print("1. 確認 .env 文件配置正確")
        print("2. 運行: python run_realtime_kline.py")
        print("3. 或運行: streamlit run web/main_app.py")
    else:
        sys.exit(1)