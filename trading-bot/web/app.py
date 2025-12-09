"""
AutoTrading Bot Web UI

基於 Streamlit 的交易機器人 Web 介面
整合 TradingView 圖表、OKX API、實時數據與交易指標
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入自定義模組
from core.exchange_okx import OKXExchange
from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
from core.risk import RiskManager, RiskLimits, AccountState
from core.utils_logging import setup_logging, get_logger

# 設置頁面配置
st.set_page_config(
    page_title="AutoTrading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化日誌
setup_logging(log_level="INFO")
logger = get_logger("WebUI")

# 自定義 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1E88E5 0%, #1976D2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }
    
    .sidebar-section {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 應用狀態管理
if 'exchange' not in st.session_state:
    st.session_state.exchange = None
if 'strategy' not in st.session_state:
    st.session_state.strategy = None
if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = None
if 'market_data' not in st.session_state:
    st.session_state.market_data = {}
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False

@st.cache_data
def load_config():
    """載入配置"""
    import yaml
    config_path = project_root / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def init_exchange(api_config):
    """初始化交易所連接"""
    try:
        exchange = OKXExchange({
            'name': 'OKX',
            'api_key': api_config.get('api_key', ''),
            'secret_key': api_config.get('secret_key', ''),
            'passphrase': api_config.get('passphrase', ''),
            'testnet': api_config.get('testnet', True)
        })
        return exchange
    except Exception as e:
        st.error(f"交易所初始化失敗: {e}")
        return None

def init_strategy():
    """初始化策略"""
    config = load_config()
    strategy_config = {
        "name": "ICT_NY_FVG_WebUI",
        "parameters": config.get('strategy', {}).get('parameters', {})
    }
    return ICTNYFVGStrategy(strategy_config)

def init_risk_manager():
    """初始化風險管理器"""
    config = load_config()
    trading_config = config.get('trading', {})
    
    limits = RiskLimits(
        max_risk_per_trade=trading_config.get('risk_per_trade', 0.02),
        max_daily_loss=trading_config.get('max_daily_loss', 0.05),
        max_positions=trading_config.get('max_positions', 3)
    )
    return RiskManager(limits)

async def fetch_market_data(exchange, symbol, timeframe='5m', limit=100):
    """獲取市場數據"""
    try:
        df = await exchange.fetch_ohlcv(symbol, timeframe, limit)
        return df
    except Exception as e:
        st.error(f"獲取市場數據失敗: {e}")
        return None

def create_candlestick_chart(df, title="K線圖"):
    """建立 K 線圖表"""
    if df is None or df.empty:
        return None
        
    fig = go.Figure()
    
    # K線圖
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K線',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))
    
    # 成交量（子圖）
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['volume'],
        name='成交量',
        marker_color='rgba(158,158,158,0.5)',
        yaxis='y2'
    ))
    
    # 布局設定
    fig.update_layout(
        title=title,
        yaxis_title="價格",
        yaxis2=dict(
            title="成交量",
            side="right",
            overlaying="y",
            position=1
        ),
        xaxis_rangeslider_visible=False,
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def create_indicator_chart(df, indicators):
    """建立技術指標圖表"""
    if df is None or df.empty:
        return None
        
    fig = make_subplots(
        rows=len(indicators), 
        cols=1,
        subplot_titles=[ind['name'] for ind in indicators],
        vertical_spacing=0.05,
        shared_xaxes=True
    )
    
    for i, indicator in enumerate(indicators, 1):
        if indicator['type'] == 'line':
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=indicator['data'],
                    name=indicator['name'],
                    line=dict(color=indicator.get('color', '#1f77b4'))
                ),
                row=i, col=1
            )
        elif indicator['type'] == 'bar':
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=indicator['data'],
                    name=indicator['name'],
                    marker_color=indicator.get('color', '#2ca02c')
                ),
                row=i, col=1
            )
    
    fig.update_layout(
        height=200 * len(indicators),
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def main():
    """主應用程式"""
    
    # 標題
    st.markdown('<h1 class="main-header">🤖 AutoTrading Bot</h1>', 
                unsafe_allow_html=True)
    
    # 側邊欄配置
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.header("⚙️ 系統配置")
        
        # API 配置
        st.subheader("🔗 OKX API 設定")
        api_key = st.text_input("API Key", type="password", 
                               help="OKX API 金鑰")
        secret_key = st.text_input("Secret Key", type="password", 
                                  help="OKX API 密鑰")
        passphrase = st.text_input("Passphrase", type="password", 
                                  help="OKX API 通行詞")
        testnet = st.checkbox("測試網", value=True, 
                             help="使用 OKX 測試網")
        
        # 連接按鈕
        if st.button("🔌 連接交易所", type="primary"):
            if api_key and secret_key and passphrase:
                api_config = {
                    'api_key': api_key,
                    'secret_key': secret_key, 
                    'passphrase': passphrase,
                    'testnet': testnet
                }
                st.session_state.exchange = init_exchange(api_config)
                if st.session_state.exchange:
                    st.success("✅ 交易所連接成功!")
                    st.session_state.strategy = init_strategy()
                    st.session_state.risk_manager = init_risk_manager()
            else:
                st.error("❌ 請填入完整的 API 資訊")
        
        # 交易對選擇
        st.subheader("📊 交易對設定")
        symbol = st.selectbox(
            "選擇交易對",
            ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
            help="選擇要監控的交易對"
        )
        
        timeframe = st.selectbox(
            "時間框架",
            ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"],
            index=2,  # 預設 5m
            help="K線時間間隔"
        )
        
        # 策略控制
        st.subheader("🎯 策略控制")
        if st.button("▶️ 啟動交易", type="primary"):
            if st.session_state.exchange:
                st.session_state.trading_active = True
                st.success("🚀 自動交易已啟動")
            else:
                st.error("❌ 請先連接交易所")
                
        if st.button("⏹️ 停止交易"):
            st.session_state.trading_active = False
            st.info("🛑 自動交易已停止")
        
        # 系統狀態
        st.subheader("📊 系統狀態")
        if st.session_state.exchange:
            st.markdown(
                '<span class="status-indicator status-online"></span>交易所: 已連接',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span class="status-indicator status-offline"></span>交易所: 未連接',
                unsafe_allow_html=True
            )
            
        if st.session_state.trading_active:
            st.markdown(
                '<span class="status-indicator status-online"></span>策略: 運行中',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span class="status-indicator status-offline"></span>策略: 已停止',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 主要內容區域
    if st.session_state.exchange:
        # 頂部指標卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "當前價格",
                "Loading...",
                delta="Loading...",
                help="最新成交價格"
            )
            
        with col2:
            st.metric(
                "24h 漲跌",
                "Loading...",
                delta="Loading...",
                help="24小時價格變動"
            )
            
        with col3:
            st.metric(
                "24h 成交量",
                "Loading...",
                help="24小時成交量"
            )
            
        with col4:
            st.metric(
                "帳戶餘額",
                "Loading...",
                help="可用餘額"
            )
        
        # 圖表區域
        chart_tab1, chart_tab2, chart_tab3 = st.tabs(["📈 價格圖表", "📊 技術指標", "🎯 策略信號"])
        
        with chart_tab1:
            st.subheader(f"🕯️ {symbol} K線圖")
            
            # 獲取數據按鈕
            if st.button("🔄 刷新數據"):
                with st.spinner("正在獲取市場數據..."):
                    # 這裡需要在實際應用中使用異步函數
                    st.info("數據刷新功能需要後端支援，請稍後...")
            
            # 模擬數據展示
            @st.cache_data
            def get_sample_data():
                dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
                np.random.seed(42)
                prices = 45000 + np.cumsum(np.random.randn(100) * 50)
                
                return pd.DataFrame({
                    'open': prices,
                    'high': prices + np.random.uniform(10, 100, 100),
                    'low': prices - np.random.uniform(10, 100, 100),
                    'close': prices + np.random.uniform(-50, 50, 100),
                    'volume': np.random.uniform(100, 1000, 100)
                }, index=dates)
            
            sample_data = get_sample_data()
            chart = create_candlestick_chart(sample_data, f"{symbol} {timeframe}")
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        
        with chart_tab2:
            st.subheader("📈 技術指標")
            
            # 指標選擇
            col1, col2 = st.columns(2)
            with col1:
                show_rsi = st.checkbox("RSI", value=True)
                show_macd = st.checkbox("MACD", value=True)
            with col2:
                show_ma = st.checkbox("移動平均線", value=True)
                show_bb = st.checkbox("布林帶", value=False)
            
            # 模擬指標數據
            if show_rsi or show_macd or show_ma:
                sample_data = get_sample_data()
                
                if show_rsi:
                    st.subsubheader("RSI (相對強弱指標)")
                    rsi_data = np.random.uniform(30, 70, len(sample_data))
                    rsi_fig = px.line(
                        x=sample_data.index, 
                        y=rsi_data,
                        title="RSI"
                    )
                    rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超買")
                    rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超賣")
                    rsi_fig.update_layout(height=300)
                    st.plotly_chart(rsi_fig, use_container_width=True)
                
                if show_macd:
                    st.subsubheader("MACD")
                    macd_line = np.random.uniform(-100, 100, len(sample_data))
                    signal_line = macd_line * 0.8
                    histogram = macd_line - signal_line
                    
                    macd_fig = go.Figure()
                    macd_fig.add_trace(go.Scatter(
                        x=sample_data.index, y=macd_line, name='MACD',
                        line=dict(color='blue')
                    ))
                    macd_fig.add_trace(go.Scatter(
                        x=sample_data.index, y=signal_line, name='Signal',
                        line=dict(color='red')
                    ))
                    macd_fig.add_trace(go.Bar(
                        x=sample_data.index, y=histogram, name='Histogram',
                        marker_color='gray'
                    ))
                    macd_fig.update_layout(height=300, title="MACD")
                    st.plotly_chart(macd_fig, use_container_width=True)
        
        with chart_tab3:
            st.subheader("🎯 ICT NY FVG 策略信號")
            
            if st.session_state.strategy:
                # 策略參數顯示
                st.write("**策略參數:**")
                params = st.session_state.strategy.parameters
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("交易時段", f"{params.get('session_start')} - {params.get('session_end')}")
                with col2:
                    st.metric("風險收益比", f"1:{params.get('risk_reward_ratio', 3)}")
                with col3:
                    st.metric("FVG 大小", f"{params.get('min_fvg_size_pips')} - {params.get('max_fvg_size_pips')} pips")
                
                # 信號歷史
                st.write("**最近信號:**")
                signal_data = {
                    '時間': ['2024-01-01 10:30', '2024-01-01 11:15', '2024-01-01 14:20'],
                    '類型': ['LONG', 'SHORT', 'LONG'],
                    '進場價': ['$45,250', '$45,180', '$45,320'],
                    '止損': ['$45,100', '$45,280', '$45,200'],
                    '止盈': ['$45,550', '$44,880', '$45,680'],
                    '狀態': ['已平倉 (+$150)', '已平倉 (-$50)', '持倉中']
                }
                signal_df = pd.DataFrame(signal_data)
                st.dataframe(signal_df, use_container_width=True)
        
        # 底部交易面板
        st.header("💼 交易控制面板")
        
        trade_tab1, trade_tab2, trade_tab3 = st.tabs(["📋 當前持倉", "📈 交易歷史", "⚖️ 風險管理"])
        
        with trade_tab1:
            st.subheader("當前持倉")
            
            # 模擬持倉數據
            position_data = {
                '交易對': ['BTC/USDT'],
                '方向': ['多頭'],
                '數量': ['0.1 BTC'],
                '進場價': ['$45,200'],
                '當前價': ['$45,350'],
                '未實現盈虧': ['+$15.00'],
                '盈虧%': ['+0.33%']
            }
            if position_data['交易對']:
                position_df = pd.DataFrame(position_data)
                st.dataframe(position_df, use_container_width=True)
            else:
                st.info("目前沒有持倉")
        
        with trade_tab2:
            st.subheader("交易歷史")
            
            # 模擬交易歷史
            history_data = {
                '時間': pd.date_range('2024-01-01', periods=5, freq='D'),
                '交易對': ['BTC/USDT'] * 5,
                '方向': ['多頭', '空頭', '多頭', '多頭', '空頭'],
                '數量': ['0.1', '0.15', '0.08', '0.12', '0.1'],
                '進場價': ['$44,800', '$45,200', '$45,500', '$45,100', '$45,300'],
                '出場價': ['$45,100', '$44,950', '$45,650', '$45,380', '$45,150'],
                '盈虧': ['+$30', '+$37.5', '+$12', '+$33.6', '+$15'],
                '手續費': ['$0.90', '$1.35', '$0.72', '$1.08', '$0.90']
            }
            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True)
            
            # 績效統計
            st.subheader("📊 績效統計")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總盈虧", "+$128.1", "+2.8%")
            with col2:
                st.metric("勝率", "80%", "+10%")
            with col3:
                st.metric("平均盈虧", "+$25.6", "+5%")
            with col4:
                st.metric("最大回撤", "-1.2%", "+0.5%")
        
        with trade_tab3:
            st.subheader("⚖️ 風險管理")
            
            if st.session_state.risk_manager:
                # 風險參數調整
                col1, col2 = st.columns(2)
                with col1:
                    risk_per_trade = st.slider(
                        "單筆風險比例 (%)",
                        min_value=0.1, max_value=5.0, 
                        value=2.0, step=0.1
                    )
                    max_positions = st.slider(
                        "最大持倉數量",
                        min_value=1, max_value=10,
                        value=3, step=1
                    )
                
                with col2:
                    max_daily_loss = st.slider(
                        "單日最大虧損 (%)",
                        min_value=1.0, max_value=20.0,
                        value=5.0, step=0.5
                    )
                    min_rr_ratio = st.slider(
                        "最小風險收益比",
                        min_value=1.0, max_value=5.0,
                        value=2.0, step=0.1
                    )
                
                # 當日風險狀況
                st.subheader("當日風險狀況")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("已用風險", "1.2%", help="當日已承擔的風險")
                with col2:
                    st.metric("剩餘風險", "3.8%", help="當日剩餘可承擔風險")
                with col3:
                    st.metric("當前持倉", "1", help="目前持倉數量")
                
                # 風險警告
                if risk_per_trade > 3.0:
                    st.warning("⚠️ 單筆風險過高，建議降低至 2% 以下")
                if max_daily_loss > 10.0:
                    st.warning("⚠️ 單日最大虧損設定過高，建議控制在 5% 以內")
    
    else:
        # 未連接交易所時的歡迎頁面
        st.info("👈 請在左側邊欄配置 OKX API 並連接交易所以開始使用")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("https://via.placeholder.com/400x300/1E88E5/FFFFFF?text=AutoTrading+Bot", 
                    caption="自動化交易機器人")
        
        st.markdown("""
        ### 🚀 功能特色
        
        - **📊 實時市場數據**: 整合 OKX API 獲取即時行情
        - **📈 TradingView 圖表**: 專業的 K 線圖表與技術指標
        - **🤖 ICT 策略**: 基於 Smart Money Concepts 的自動交易策略
        - **⚖️ 風險管理**: 完善的倉位管理與風險控制
        - **📱 實時監控**: WebSocket 即時數據更新
        - **🔔 智能通知**: Telegram/Discord 交易通知
        
        ### 📋 使用步驟
        
        1. **配置 API**: 在左側邊欄輸入 OKX API 資訊
        2. **選擇交易對**: 選擇要監控的加密貨幣交易對
        3. **啟動策略**: 點擊啟動按鈕開始自動交易
        4. **監控交易**: 實時查看持倉、盈虧與風險狀況
        
        ### ⚠️ 風險提示
        
        - 加密貨幣交易具有高風險，請謹慎投資
        - 建議先在測試網環境熟悉操作
        - 請設定合適的風險參數並嚴格執行
        """)

if __name__ == "__main__":
    main()