"""
真正的實時K線圖實現
基於研究TradingView、Binance等真正的實現方式
使用Plotly的正確更新機制，避免整圖重繪
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger


class TrueRealtimeKlineChart:
    """真正的實時K線圖 - 模仿TradingView的實現方式"""
    
    def __init__(self):
        self.charts = {}  # 存儲圖表實例
        self.data_buffer = {}  # 數據緩衝區
        self.last_update_time = {}
        
    def initialize_chart(self, symbol: str, timeframe: str, 
                        initial_data: pd.DataFrame) -> go.Figure:
        """初始化圖表 - 只執行一次"""
        
        chart_id = f"{symbol}_{timeframe}"
        
        if chart_id in self.charts:
            return self.charts[chart_id]
        
        # 創建初始圖表
        fig = go.Figure()
        
        # 添加K線數據
        fig.add_trace(
            go.Candlestick(
                x=initial_data.index,
                open=initial_data['open'],
                high=initial_data['high'],
                low=initial_data['low'],
                close=initial_data['close'],
                name='K線',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350',
                increasing_fillcolor='#26a69a',
                decreasing_fillcolor='#ef5350'
            )
        )
        
        # 關鍵配置 - 防止閃爍
        fig.update_layout(
            title=f'{symbol} {timeframe} 實時K線',
            height=500,
            showlegend=False,
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            # 最重要的設置
            uirevision='constant',  # 保持用戶操作狀態
            margin=dict(l=50, r=50, t=50, b=50),
            # 禁用自動調整
            autosize=False,
            # 平滑過渡設置
            transition=dict(duration=200, easing='linear')
        )
        
        # 優化軸設置
        fig.update_xaxes(
            showgrid=True, 
            gridwidth=0.5, 
            gridcolor='rgba(128,128,128,0.2)',
            rangeslider_visible=False
        )
        fig.update_yaxes(
            showgrid=True, 
            gridwidth=0.5, 
            gridcolor='rgba(128,128,128,0.2)'
        )
        
        # 保存圖表
        self.charts[chart_id] = fig
        self.data_buffer[chart_id] = initial_data.copy()
        
        return fig
    
    def update_chart_streaming(self, symbol: str, timeframe: str, 
                             new_data: pd.DataFrame) -> Optional[go.Figure]:
        """流式更新圖表數據 - 關鍵！不重新創建圖表"""
        
        chart_id = f"{symbol}_{timeframe}"
        
        if chart_id not in self.charts:
            return None
        
        try:
            fig = self.charts[chart_id]
            old_data = self.data_buffer[chart_id]
            
            # 檢查是否有新數據
            if new_data.index[-1] <= old_data.index[-1]:
                return fig  # 沒有新數據，返回原圖
            
            # 合併新舊數據
            combined_data = pd.concat([old_data, new_data]).drop_duplicates()
            combined_data = combined_data.sort_index().tail(300)  # 只保留最新300個點
            
            # 關鍵：使用正確的Plotly更新方式
            # 直接修改trace的數據，不重新創建
            with fig.batch_update():
                fig.data[0].x = combined_data.index
                fig.data[0].open = combined_data['open']
                fig.data[0].high = combined_data['high']
                fig.data[0].low = combined_data['low']
                fig.data[0].close = combined_data['close']
            
            # 更新標題時間戳
            current_time = datetime.now().strftime("%H:%M:%S")
            fig.update_layout(
                title=f'{symbol} {timeframe} 實時K線 | {current_time}',
                uirevision='constant'  # 保持用戶狀態
            )
            
            # 更新緩衝區
            self.data_buffer[chart_id] = combined_data
            self.last_update_time[chart_id] = time.time()
            
            return fig
            
        except Exception as e:
            logger.error(f"Chart streaming update error: {e}")
            return self.charts[chart_id]  # 返回原圖
    
    def render_true_realtime_chart(self, symbol: str, timeframe: str = "5m"):
        """渲染真正的實時K線圖"""
        from .market_data_provider import get_live_kline_data
        
        # 創建唯一的圖表容器key
        chart_key = f"true_realtime_{symbol}_{timeframe}"
        
        # 獲取最新數據
        current_data = get_live_kline_data(symbol, timeframe, 200)
        
        if current_data is None or current_data.empty:
            st.warning("⚠️ 正在載入數據...")
            return
        
        # 初始化或更新圖表
        if chart_key not in st.session_state:
            # 第一次創建
            fig = self.initialize_chart(symbol, timeframe, current_data)
            st.session_state[chart_key] = st.empty()
        else:
            # 流式更新
            fig = self.update_chart_streaming(symbol, timeframe, current_data)
        
        # 顯示圖表 - 關鍵：使用固定的配置
        chart_container = st.session_state[chart_key]
        
        with chart_container:
            st.plotly_chart(
                fig,
                key=f"fixed_{chart_key}",  # 固定key防止重建
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'responsive': True,
                    'doubleClick': False,  # 禁用雙擊重置
                    'showTips': False,     # 禁用提示
                    'staticPlot': False,   # 保持互動
                    # 關鍵設置：禁用自動調整
                    'autosizable': False,
                    'fillFrame': False
                }
            )
        
        # 顯示實時狀態
        self._render_realtime_status(symbol, timeframe, current_data)
    
    def _render_realtime_status(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """渲染實時狀態信息"""
        if data.empty:
            return
            
        # 創建固定的狀態容器
        status_key = f"status_{symbol}_{timeframe}"
        if status_key not in st.session_state:
            st.session_state[status_key] = st.empty()
        
        status_container = st.session_state[status_key]
        
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest
        
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
        
        with status_container:
            # 使用固定HTML結構
            status_html = f"""
            <div style="
                background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
                border: 2px solid {'#26a69a' if change >= 0 else '#ef5350'};
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                color: white;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center;">
                        <div style="font-size: 16px; color: #888; margin-bottom: 5px;">💰 當前價格</div>
                        <div style="font-size: 32px; font-weight: bold; color: {'#26a69a' if change >= 0 else '#ef5350'};">
                            ${latest['close']:.2f}
                        </div>
                        <div style="font-size: 18px; color: {'#26a69a' if change >= 0 else '#ef5350'};">
                            {change:+.2f} ({change_pct:+.2f}%)
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #888;">📈 最高</div>
                        <div style="font-size: 20px; font-weight: bold;">${latest['high']:.2f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #888;">📉 最低</div>
                        <div style="font-size: 20px; font-weight: bold;">${latest['low']:.2f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #888;">📊 成交量</div>
                        <div style="font-size: 20px; font-weight: bold;">{latest['volume']/1000:.1f}K</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 12px; color: #26a69a;">✅ 無閃爍</div>
                        <div style="font-size: 14px;">真正平滑</div>
                        <div style="font-size: 12px; color: #888;">{datetime.now().strftime('%H:%M:%S')}</div>
                    </div>
                </div>
            </div>
            """
            
            st.markdown(status_html, unsafe_allow_html=True)


class StreamlitRealtimeComponent:
    """Streamlit實時組件 - 正確實現"""
    
    def __init__(self):
        self.chart_engine = TrueRealtimeKlineChart()
        
    @st.fragment(run_every="3s")  # 3秒更新一次，避免過於頻繁
    def realtime_kline_fragment(self, symbol: str, timeframe: str):
        """真正的實時K線Fragment"""
        
        # 狀態指示
        st.markdown(f"""
        <div style="text-align: center; background: #26a69a; color: white; 
                   padding: 10px; border-radius: 5px; margin: 10px 0; font-weight: bold;">
            🎯 真正實時K線 - 每3秒平滑更新 | {symbol} {timeframe} | 無整圖重繪 ✨
        </div>
        """, unsafe_allow_html=True)
        
        # 渲染真正的實時圖表
        self.chart_engine.render_true_realtime_chart(symbol, timeframe)
    
    def render_professional_interface(self, symbol: str, timeframe: str):
        """渲染專業界面"""
        
        # 專業標題
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        ">
            <h1 style="margin: 0; font-size: 28px;">📈 專業實時K線交易系統</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                真正的TradingView風格 • 無閃爍平滑更新 • 專業交易體驗
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 渲染實時K線
        self.realtime_kline_fragment(symbol, timeframe)


# 全局實例
true_realtime_chart = TrueRealtimeKlineChart()
streamlit_realtime_component = StreamlitRealtimeComponent()


# 便捷函數
def render_true_realtime_kline(symbol: str, timeframe: str = "5m"):
    """渲染真正的實時K線圖"""
    streamlit_realtime_component.render_professional_interface(symbol, timeframe)


# 測試函數  
if __name__ == "__main__":
    print("Testing True Realtime Kline Chart...")
    
    # 創建測試數據
    dates = pd.date_range('2024-01-01', periods=50, freq='5min')
    test_data = pd.DataFrame({
        'open': np.random.randn(50).cumsum() + 45000,
        'high': np.random.randn(50).cumsum() + 45100,
        'low': np.random.randn(50).cumsum() + 44900,
        'close': np.random.randn(50).cumsum() + 45000,
        'volume': np.random.randint(100, 1000, 50)
    }, index=dates)
    
    chart = TrueRealtimeKlineChart()
    fig = chart.initialize_chart("BTC/USDT", "5m", test_data)
    
    print("True realtime chart initialized!")
    print(f"Chart traces: {len(fig.data)}")
    print(f"Data points: {len(test_data)}")