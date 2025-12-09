"""
平滑K線更新器 - 實現TradingView風格的平滑更新
只更新K棒數據，不重繪整個圖表，避免閃爍
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


class SmoothKlineUpdater:
    """平滑K線更新器 - 像TradingView一樣的平滑更新"""
    
    def __init__(self):
        self.chart_data_cache = {}
        self.last_prices = {}
        self.chart_configs = {}
        self.update_counters = {}
        
    def create_persistent_chart(self, symbol: str, timeframe: str, 
                               initial_data: pd.DataFrame, height: int = 600) -> str:
        """創建持久化圖表，只初始化一次"""
        chart_id = f"{symbol}_{timeframe}"
        
        if chart_id not in self.chart_data_cache:
            # 只在第一次創建圖表
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=[f'{symbol} {timeframe} 平滑實時K線', '成交量'],
                row_heights=[0.75, 0.25],
                vertical_spacing=0.08,
                shared_xaxes=True
            )
            
            # K線圖
            fig.add_trace(
                go.Candlestick(
                    x=initial_data.index,
                    open=initial_data['open'],
                    high=initial_data['high'],
                    low=initial_data['low'],
                    close=initial_data['close'],
                    name='K線',
                    increasing_line_color='#00ff88',
                    decreasing_line_color='#ff4444',
                    increasing_fillcolor='rgba(0,255,136,0.8)',
                    decreasing_fillcolor='rgba(255,68,68,0.8)'
                ),
                row=1, col=1
            )
            
            # 成交量
            colors = ['#00ff88' if close >= open else '#ff4444' 
                     for close, open in zip(initial_data['close'], initial_data['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=initial_data.index,
                    y=initial_data['volume'],
                    name='成交量',
                    marker_color=colors,
                    opacity=0.6,
                    showlegend=False
                ),
                row=2, col=1
            )
            
            # 優化布局 - 重點：固定配置避免重繪
            fig.update_layout(
                title=f'📊 {symbol} 平滑實時K線 - {timeframe}',
                height=height,
                showlegend=False,
                xaxis_rangeslider_visible=False,
                template='plotly_dark',
                margin=dict(l=50, r=50, t=70, b=50),
                # 關鍵優化設置
                uirevision='constant',  # 保持用戶縮放和平移狀態
                transition={'duration': 300, 'easing': 'cubic-in-out'},  # 平滑過渡
                hovermode='x unified'
            )
            
            # 優化軸設置
            fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128,128,128,0.2)')
            
            # 保存圖表配置
            self.chart_data_cache[chart_id] = {
                'figure': fig,
                'last_data': initial_data,
                'created_time': time.time()
            }
            
            self.update_counters[chart_id] = 0
            
        return chart_id
    
    def update_chart_data_only(self, chart_id: str, new_data: pd.DataFrame) -> bool:
        """只更新圖表數據，不重新創建圖表"""
        if chart_id not in self.chart_data_cache:
            return False
        
        try:
            cached_chart = self.chart_data_cache[chart_id]
            fig = cached_chart['figure']
            last_data = cached_chart['last_data']
            
            # 檢查是否有新數據
            if new_data.index[-1] <= last_data.index[-1]:
                return False  # 沒有新數據
            
            # 更新K線數據 - 使用Plotly的restyle方法
            fig.data[0].x = new_data.index
            fig.data[0].open = new_data['open']
            fig.data[0].high = new_data['high'] 
            fig.data[0].low = new_data['low']
            fig.data[0].close = new_data['close']
            
            # 更新成交量數據
            colors = ['#00ff88' if close >= open else '#ff4444' 
                     for close, open in zip(new_data['close'], new_data['open'])]
            
            fig.data[1].x = new_data.index
            fig.data[1].y = new_data['volume']
            fig.data[1].marker.color = colors
            
            # 更新標題時間戳
            current_time = datetime.now().strftime("%H:%M:%S")
            symbol = chart_id.split('_')[0]
            timeframe = chart_id.split('_')[1]
            fig.update_layout(
                title=f'📊 {symbol} 平滑實時K線 - {timeframe} | {current_time}',
                uirevision='constant'  # 保持用戶操作狀態
            )
            
            # 更新快取
            self.chart_data_cache[chart_id]['last_data'] = new_data
            self.update_counters[chart_id] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Chart data update error: {e}")
            return False
    
    def render_smooth_kline_chart(self, symbol: str, timeframe: str = "5m"):
        """渲染平滑更新的K線圖表"""
        from .market_data_provider import get_live_kline_data
        
        chart_id = f"{symbol}_{timeframe}"
        
        # 獲取數據
        current_data = get_live_kline_data(symbol, timeframe, 200)
        
        if current_data is None or current_data.empty:
            st.warning("⚠️ 正在載入數據...")
            return
        
        # 創建或獲取圖表容器
        if f"smooth_chart_{chart_id}" not in st.session_state:
            st.session_state[f"smooth_chart_{chart_id}"] = st.empty()
        
        chart_container = st.session_state[f"smooth_chart_{chart_id}"]
        
        # 檢查是否需要初始化圖表
        if chart_id not in self.chart_data_cache:
            # 第一次創建圖表
            self.create_persistent_chart(symbol, timeframe, current_data)
            
            with chart_container:
                st.plotly_chart(
                    self.chart_data_cache[chart_id]['figure'],
                    key=f"smooth_{chart_id}",
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'staticPlot': False,
                        'responsive': True,
                        # 關鍵：禁用自動調整以避免重繪
                        'autosizable': False,
                        'frameMargins': 0
                    }
                )
        else:
            # 只更新數據，不重新創建圖表
            data_updated = self.update_chart_data_only(chart_id, current_data)
            
            if data_updated:
                # 使用st.empty()的特性，只更新內容不重建容器
                with chart_container:
                    # 重要：使用相同的key和config避免重建
                    st.plotly_chart(
                        self.chart_data_cache[chart_id]['figure'],
                        key=f"smooth_{chart_id}",  # 固定key
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'staticPlot': False,
                            'responsive': True,
                            'autosizable': False,
                            'frameMargins': 0
                        }
                    )
        
        # 顯示最新價格資訊 - 使用固定容器避免閃爍
        self._render_price_info(symbol, current_data)
    
    def _render_price_info(self, symbol: str, data: pd.DataFrame):
        """渲染價格信息 - 固定容器避免閃爍"""
        info_key = f"price_info_{symbol}"
        
        if f"price_container_{info_key}" not in st.session_state:
            st.session_state[f"price_container_{info_key}"] = st.empty()
        
        price_container = st.session_state[f"price_container_{info_key}"]
        
        if not data.empty:
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            
            change = latest['close'] - prev['close']
            change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
            
            with price_container:
                # 使用固定的HTML結構避免重排
                price_html = f"""
                <div style="display: flex; justify-content: space-around; background: #1e1e1e; 
                           padding: 15px; border-radius: 10px; margin: 10px 0;">
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 14px; color: #888;">💰 實時價格</div>
                        <div style="font-size: 24px; font-weight: bold; color: {'#00ff88' if change >= 0 else '#ff4444'};">
                            ${latest['close']:.4f}
                        </div>
                        <div style="font-size: 16px; color: {'#00ff88' if change >= 0 else '#ff4444'};">
                            {change:+.4f} ({change_pct:+.2f}%)
                        </div>
                    </div>
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 14px; color: #888;">📈 24h最高</div>
                        <div style="font-size: 18px; font-weight: bold;">${latest['high']:.4f}</div>
                    </div>
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 14px; color: #888;">📉 24h最低</div>
                        <div style="font-size: 18px; font-weight: bold;">${latest['low']:.4f}</div>
                    </div>
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 14px; color: #888;">📊 成交量</div>
                        <div style="font-size: 18px; font-weight: bold;">{latest['volume']/1000:.1f}K</div>
                    </div>
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 12px; color: #00ff88;">🚀 平滑更新</div>
                        <div style="font-size: 14px;">無閃爍模式</div>
                    </div>
                </div>
                """
                
                st.markdown(price_html, unsafe_allow_html=True)


class TradingViewStyleUpdater:
    """TradingView風格更新器"""
    
    def __init__(self):
        self.smooth_updater = SmoothKlineUpdater()
        self.last_update_time = {}
        
    @st.fragment(run_every="2s")  # 降低更新頻率避免閃爍
    def smooth_kline_fragment(self, symbol: str, timeframe: str):
        """平滑K線Fragment - TradingView風格"""
        
        # 顯示平滑更新狀態
        status_container_key = f"status_{symbol}_{timeframe}"
        if status_container_key not in st.session_state:
            st.session_state[status_container_key] = st.empty()
        
        with st.session_state[status_container_key]:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"""
            <div style="text-align: center; background: linear-gradient(90deg, #00ff88, #00cc66); 
                       padding: 8px; border-radius: 5px; color: white; font-weight: bold; margin: 10px 0;">
                🔄 TradingView風格平滑更新 | {current_time} | 無整圖重繪 ✨
            </div>
            """, unsafe_allow_html=True)
        
        # 渲染平滑更新的K線圖
        self.smooth_updater.render_smooth_kline_chart(symbol, timeframe)
    
    @st.fragment(run_every="3s")  # 多交易對更新頻率
    def smooth_multi_ticker_fragment(self, symbols: List[str]):
        """平滑多交易對Fragment"""
        from .market_data_provider import get_multiple_tickers_data
        
        # 固定容器避免重排
        if "multi_ticker_container" not in st.session_state:
            st.session_state.multi_ticker_container = st.empty()
        
        with st.session_state.multi_ticker_container:
            current_timestamp = int(time.time())
            tickers_data = get_multiple_tickers_data(symbols, _force_refresh=current_timestamp)
            
            if tickers_data:
                # 使用固定的HTML布局避免重排
                ticker_cards = []
                
                for symbol in symbols:
                    if symbol in tickers_data:
                        ticker = tickers_data[symbol]
                        price = ticker['last_price']
                        change = ticker['change_24h']
                        
                        card_html = f"""
                        <div style="background: {'linear-gradient(135deg, #00ff88, #00cc66)' if change >= 0 else 'linear-gradient(135deg, #ff4444, #cc3333)'};
                                   color: white; padding: 20px; border-radius: 15px; margin: 10px;
                                   text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                                   min-width: 200px;">
                            <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">
                                {'🟢' if change >= 0 else '🔴'} {symbol.replace('/', '')}
                            </div>
                            <div style="font-size: 28px; font-weight: bold; margin: 10px 0;">
                                ${price:,.4f}
                            </div>
                            <div style="font-size: 18px;">
                                {change:+.2f}%
                            </div>
                        </div>
                        """
                        ticker_cards.append(card_html)
                
                # 組合所有卡片
                combined_html = f"""
                <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;">
                    {''.join(ticker_cards)}
                </div>
                """
                
                st.markdown(combined_html, unsafe_allow_html=True)
            else:
                st.info("正在載入多交易對數據...")
    
    def render_tradingview_style_interface(self, symbol: str, timeframe: str):
        """渲染TradingView風格界面"""
        
        # 標題和控制
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1a1a1a, #2d2d2d); 
                   padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0; text-align: center;">
                📈 {symbol} TradingView風格實時K線 - {timeframe}
            </h2>
            <p style="color: #888; text-align: center; margin: 10px 0 0 0;">
                ✨ 平滑更新 • 無閃爍 • 只更新K棒數據 • 保持用戶操作狀態
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 主圖表區域
        self.smooth_kline_fragment(symbol, timeframe)
        
        st.divider()
        
        # 多交易對監控
        st.markdown("### 📊 多交易對實時監控")
        self.smooth_multi_ticker_fragment(["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"])


# 全局實例
smooth_kline_updater = SmoothKlineUpdater() 
tradingview_style_updater = TradingViewStyleUpdater()


# 便捷函數
def render_tradingview_kline(symbol: str, timeframe: str = "5m"):
    """渲染TradingView風格的K線圖"""
    tradingview_style_updater.render_tradingview_style_interface(symbol, timeframe)


# 測試函數
if __name__ == "__main__":
    print("Testing Smooth Kline Updater...")
    
    # 創建測試數據
    import pandas as pd
    from datetime import datetime, timedelta
    
    dates = pd.date_range('2024-01-01', periods=100, freq='5min')
    test_data = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 45000,
        'high': np.random.randn(100).cumsum() + 45100,
        'low': np.random.randn(100).cumsum() + 44900,
        'close': np.random.randn(100).cumsum() + 45000,
        'volume': np.random.randint(100, 1000, 100)
    }, index=dates)
    
    updater = SmoothKlineUpdater()
    chart_id = updater.create_persistent_chart("BTC/USDT", "5m", test_data)
    
    print(f"Chart created: {chart_id}")
    print("Smooth updater ready!")