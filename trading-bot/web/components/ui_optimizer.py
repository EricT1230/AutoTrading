"""
UI優化組件
優化介面清晰度、更新頻率和防止卡死
"""

import streamlit as st
import time
import threading
import asyncio
from typing import Dict, Any, Callable
import pandas as pd
from datetime import datetime
from loguru import logger
import gc


class UIOptimizer:
    """UI優化器 - 防止卡死和提升響應性"""
    
    def __init__(self):
        self.update_locks = {}
        self.last_updates = {}
        self.update_queues = {}
        self.max_update_frequency = 1.0  # 最大1秒更新一次
        self.ui_state = {}
        
    def safe_update_component(self, component_id: str, update_func: Callable, 
                             force_refresh: bool = False) -> bool:
        """安全更新組件，防止卡死"""
        current_time = time.time()
        
        # 檢查更新頻率限制
        if not force_refresh:
            last_update = self.last_updates.get(component_id, 0)
            if current_time - last_update < self.max_update_frequency:
                return False  # 跳過此次更新
        
        # 檢查是否有其他更新在進行
        if component_id in self.update_locks and self.update_locks[component_id]:
            logger.warning(f"Component {component_id} update in progress, skipping")
            return False
        
        try:
            # 設置更新鎖
            self.update_locks[component_id] = True
            
            # 執行更新
            result = update_func()
            
            # 記錄更新時間
            self.last_updates[component_id] = current_time
            
            return True
            
        except Exception as e:
            logger.error(f"Component {component_id} update error: {e}")
            return False
        finally:
            # 釋放更新鎖
            self.update_locks[component_id] = False
    
    def create_status_indicator(self, status: str, details: Dict[str, Any] = None) -> str:
        """創建清晰的狀態指示器"""
        if details is None:
            details = {}
            
        # 狀態顏色映射
        status_colors = {
            'connected': '#28a745',     # 綠色
            'connecting': '#ffc107',    # 黃色  
            'disconnected': '#dc3545', # 紅色
            'error': '#fd7e14',         # 橙色
            'loading': '#17a2b8'        # 藍色
        }
        
        # 狀態圖標映射
        status_icons = {
            'connected': '🟢',
            'connecting': '🟡', 
            'disconnected': '🔴',
            'error': '🟠',
            'loading': '🔵'
        }
        
        color = status_colors.get(status, '#6c757d')
        icon = status_icons.get(status, '⚪')
        
        # 構建狀態顯示
        status_html = f"""
        <div style="
            background: {color}; 
            color: white; 
            padding: 8px 15px; 
            border-radius: 20px; 
            display: inline-flex; 
            align-items: center; 
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <span style="margin-right: 8px;">{icon}</span>
            <span>{status.upper()}</span>
        """
        
        # 添加詳細信息
        if details:
            status_html += '<div style="margin-left: 10px; font-size: 12px; opacity: 0.9;">'
            for key, value in details.items():
                status_html += f"| {key}: {value} "
            status_html += '</div>'
        
        status_html += '</div>'
        
        return status_html
    
    def create_data_freshness_indicator(self, timestamp: datetime, 
                                      max_age_seconds: int = 30) -> str:
        """創建數據新鮮度指示器"""
        if timestamp is None:
            return self.create_status_indicator('error', {'reason': 'No Data'})
        
        current_time = datetime.now()
        
        if hasattr(timestamp, 'tz_localize') and timestamp.tz is None:
            # 處理naive datetime
            timestamp = timestamp.tz_localize('UTC').tz_convert('Asia/Taipei')
        
        age_seconds = (current_time.timestamp() - timestamp.timestamp())
        
        if age_seconds < 5:
            status = 'connected'
            details = {'age': f'{age_seconds:.1f}s'}
        elif age_seconds < max_age_seconds:
            status = 'connecting' 
            details = {'age': f'{age_seconds:.1f}s'}
        else:
            status = 'disconnected'
            details = {'age': f'{age_seconds:.0f}s ago'}
        
        return self.create_status_indicator(status, details)
    
    def create_update_frequency_display(self, component_id: str) -> str:
        """創建更新頻率顯示"""
        current_time = time.time()
        last_update = self.last_updates.get(component_id, current_time)
        
        # 計算更新間隔
        interval = current_time - last_update
        
        if interval < 1:
            freq_text = "< 1s"
            status = 'connected'
        elif interval < 5:
            freq_text = f"{interval:.1f}s"
            status = 'connecting'
        else:
            freq_text = f"{interval:.0f}s ago"
            status = 'disconnected'
        
        return self.create_status_indicator(status, {'update': freq_text})


class MemoryOptimizer:
    """內存優化器 - 防止內存洩漏"""
    
    def __init__(self):
        self.memory_limits = {
            'dataframe_rows': 1000,    # DataFrame最大行數
            'cache_entries': 100,      # 快取項目最大數量
            'session_keys': 50         # Session State最大鍵數
        }
        
    def optimize_dataframe(self, df: pd.DataFrame, max_rows: int = None) -> pd.DataFrame:
        """優化DataFrame內存使用"""
        if df is None or df.empty:
            return df
        
        max_rows = max_rows or self.memory_limits['dataframe_rows']
        
        # 限制行數
        if len(df) > max_rows:
            df = df.tail(max_rows)
        
        # 優化數據類型
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    # 嘗試轉換為數值類型
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            elif df[col].dtype == 'float64':
                # 降低精度
                df[col] = df[col].astype('float32')
            elif df[col].dtype == 'int64':
                # 使用較小的整數類型
                if df[col].min() >= -32768 and df[col].max() <= 32767:
                    df[col] = df[col].astype('int16')
                elif df[col].min() >= -2147483648 and df[col].max() <= 2147483647:
                    df[col] = df[col].astype('int32')
        
        return df
    
    def cleanup_session_state(self):
        """清理Session State"""
        if len(st.session_state) <= self.memory_limits['session_keys']:
            return
        
        # 獲取所有鍵和最後訪問時間
        keys_to_remove = []
        current_time = time.time()
        
        for key in st.session_state:
            # 移除臨時鍵
            if key.startswith('temp_') or key.startswith('cache_'):
                last_access = st.session_state.get(f"{key}_timestamp", 0)
                if current_time - last_access > 300:  # 5分鐘未使用
                    keys_to_remove.append(key)
        
        # 刪除過期鍵
        for key in keys_to_remove:
            try:
                del st.session_state[key]
                if f"{key}_timestamp" in st.session_state:
                    del st.session_state[f"{key}_timestamp"]
            except:
                pass
        
        logger.info(f"Cleaned up {len(keys_to_remove)} session state keys")
    
    def force_garbage_collection(self):
        """強制垃圾回收"""
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")


class ResponsiveUpdater:
    """響應式更新器 - 智能控制更新頻率"""
    
    def __init__(self):
        self.update_intervals = {
            'realtime_chart': 1.0,    # K線圖：1秒
            'ticker_display': 2.0,    # 行情顯示：2秒  
            'multi_symbol': 3.0,      # 多交易對：3秒
            'system_monitor': 5.0     # 系統監控：5秒
        }
        self.last_updates = {}
        self.update_enabled = {}
        
    def should_update(self, component_id: str, force: bool = False) -> bool:
        """檢查是否應該更新組件"""
        if force:
            return True
            
        if not self.update_enabled.get(component_id, True):
            return False
        
        current_time = time.time()
        last_update = self.last_updates.get(component_id, 0)
        interval = self.update_intervals.get(component_id, 1.0)
        
        return (current_time - last_update) >= interval
    
    def mark_updated(self, component_id: str):
        """標記組件已更新"""
        self.last_updates[component_id] = time.time()
    
    def pause_updates(self, component_id: str):
        """暫停組件更新"""
        self.update_enabled[component_id] = False
    
    def resume_updates(self, component_id: str):
        """恢復組件更新"""
        self.update_enabled[component_id] = True
    
    def get_next_update_time(self, component_id: str) -> float:
        """獲取下次更新時間"""
        last_update = self.last_updates.get(component_id, 0)
        interval = self.update_intervals.get(component_id, 1.0)
        return max(0, interval - (time.time() - last_update))


# 全局實例
ui_optimizer = UIOptimizer()
memory_optimizer = MemoryOptimizer()
responsive_updater = ResponsiveUpdater()


# 裝飾器函數
def safe_component_update(component_id: str, force_refresh: bool = False):
    """安全組件更新裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return ui_optimizer.safe_update_component(
                component_id, 
                lambda: func(*args, **kwargs),
                force_refresh
            )
        return wrapper
    return decorator


def responsive_update(component_id: str):
    """響應式更新裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if responsive_updater.should_update(component_id):
                result = func(*args, **kwargs)
                responsive_updater.mark_updated(component_id)
                return result
            return None
        return wrapper
    return decorator


# 便捷函數
def show_connection_status(service_name: str, is_connected: bool, 
                          details: Dict[str, Any] = None):
    """顯示連接狀態"""
    status = 'connected' if is_connected else 'disconnected'
    status_html = ui_optimizer.create_status_indicator(status, details)
    st.markdown(f"**{service_name}**: {status_html}", unsafe_allow_html=True)

def show_data_freshness(data_timestamp: datetime, label: str = "數據"):
    """顯示數據新鮮度"""
    freshness_html = ui_optimizer.create_data_freshness_indicator(data_timestamp)
    st.markdown(f"**{label}**: {freshness_html}", unsafe_allow_html=True)


# 測試函數
if __name__ == "__main__":
    # 測試UI優化組件
    print("Testing UI optimizer...")
    
    optimizer = UIOptimizer()
    
    def test_update():
        print("Update function called")
        return True
    
    # 測試安全更新
    result = optimizer.safe_update_component("test", test_update)
    print(f"Update result: {result}")
    
    # 測試狀態指示器
    status_html = optimizer.create_status_indicator('connected', {'ping': '25ms'})
    print(f"Status HTML: {status_html}")