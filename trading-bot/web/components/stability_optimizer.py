"""
穩定性優化組件 
防止系統卡死、優化更新頻率、提升用戶體驗
"""

import streamlit as st
import time
import threading
import asyncio
import gc
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
import psutil
import queue


class StabilityManager:
    """穩定性管理器 - 防止系統卡死"""
    
    def __init__(self):
        self.update_locks = {}
        self.component_timeouts = {}
        self.max_update_duration = 5.0  # 最大更新時間5秒
        self.update_history = {}
        self.blocked_components = set()
        
    def safe_execute(self, component_id: str, func, timeout: float = None, 
                    fallback_result: Any = None):
        """安全執行函數，防止卡死"""
        timeout = timeout or self.max_update_duration
        
        # 檢查組件是否被阻止
        if component_id in self.blocked_components:
            logger.warning(f"Component {component_id} is blocked")
            return fallback_result
        
        # 檢查是否已經在執行
        if component_id in self.update_locks and self.update_locks[component_id]:
            logger.warning(f"Component {component_id} already updating")
            return fallback_result
        
        start_time = time.time()
        
        try:
            # 設置執行鎖
            self.update_locks[component_id] = True
            
            # 執行函數
            result = func()
            
            # 記錄執行時間
            execution_time = time.time() - start_time
            self._record_execution_time(component_id, execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Component {component_id} execution failed after {execution_time:.2f}s: {e}")
            
            # 如果執行時間過長，暫時阻止該組件
            if execution_time > timeout:
                self._temporarily_block_component(component_id)
                
            return fallback_result
            
        finally:
            # 釋放鎖
            self.update_locks[component_id] = False
    
    def _record_execution_time(self, component_id: str, execution_time: float):
        """記錄執行時間"""
        if component_id not in self.update_history:
            self.update_history[component_id] = []
        
        self.update_history[component_id].append({
            'timestamp': datetime.now(),
            'execution_time': execution_time
        })
        
        # 只保留最近10次記錄
        if len(self.update_history[component_id]) > 10:
            self.update_history[component_id] = self.update_history[component_id][-10:]
    
    def _temporarily_block_component(self, component_id: str, duration: int = 30):
        """暫時阻止組件更新"""
        self.blocked_components.add(component_id)
        
        def unblock_component():
            time.sleep(duration)
            self.blocked_components.discard(component_id)
            logger.info(f"Component {component_id} unblocked after {duration}s")
        
        thread = threading.Thread(target=unblock_component, daemon=True)
        thread.start()
        
        logger.warning(f"Component {component_id} blocked for {duration}s due to timeout")
    
    def get_component_health(self, component_id: str) -> Dict[str, Any]:
        """獲取組件健康狀況"""
        if component_id not in self.update_history:
            return {'status': 'unknown', 'avg_time': 0, 'last_update': None}
        
        history = self.update_history[component_id]
        
        # 計算平均執行時間
        avg_time = sum(record['execution_time'] for record in history) / len(history)
        
        # 獲取最後更新時間
        last_update = history[-1]['timestamp'] if history else None
        
        # 判斷健康狀況
        if component_id in self.blocked_components:
            status = 'blocked'
        elif avg_time > self.max_update_duration * 0.8:
            status = 'slow'
        elif avg_time > self.max_update_duration * 0.5:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'avg_time': avg_time,
            'last_update': last_update,
            'update_count': len(history)
        }


class MemoryWatchdog:
    """內存監控器 - 防止內存洩漏"""
    
    def __init__(self):
        self.memory_threshold = 80  # 內存使用率閾值
        self.monitoring = False
        self.cleanup_queue = queue.Queue()
        
    def start_monitoring(self):
        """開始內存監控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_memory():
            while self.monitoring:
                try:
                    # 檢查內存使用率
                    memory_percent = psutil.virtual_memory().percent
                    
                    if memory_percent > self.memory_threshold:
                        logger.warning(f"High memory usage: {memory_percent:.1f}%")
                        self._trigger_memory_cleanup()
                    
                    time.sleep(10)  # 每10秒檢查一次
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=monitor_memory, daemon=True)
        thread.start()
        logger.info("Memory watchdog started")
    
    def stop_monitoring(self):
        """停止內存監控"""
        self.monitoring = False
    
    def _trigger_memory_cleanup(self):
        """觸發內存清理"""
        try:
            # 清理Session State中的大型對象
            self._cleanup_session_state()
            
            # 強制垃圾回收
            collected = gc.collect()
            logger.info(f"Memory cleanup: collected {collected} objects")
            
            # 清理Streamlit快取
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            
        except Exception as e:
            logger.error(f"Memory cleanup error: {e}")
    
    def _cleanup_session_state(self):
        """清理Session State"""
        keys_to_remove = []
        current_time = time.time()
        
        for key in st.session_state:
            # 移除臨時或過期的鍵
            if (key.startswith('temp_') or 
                key.startswith('cache_') or 
                key.endswith('_old')):
                
                # 檢查最後使用時間
                timestamp_key = f"{key}_timestamp"
                if timestamp_key in st.session_state:
                    last_used = st.session_state[timestamp_key]
                    if current_time - last_used > 300:  # 5分鐘未使用
                        keys_to_remove.append(key)
                        keys_to_remove.append(timestamp_key)
                else:
                    # 沒有時間戳的臨時鍵直接刪除
                    keys_to_remove.append(key)
        
        # 刪除標記的鍵
        for key in keys_to_remove:
            try:
                del st.session_state[key]
            except:
                pass
        
        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} session state keys")


class UpdateFrequencyOptimizer:
    """更新頻率優化器 - 動態調整更新頻率"""
    
    def __init__(self):
        self.base_intervals = {
            'realtime_chart': 1.0,
            'ticker_display': 2.0,
            'multi_symbol': 3.0,
            'system_monitor': 5.0
        }
        self.current_intervals = self.base_intervals.copy()
        self.last_updates = {}
        self.performance_history = {}
        
    def should_update(self, component_id: str) -> bool:
        """檢查是否應該更新"""
        current_time = time.time()
        last_update = self.last_updates.get(component_id, 0)
        interval = self.current_intervals.get(component_id, 1.0)
        
        return (current_time - last_update) >= interval
    
    def mark_updated(self, component_id: str, performance_score: float = 1.0):
        """標記組件已更新並記錄性能分數"""
        current_time = time.time()
        self.last_updates[component_id] = current_time
        
        # 記錄性能
        if component_id not in self.performance_history:
            self.performance_history[component_id] = []
        
        self.performance_history[component_id].append({
            'timestamp': current_time,
            'score': performance_score
        })
        
        # 只保留最近20次記錄
        if len(self.performance_history[component_id]) > 20:
            self.performance_history[component_id] = self.performance_history[component_id][-20:]
        
        # 動態調整更新頻率
        self._adjust_frequency(component_id)
    
    def _adjust_frequency(self, component_id: str):
        """動態調整更新頻率"""
        if component_id not in self.performance_history:
            return
        
        history = self.performance_history[component_id]
        if len(history) < 5:
            return
        
        # 計算最近的平均性能分數
        recent_scores = [record['score'] for record in history[-5:]]
        avg_score = sum(recent_scores) / len(recent_scores)
        
        base_interval = self.base_intervals.get(component_id, 1.0)
        
        # 根據性能調整頻率
        if avg_score > 0.8:
            # 性能良好，可以稍微提高頻率
            new_interval = base_interval * 0.9
        elif avg_score > 0.6:
            # 性能一般，保持基準頻率
            new_interval = base_interval
        elif avg_score > 0.4:
            # 性能較差，降低頻率
            new_interval = base_interval * 1.5
        else:
            # 性能很差，顯著降低頻率
            new_interval = base_interval * 2.0
        
        # 限制頻率範圍
        min_interval = base_interval * 0.5
        max_interval = base_interval * 3.0
        new_interval = max(min_interval, min(max_interval, new_interval))
        
        if abs(new_interval - self.current_intervals.get(component_id, base_interval)) > 0.1:
            self.current_intervals[component_id] = new_interval
            logger.debug(f"Adjusted {component_id} interval to {new_interval:.1f}s (score: {avg_score:.2f})")
    
    def get_next_update_time(self, component_id: str) -> float:
        """獲取下次更新時間"""
        current_time = time.time()
        last_update = self.last_updates.get(component_id, current_time)
        interval = self.current_intervals.get(component_id, 1.0)
        
        return max(0, interval - (current_time - last_update))


class ClearStatusDisplay:
    """清晰狀態顯示組件"""
    
    @staticmethod
    def create_connection_indicator(is_connected: bool, service_name: str, 
                                   latency_ms: Optional[float] = None) -> str:
        """創建連接狀態指示器"""
        if is_connected:
            color = "#28a745"
            icon = "🟢"
            status_text = "已連接"
            if latency_ms:
                status_text += f" ({latency_ms:.0f}ms)"
        else:
            color = "#dc3545"
            icon = "🔴"
            status_text = "未連接"
        
        return f"""
        <div style="
            display: inline-flex; 
            align-items: center; 
            background: {color}; 
            color: white; 
            padding: 6px 12px; 
            border-radius: 15px; 
            font-size: 13px; 
            font-weight: bold;
            margin: 2px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <span style="margin-right: 6px;">{icon}</span>
            <span>{service_name}: {status_text}</span>
        </div>
        """
    
    @staticmethod
    def create_update_status(next_update_seconds: float, component_name: str = "") -> str:
        """創建更新狀態顯示"""
        if next_update_seconds <= 0.1:
            color = "#17a2b8"
            icon = "🔄"
            text = "正在更新"
        elif next_update_seconds <= 1.0:
            color = "#28a745"
            icon = "⏱️"
            text = f"{next_update_seconds:.1f}s"
        else:
            color = "#ffc107"
            icon = "⏰"
            text = f"{next_update_seconds:.0f}s"
        
        component_text = f"{component_name} " if component_name else ""
        
        return f"""
        <div style="
            display: inline-flex; 
            align-items: center; 
            background: {color}; 
            color: white; 
            padding: 6px 12px; 
            border-radius: 15px; 
            font-size: 13px; 
            font-weight: bold;
            margin: 2px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <span style="margin-right: 6px;">{icon}</span>
            <span>{component_text}下次更新: {text}</span>
        </div>
        """


# 全局實例
stability_manager = StabilityManager()
memory_watchdog = MemoryWatchdog()
frequency_optimizer = UpdateFrequencyOptimizer()
status_display = ClearStatusDisplay()


# 裝飾器函數
def stable_execution(component_id: str, timeout: float = 5.0, fallback_result: Any = None):
    """穩定執行裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return stability_manager.safe_execute(
                component_id,
                lambda: func(*args, **kwargs),
                timeout,
                fallback_result
            )
        return wrapper
    return decorator


# 便捷函數
def show_system_health():
    """顯示系統健康狀況"""
    st.subheader("🔍 系統健康狀況")
    
    # 內存使用情況
    memory_info = psutil.virtual_memory()
    memory_color = "normal" if memory_info.percent < 70 else "inverse"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "內存使用率", 
            f"{memory_info.percent:.1f}%",
            delta_color=memory_color
        )
    
    with col2:
        # 顯示阻止的組件數量
        blocked_count = len(stability_manager.blocked_components)
        st.metric("阻止組件", f"{blocked_count}")
    
    with col3:
        # 顯示監控狀態
        monitoring_status = "運行中" if memory_watchdog.monitoring else "已停止"
        st.metric("內存監控", monitoring_status)


def auto_start_watchdog():
    """自動啟動監控"""
    if 'watchdog_started' not in st.session_state:
        memory_watchdog.start_monitoring()
        st.session_state.watchdog_started = True


# 測試函數
if __name__ == "__main__":
    # 測試穩定性管理器
    manager = StabilityManager()
    
    def test_function():
        time.sleep(0.1)
        return "success"
    
    result = manager.safe_execute("test_component", test_function)
    print(f"Test result: {result}")
    
    health = manager.get_component_health("test_component")
    print(f"Component health: {health}")