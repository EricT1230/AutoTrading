"""
性能優化組件
優化前後端實時性能，減少延遲，提升用戶體驗
"""

import streamlit as st
import asyncio
import threading
import time
import queue
from typing import Dict, Any, Callable
import pandas as pd
from loguru import logger
import gc


class PerformanceOptimizer:
    """性能優化器"""
    
    def __init__(self):
        self.data_cache = {}
        self.update_queue = queue.Queue()
        self.background_workers = {}
        self.optimization_config = {
            'enable_compression': True,
            'cache_limit': 1000,
            'update_batch_size': 10,
            'memory_cleanup_interval': 30,
            'websocket_buffer_size': 1000
        }
    
    def optimize_streamlit_performance(self):
        """優化Streamlit性能"""
        # 設置Streamlit配置
        if 'performance_optimized' not in st.session_state:
            # 禁用某些調試功能以提升性能
            st.session_state.performance_optimized = True
            
            # 優化內存使用
            self._setup_memory_optimization()
            
            # 啟動背景清理任務
            self._start_background_cleanup()
    
    def _setup_memory_optimization(self):
        """設置內存優化"""
        # 設置DataFrame顯示選項以減少內存使用
        pd.set_option('display.max_rows', 50)
        pd.set_option('display.max_columns', 20)
        
        # 啟動內存監控
        self._start_memory_monitor()
    
    def _start_memory_monitor(self):
        """啟動內存監控"""
        def monitor_memory():
            while True:
                try:
                    # 每30秒清理一次內存
                    time.sleep(self.optimization_config['memory_cleanup_interval'])
                    
                    # 清理過期的快取數據
                    self._cleanup_expired_cache()
                    
                    # 強制垃圾回收
                    gc.collect()
                    
                except Exception as e:
                    logger.error(f"Memory monitor error: {e}")
        
        if 'memory_monitor_started' not in st.session_state:
            thread = threading.Thread(target=monitor_memory, daemon=True)
            thread.start()
            st.session_state.memory_monitor_started = True
            logger.info("Memory monitor started")
    
    def _cleanup_expired_cache(self):
        """清理過期快取"""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self.data_cache.items():
            if isinstance(data, dict) and 'timestamp' in data:
                # 如果數據超過60秒就清理
                if current_time - data['timestamp'] > 60:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.data_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _start_background_cleanup(self):
        """啟動背景清理任務"""
        def cleanup_task():
            while True:
                try:
                    time.sleep(60)  # 每分鐘清理一次
                    
                    # 清理Streamlit快取
                    if hasattr(st, 'cache_data'):
                        # 只清理舊的數據快取，保留資源快取
                        for func_name in list(st.session_state.keys()):
                            if func_name.startswith('cache_data_'):
                                try:
                                    cache_time = st.session_state.get(f"{func_name}_time", 0)
                                    if time.time() - cache_time > 120:  # 2分鐘後清理
                                        if func_name in st.session_state:
                                            del st.session_state[func_name]
                                except:
                                    pass
                
                except Exception as e:
                    logger.error(f"Background cleanup error: {e}")
        
        if 'cleanup_task_started' not in st.session_state:
            thread = threading.Thread(target=cleanup_task, daemon=True)
            thread.start()
            st.session_state.cleanup_task_started = True
            logger.info("Background cleanup task started")
    
    def optimize_data_loading(self, data_func: Callable, cache_key: str, ttl: int = 5):
        """優化數據加載"""
        current_time = time.time()
        
        # 檢查快取
        if cache_key in self.data_cache:
            cache_data = self.data_cache[cache_key]
            if current_time - cache_data['timestamp'] < ttl:
                return cache_data['data']
        
        # 加載新數據
        try:
            data = data_func()
            self.data_cache[cache_key] = {
                'data': data,
                'timestamp': current_time
            }
            return data
        except Exception as e:
            logger.error(f"Data loading error for {cache_key}: {e}")
            # 返回快取的舊數據（如果有）
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]['data']
            return None
    
    def create_efficient_chart_container(self, chart_id: str):
        """創建高效的圖表容器"""
        if f"chart_container_{chart_id}" not in st.session_state:
            st.session_state[f"chart_container_{chart_id}"] = st.empty()
        
        return st.session_state[f"chart_container_{chart_id}"]
    
    def batch_update_charts(self, updates: Dict[str, Any]):
        """批量更新圖表"""
        # 將更新請求加入隊列
        for chart_id, update_data in updates.items():
            self.update_queue.put({
                'chart_id': chart_id,
                'data': update_data,
                'timestamp': time.time()
            })
        
        # 處理批量更新
        self._process_batch_updates()
    
    def _process_batch_updates(self):
        """處理批量更新"""
        updates = []
        
        # 收集待更新的項目（最多處理batch_size個）
        for _ in range(self.optimization_config['update_batch_size']):
            try:
                update = self.update_queue.get_nowait()
                updates.append(update)
            except queue.Empty:
                break
        
        # 執行批量更新
        if updates:
            for update in updates:
                try:
                    chart_id = update['chart_id']
                    container = self.create_efficient_chart_container(chart_id)
                    
                    with container:
                        # 在這裡執行實際的圖表更新
                        self._render_optimized_chart(update['data'])
                        
                except Exception as e:
                    logger.error(f"Chart update error for {update['chart_id']}: {e}")
    
    def _render_optimized_chart(self, chart_data: Dict[str, Any]):
        """渲染優化的圖表"""
        import plotly.graph_objects as go
        
        try:
            # 使用優化的Plotly配置
            config = {
                'displayModeBar': False,  # 隱藏工具欄以提升性能
                'staticPlot': False,
                'responsive': True,
                'displaylogo': False,
            }
            
            # 如果數據量大，進行採樣
            if 'data' in chart_data and isinstance(chart_data['data'], pd.DataFrame):
                df = chart_data['data']
                if len(df) > 500:  # 超過500個點就採樣
                    # 保留最新的500個點
                    df = df.tail(500)
                    chart_data['data'] = df
            
            # 創建圖表（這裡需要根據具體的圖表類型實現）
            fig = self._create_chart_from_data(chart_data)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True, config=config)
                
        except Exception as e:
            logger.error(f"Optimized chart render error: {e}")
    
    def _create_chart_from_data(self, chart_data: Dict[str, Any]):
        """從數據創建圖表"""
        # 這是一個通用的圖表創建函數，可以根據需要擴展
        try:
            import plotly.graph_objects as go
            
            if 'type' in chart_data:
                if chart_data['type'] == 'candlestick':
                    data = chart_data['data']
                    return go.Figure(data=[
                        go.Candlestick(
                            x=data.index,
                            open=data['open'],
                            high=data['high'],
                            low=data['low'],
                            close=data['close']
                        )
                    ])
                elif chart_data['type'] == 'line':
                    data = chart_data['data']
                    return go.Figure(data=[
                        go.Scatter(
                            x=data.index,
                            y=data['close'],
                            mode='lines'
                        )
                    ])
            
            return None
            
        except Exception as e:
            logger.error(f"Chart creation error: {e}")
            return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計"""
        return {
            'cache_size': len(self.data_cache),
            'queue_size': self.update_queue.qsize(),
            'memory_optimization': st.session_state.get('performance_optimized', False),
            'background_tasks': {
                'memory_monitor': st.session_state.get('memory_monitor_started', False),
                'cleanup_task': st.session_state.get('cleanup_task_started', False)
            }
        }


class StreamlitPerformanceDashboard:
    """Streamlit性能儀表板"""
    
    def __init__(self, optimizer: PerformanceOptimizer):
        self.optimizer = optimizer
    
    def render_performance_panel(self):
        """渲染性能面板"""
        with st.expander("⚡ 性能監控", expanded=False):
            stats = self.optimizer.get_performance_stats()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("快取大小", stats['cache_size'])
                st.metric("更新隊列", stats['queue_size'])
            
            with col2:
                memory_status = "✅ 已優化" if stats['memory_optimization'] else "❌ 未優化"
                st.write(f"**內存優化**: {memory_status}")
                
                monitor_status = "✅ 運行中" if stats['background_tasks']['memory_monitor'] else "❌ 未啟動"
                st.write(f"**內存監控**: {monitor_status}")
            
            with col3:
                cleanup_status = "✅ 運行中" if stats['background_tasks']['cleanup_task'] else "❌ 未啟動"
                st.write(f"**清理任務**: {cleanup_status}")
                
                if st.button("🔧 手動優化", help="手動執行性能優化"):
                    self.optimizer.optimize_streamlit_performance()
                    st.success("性能優化完成!")
            
            # 顯示優化建議
            st.write("**性能優化建議:**")
            recommendations = [
                "✅ 啟用WebSocket實時數據流",
                "✅ 使用數據快取減少API調用", 
                "✅ 批量處理圖表更新",
                "✅ 定期清理內存和快取",
                "⚡ 圖表數據採樣（大數據集）"
            ]
            
            for rec in recommendations:
                st.write(f"- {rec}")


# 全局實例
performance_optimizer = PerformanceOptimizer()
performance_dashboard = StreamlitPerformanceDashboard(performance_optimizer)


# 裝飾器函數
def optimize_data_function(cache_key: str, ttl: int = 5):
    """數據函數優化裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return performance_optimizer.optimize_data_loading(
                lambda: func(*args, **kwargs), 
                cache_key, 
                ttl
            )
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 測試性能優化器
    optimizer = PerformanceOptimizer()
    optimizer.optimize_streamlit_performance()
    
    print("Performance optimizer initialized")
    print(f"Stats: {optimizer.get_performance_stats()}")