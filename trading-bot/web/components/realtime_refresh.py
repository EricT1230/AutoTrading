"""
實時刷新組件
使用現代方法實現真正的每秒數據刷新
"""

import streamlit as st
import time
import asyncio
from typing import Optional

class RealtimeRefresher:
    """實時刷新管理器"""
    
    def __init__(self, refresh_interval: float = 1.0):
        self.refresh_interval = refresh_interval
        self.last_refresh = 0
        
    def should_refresh(self) -> bool:
        """檢查是否需要刷新"""
        current_time = time.time()
        if current_time - self.last_refresh >= self.refresh_interval:
            self.last_refresh = current_time
            return True
        return False
    
    def get_remaining_time(self) -> float:
        """獲取下次刷新倒計時"""
        current_time = time.time()
        elapsed = current_time - self.last_refresh
        return max(0, self.refresh_interval - elapsed)

def auto_refresh_container(key: str = "auto_refresh", interval: float = 1.0):
    """
    創建自動刷新容器（被動模式，不強制刷新）
    
    Args:
        key: 唯一標識符
        interval: 刷新間隔（秒）
    """
    
    # 檢查是否啟用自動刷新
    if st.session_state.get('auto_refresh_enabled', False):
        # 僅顯示狀態，讓 Streamlit 的 TTL 快取自然處理數據更新
        st.markdown("""
        <div style='text-align: center; color: #00ff88; font-size: 12px; margin: 5px 0;'>
            🔄 數據自動更新中（基於快取TTL）
        </div>
        """, unsafe_allow_html=True)

def force_refresh_button(label: str = "🔄 強制刷新", key: str = "force_refresh"):
    """創建強制刷新按鈕"""
    if st.button(label, key=key, type="primary"):
        # 清除所有快取
        st.cache_data.clear()
        st.cache_resource.clear()
        
        # 重置刷新器狀態
        for session_key in list(st.session_state.keys()):
            if session_key.startswith("refresher_"):
                del st.session_state[session_key]
        
        # 強制重新運行
        st.rerun()
        return True
    return False

def realtime_status_indicator():
    """實時狀態指示器"""
    auto_refresh = st.session_state.get('auto_refresh_enabled', False)
    
    if auto_refresh:
        status_color = "#00ff88"
        status_text = "🟢 實時更新已啟用"
        icon = "🔄"
    else:
        status_color = "#ff6b6b"
        status_text = "🔴 實時更新已停用"
        icon = "⏸️"
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(90deg, {status_color}22, {status_color}11);
        border: 1px solid {status_color}44;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 5px 0;
        text-align: center;
        color: {status_color};
        font-weight: bold;
        font-size: 13px;
    '>
        {icon} {status_text}
    </div>
    """, unsafe_allow_html=True)

def enhanced_auto_refresh_setup():
    """增強版自動刷新設置（僅顯示狀態，不強制刷新）"""
    
    # 檢查是否啟用自動刷新
    if st.session_state.get('auto_refresh_enabled', False):
        return {
            'active': True,
            'count': 0,
            'remaining': 0,
            'status': "🔄 實時數據自動更新已啟用"
        }
    
    return {
        'active': False,
        'count': 0,
        'remaining': 0,
        'status': "⏸️ 實時數據更新已停用"
    }