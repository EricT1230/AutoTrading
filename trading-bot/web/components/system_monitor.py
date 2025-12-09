"""
系統監控組件
監控系統健康狀態、性能指標和數據流狀態
"""

import time
import psutil
import threading
from typing import Dict, List, Any
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger


class SystemMonitor:
    """系統性能監控器"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics_history = []
        self.max_history_size = 100
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'websocket_latency': 1000,  # ms
            'api_error_rate': 10  # %
        }
        self.last_update = time.time()
        
    def start_monitoring(self):
        """啟動系統監控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    metrics = self.collect_metrics()
                    self.store_metrics(metrics)
                    self.check_alerts(metrics)
                    time.sleep(5)  # 每5秒收集一次
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """停止系統監控"""
        self.monitoring = False
        logger.info("System monitoring stopped")
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集系統指標"""
        try:
            # CPU和內存使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # 網絡連接數
            try:
                connections = len(psutil.net_connections())
            except:
                connections = 0
            
            # 進程信息
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            return {
                'timestamp': datetime.now(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / 1024 / 1024 / 1024,
                'memory_total_gb': memory.total / 1024 / 1024 / 1024,
                'process_memory_mb': process_memory,
                'network_connections': connections,
                'uptime': time.time() - self.last_update
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}
    
    def store_metrics(self, metrics: Dict[str, Any]):
        """存儲指標歷史"""
        if metrics:
            self.metrics_history.append(metrics)
            
            # 限制歷史大小
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """檢查告警條件"""
        alerts = []
        
        if metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
            alerts.append(f"⚠️ CPU使用率過高: {metrics['cpu_percent']:.1f}%")
        
        if metrics.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
            alerts.append(f"⚠️ 內存使用率過高: {metrics['memory_percent']:.1f}%")
        
        # 存儲告警到session state
        if alerts and 'system_alerts' not in st.session_state:
            st.session_state.system_alerts = alerts
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """獲取最新指標"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return {}
    
    def get_metrics_dataframe(self, hours: int = 1) -> pd.DataFrame:
        """獲取指標DataFrame"""
        if not self.metrics_history:
            return pd.DataFrame()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_metrics = [
            m for m in self.metrics_history 
            if m.get('timestamp', datetime.min) > cutoff_time
        ]
        
        if not filtered_metrics:
            return pd.DataFrame()
        
        df = pd.DataFrame(filtered_metrics)
        df.set_index('timestamp', inplace=True)
        return df


class DataFlowMonitor:
    """數據流監控器"""
    
    def __init__(self):
        self.data_sources = {}
        self.latency_history = {}
        self.error_counts = {}
        
    def register_data_source(self, name: str, source_type: str = "unknown"):
        """註冊數據源"""
        self.data_sources[name] = {
            'type': source_type,
            'last_update': None,
            'update_count': 0,
            'error_count': 0,
            'status': 'unknown'
        }
    
    def update_data_source(self, name: str, latency_ms: float = None, 
                          error: bool = False):
        """更新數據源狀態"""
        if name not in self.data_sources:
            self.register_data_source(name)
        
        source = self.data_sources[name]
        source['last_update'] = datetime.now()
        
        if error:
            source['error_count'] += 1
            source['status'] = 'error'
        else:
            source['update_count'] += 1
            source['status'] = 'active'
        
        # 記錄延遲
        if latency_ms is not None:
            if name not in self.latency_history:
                self.latency_history[name] = []
            
            self.latency_history[name].append({
                'timestamp': datetime.now(),
                'latency_ms': latency_ms
            })
            
            # 限制歷史大小
            if len(self.latency_history[name]) > 50:
                self.latency_history[name] = self.latency_history[name][-50:]
    
    def get_data_source_status(self, name: str) -> Dict[str, Any]:
        """獲取數據源狀態"""
        if name not in self.data_sources:
            return {}
        
        source = self.data_sources[name]
        
        # 計算平均延遲
        avg_latency = 0
        if name in self.latency_history and self.latency_history[name]:
            latencies = [l['latency_ms'] for l in self.latency_history[name][-10:]]
            avg_latency = sum(latencies) / len(latencies)
        
        # 檢查是否活躍
        is_stale = False
        if source['last_update']:
            time_diff = (datetime.now() - source['last_update']).total_seconds()
            is_stale = time_diff > 30  # 30秒無更新視為停滯
        
        return {
            **source,
            'avg_latency_ms': avg_latency,
            'is_stale': is_stale,
            'success_rate': (
                source['update_count'] / max(source['update_count'] + source['error_count'], 1)
            ) * 100
        }
    
    def get_all_sources_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有數據源狀態"""
        return {
            name: self.get_data_source_status(name) 
            for name in self.data_sources
        }


class StreamlitMonitorDashboard:
    """Streamlit監控儀表板"""
    
    def __init__(self, system_monitor: SystemMonitor, data_flow_monitor: DataFlowMonitor):
        self.system_monitor = system_monitor
        self.data_flow_monitor = data_flow_monitor
    
    def render_system_metrics(self):
        """渲染系統指標面板"""
        st.subheader("🖥️ 系統性能指標")
        
        metrics = self.system_monitor.get_latest_metrics()
        
        if not metrics:
            st.info("正在收集系統指標...")
            return
        
        # 系統指標卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu = metrics.get('cpu_percent', 0)
            delta_color = "inverse" if cpu > 70 else "normal"
            st.metric(
                "CPU 使用率", 
                f"{cpu:.1f}%",
                delta_color=delta_color
            )
        
        with col2:
            memory = metrics.get('memory_percent', 0)
            delta_color = "inverse" if memory > 80 else "normal"
            st.metric(
                "內存使用率", 
                f"{memory:.1f}%",
                delta_color=delta_color
            )
        
        with col3:
            process_mem = metrics.get('process_memory_mb', 0)
            st.metric(
                "進程內存", 
                f"{process_mem:.1f} MB"
            )
        
        with col4:
            connections = metrics.get('network_connections', 0)
            st.metric(
                "網絡連接", 
                f"{connections}"
            )
        
        # 歷史圖表
        df = self.system_monitor.get_metrics_dataframe(hours=1)
        
        if not df.empty:
            st.subheader("📈 性能趨勢")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.line_chart(df[['cpu_percent', 'memory_percent']], height=200)
            
            with chart_col2:
                st.line_chart(df[['process_memory_mb']], height=200)
    
    def render_data_flow_status(self):
        """渲染數據流狀態"""
        st.subheader("📡 數據流監控")
        
        sources_status = self.data_flow_monitor.get_all_sources_status()
        
        if not sources_status:
            st.info("暫無數據源監控信息")
            return
        
        for name, status in sources_status.items():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    # 狀態指示器
                    if status['is_stale']:
                        st.error(f"🔴 {name}")
                    elif status['status'] == 'active':
                        st.success(f"🟢 {name}")
                    elif status['status'] == 'error':
                        st.warning(f"🟡 {name}")
                    else:
                        st.info(f"⚪ {name}")
                
                with col2:
                    st.metric("更新次數", status['update_count'])
                
                with col3:
                    st.metric("錯誤次數", status['error_count'])
                
                with col4:
                    st.metric("成功率", f"{status['success_rate']:.1f}%")
                
                with col5:
                    if status['avg_latency_ms'] > 0:
                        st.metric("平均延遲", f"{status['avg_latency_ms']:.1f}ms")
                    else:
                        st.metric("平均延遲", "N/A")
        
        st.divider()
    
    def render_alerts(self):
        """渲染系統告警"""
        if 'system_alerts' in st.session_state and st.session_state.system_alerts:
            st.subheader("🚨 系統告警")
            
            for alert in st.session_state.system_alerts:
                st.warning(alert)
            
            if st.button("🔕 清除告警"):
                st.session_state.system_alerts = []
                st.rerun()
    
    def render_full_dashboard(self):
        """渲染完整監控儀表板"""
        st.subheader("🔍 系統監控儀表板")
        
        # 控制面板
        control_col1, control_col2 = st.columns(2)
        
        with control_col1:
            if not self.system_monitor.monitoring:
                if st.button("▶️ 啟動監控"):
                    self.system_monitor.start_monitoring()
                    st.success("系統監控已啟動")
                    st.rerun()
            else:
                if st.button("⏹️ 停止監控"):
                    self.system_monitor.stop_monitoring()
                    st.info("系統監控已停止")
                    st.rerun()
        
        with control_col2:
            auto_refresh = st.checkbox("自動刷新", value=True, key="monitor_auto_refresh")
        
        # 渲染各個監控面板
        self.render_alerts()
        self.render_system_metrics()
        self.render_data_flow_status()
        
        # 自動刷新邏輯
        if auto_refresh:
            if 'monitor_last_refresh' not in st.session_state:
                st.session_state.monitor_last_refresh = time.time()
            
            if time.time() - st.session_state.monitor_last_refresh > 10:  # 每10秒刷新
                st.session_state.monitor_last_refresh = time.time()
                st.rerun()


# 全局實例
system_monitor = SystemMonitor()
data_flow_monitor = DataFlowMonitor()
monitor_dashboard = StreamlitMonitorDashboard(system_monitor, data_flow_monitor)


# 便捷函數
def track_data_update(source_name: str, latency_ms: float = None, error: bool = False):
    """追蹤數據更新"""
    data_flow_monitor.update_data_source(source_name, latency_ms, error)

def register_data_source(name: str, source_type: str = "api"):
    """註冊數據源"""
    data_flow_monitor.register_data_source(name, source_type)


# 測試函數
if __name__ == "__main__":
    # 測試監控組件
    monitor = SystemMonitor()
    monitor.start_monitoring()
    
    print("Collecting metrics for 10 seconds...")
    time.sleep(10)
    
    latest = monitor.get_latest_metrics()
    print(f"Latest metrics: {latest}")
    
    monitor.stop_monitoring()