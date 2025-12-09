"""
錯誤處理和異常捕獲系統
提供統一的錯誤處理、重試機制和降級方案
"""

import time
import traceback
import functools
from typing import Callable, Any, Optional
import streamlit as st
from loguru import logger
import asyncio


class ErrorHandler:
    """統一錯誤處理器"""
    
    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # 重試延遲時間（秒）
    
    def handle_error(self, error: Exception, context: str = "Unknown", 
                    show_user: bool = True, fallback_value: Any = None):
        """處理錯誤"""
        error_key = f"{context}:{type(error).__name__}"
        
        # 記錄錯誤次數
        if error_key not in self.error_counts:
            self.error_counts[error_key] = 0
        self.error_counts[error_key] += 1
        
        # 記錄最後錯誤時間
        self.last_errors[error_key] = time.time()
        
        # 記錄詳細日誌
        logger.error(f"Error in {context}: {error}")
        logger.debug(traceback.format_exc())
        
        # 顯示給用戶
        if show_user:
            if self.error_counts[error_key] == 1:
                st.error(f"❌ {context} 發生錯誤: {str(error)}")
            elif self.error_counts[error_key] < 5:
                st.warning(f"⚠️ {context} 再次發生錯誤 (第{self.error_counts[error_key]}次)")
            else:
                # 錯誤太頻繁，只在日誌中記錄
                if self.error_counts[error_key] == 5:
                    st.error(f"🚨 {context} 錯誤過於頻繁，將只在日誌中記錄")
        
        return fallback_value
    
    def retry_on_error(self, max_retries: int = None, delay_factor: float = 1.0, 
                      fallback_value: Any = None, context: str = "Function"):
        """錯誤重試裝飾器"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                retries = max_retries or self.max_retries
                
                for attempt in range(retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt < retries:
                            delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)] * delay_factor
                            logger.warning(f"Attempt {attempt + 1} failed for {context}: {e}. Retrying in {delay}s...")
                            time.sleep(delay)
                        else:
                            return self.handle_error(
                                e, 
                                f"{context} (after {retries} retries)", 
                                show_user=True, 
                                fallback_value=fallback_value
                            )
                
                return fallback_value
            return wrapper
        return decorator
    
    def async_retry_on_error(self, max_retries: int = None, delay_factor: float = 1.0, 
                           fallback_value: Any = None, context: str = "AsyncFunction"):
        """異步錯誤重試裝飾器"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                retries = max_retries or self.max_retries
                
                for attempt in range(retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        if attempt < retries:
                            delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)] * delay_factor
                            logger.warning(f"Async attempt {attempt + 1} failed for {context}: {e}. Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                        else:
                            return self.handle_error(
                                e, 
                                f"{context} (after {retries} retries)", 
                                show_user=True, 
                                fallback_value=fallback_value
                            )
                
                return fallback_value
            return wrapper
        return decorator
    
    def get_error_stats(self) -> dict:
        """獲取錯誤統計"""
        current_time = time.time()
        recent_errors = {}
        
        for error_key, last_time in self.last_errors.items():
            if current_time - last_time < 3600:  # 最近1小時的錯誤
                recent_errors[error_key] = {
                    'count': self.error_counts.get(error_key, 0),
                    'last_occurred': last_time
                }
        
        return recent_errors
    
    def reset_error_counts(self):
        """重置錯誤計數"""
        self.error_counts.clear()
        self.last_errors.clear()
        logger.info("Error counts reset")


class ConnectionManager:
    """連接管理器 - 處理網絡連接相關錯誤"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.connection_status = {}
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 5
    
    def check_connection(self, service_name: str, test_func: Callable) -> bool:
        """檢查服務連接狀態"""
        try:
            result = test_func()
            self.connection_status[service_name] = True
            self.reconnect_attempts[service_name] = 0
            return True
        except Exception as e:
            self.connection_status[service_name] = False
            self.error_handler.handle_error(
                e, 
                f"Connection check for {service_name}",
                show_user=False
            )
            return False
    
    async def reconnect_service(self, service_name: str, reconnect_func: Callable) -> bool:
        """重連服務"""
        if service_name not in self.reconnect_attempts:
            self.reconnect_attempts[service_name] = 0
        
        if self.reconnect_attempts[service_name] >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts reached for {service_name}")
            return False
        
        self.reconnect_attempts[service_name] += 1
        delay = min(self.reconnect_attempts[service_name] * 2, 30)  # 最多等待30秒
        
        try:
            await asyncio.sleep(delay)
            result = await reconnect_func()
            
            if result:
                self.connection_status[service_name] = True
                self.reconnect_attempts[service_name] = 0
                logger.info(f"Successfully reconnected to {service_name}")
                return True
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                f"Reconnection attempt {self.reconnect_attempts[service_name]} for {service_name}",
                show_user=False
            )
        
        return False
    
    def get_connection_status(self) -> dict:
        """獲取所有服務的連接狀態"""
        return self.connection_status.copy()


class StreamlitErrorDisplay:
    """Streamlit錯誤顯示組件"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    def render_error_dashboard(self):
        """渲染錯誤監控儀表板"""
        with st.expander("🚨 錯誤監控", expanded=False):
            error_stats = self.error_handler.get_error_stats()
            
            if not error_stats:
                st.success("✅ 系統運行正常，無近期錯誤")
                return
            
            st.subheader("近期錯誤統計")
            
            for error_key, stats in error_stats.items():
                col1, col2, col3 = st.columns([3, 1, 2])
                
                with col1:
                    st.write(f"**{error_key}**")
                
                with col2:
                    st.metric("次數", stats['count'])
                
                with col3:
                    last_time = time.strftime('%H:%M:%S', time.localtime(stats['last_occurred']))
                    st.write(f"最後發生: {last_time}")
            
            # 錯誤處理操作
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 重置錯誤計數"):
                    self.error_handler.reset_error_counts()
                    st.success("錯誤計數已重置")
                    st.rerun()
            
            with col2:
                if st.button("📋 導出錯誤日誌"):
                    st.info("錯誤日誌導出功能開發中...")
    
    def show_connection_status(self, connection_manager: ConnectionManager):
        """顯示連接狀態"""
        status = connection_manager.get_connection_status()
        
        if not status:
            return
        
        st.subheader("🔗 連接狀態")
        
        cols = st.columns(len(status))
        
        for i, (service, is_connected) in enumerate(status.items()):
            with cols[i]:
                if is_connected:
                    st.success(f"✅ {service}")
                else:
                    st.error(f"❌ {service}")


# 全局實例
global_error_handler = ErrorHandler()
connection_manager = ConnectionManager(global_error_handler)
error_display = StreamlitErrorDisplay(global_error_handler)


# 便捷裝飾器
def handle_errors(context: str = "Function", fallback_value: Any = None, 
                 max_retries: int = 3):
    """簡化的錯誤處理裝飾器"""
    return global_error_handler.retry_on_error(
        max_retries=max_retries,
        fallback_value=fallback_value,
        context=context
    )

def handle_async_errors(context: str = "AsyncFunction", fallback_value: Any = None, 
                       max_retries: int = 3):
    """簡化的異步錯誤處理裝飾器"""
    return global_error_handler.async_retry_on_error(
        max_retries=max_retries,
        fallback_value=fallback_value,
        context=context
    )


# 測試函數
if __name__ == "__main__":
    # 測試錯誤處理器
    handler = ErrorHandler()
    
    @handler.retry_on_error(max_retries=2, context="Test Function")
    def test_function():
        import random
        if random.random() < 0.7:  # 70%機率失敗
            raise Exception("Random test error")
        return "Success!"
    
    print("Testing error handler...")
    result = test_function()
    print(f"Result: {result}")
    print(f"Error stats: {handler.get_error_stats()}")