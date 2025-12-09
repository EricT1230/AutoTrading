"""
簡化的 Web UI 啟動腳本 - 避免編碼問題
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("Starting AutoTrading Bot Web UI...")
    
    project_root = Path(__file__).parent
    main_app_path = project_root / "web" / "main_app.py"
    
    if not main_app_path.exists():
        print(f"Error: Cannot find main app at {main_app_path}")
        return False
    
    print(f"App path: {main_app_path}")
    print("Opening browser at: http://localhost:8501")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(main_app_path),
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--server.headless", "false"
        ]
        
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\nWeb UI stopped")
        return True
    except Exception as e:
        print(f"Error starting Web UI: {e}")
        return False

if __name__ == "__main__":
    main()