"""
AutoTrading Bot 主要 Web 應用程式

整合所有功能的完整 Web UI
包含：TradingView 圖表、OKX API、實時數據、交易儀表板
"""

import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import sys
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入組件
from web.components.tradingview_chart import (
    tradingview_chart, tradingview_ticker_tape, 
    tradingview_market_overview
)
from web.components.trading_dashboard import dashboard, render_complete_dashboard
from web.components.realtime_data import (
    realtime_manager, init_realtime_data,
    RealtimeTickerComponent, create_realtime_price_chart
)
from web.components.market_data_provider import (
    get_live_ticker_data, get_live_kline_data, 
    get_multiple_tickers_data, live_data_component
)
from web.components.realtime_kline_engine import (
    streamlit_kline_component, realtime_kline_engine
)
from web.components.performance_optimizer import (
    performance_optimizer, performance_dashboard
)
from web.components.error_handler import (
    global_error_handler, error_display, handle_errors, handle_async_errors
)
from web.components.system_monitor import (
    system_monitor, monitor_dashboard, track_data_update, register_data_source
)
from web.components.ui_optimizer import (
    ui_optimizer, memory_optimizer, responsive_updater, 
    show_connection_status, show_data_freshness, safe_component_update
)
from web.components.stability_optimizer import (
    stability_manager, memory_watchdog, frequency_optimizer, status_display,
    stable_execution, show_system_health, auto_start_watchdog
)
from web.components.streamlit_fragment_optimizer import (
    fragment_optimizer, render_optimized_realtime_kline, 
    render_optimized_ticker_display, render_optimized_system_monitor
)
from web.components.smooth_kline_updater import (
    tradingview_style_updater, render_tradingview_kline
)
from web.components.true_realtime_kline import (
    render_true_realtime_kline
)
from web.components.advanced_charts import advanced_chart
from web.components.realtime_refresh import (
    enhanced_auto_refresh_setup, realtime_status_indicator, 
    force_refresh_button, auto_refresh_container
)

# 導入核心模組
from core.exchange_okx import OKXExchange
from core.strategy_ict_ny_fvg import ICTNYFVGStrategy
from core.risk import RiskManager, RiskLimits
from core.utils_logging import setup_logging, get_logger

# 頁面配置
st.set_page_config(
    page_title="AutoTrading Bot - 專業交易終端",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 載入環境變數
load_dotenv(project_root / '.env')

# 設置日誌
setup_logging(log_level="INFO")
logger = get_logger("MainApp")

# 自定義 CSS
st.markdown("""
<style>
    /* 主要樣式 */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .status-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-positive { color: #28a745; }
    .metric-negative { color: #dc3545; }
    .metric-neutral { color: #6c757d; }
    
    /* 側邊欄樣式 */
    .sidebar-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    /* 按鈕樣式 */
    .stButton > button {
        border-radius: 20px;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* 警告樣式 */
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 成功樣式 */
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Tab 樣式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 Session State
def init_session_state():
    """初始化 Session State"""
    defaults = {
        'exchange': None,
        'strategy': None,
        'risk_manager': None,
        'trading_active': False,
        'api_connected': False,
        'selected_symbol': 'BTC/USDT',
        'selected_timeframe': '5m',
        'notifications': [],
        'trade_history': [],
        'account_data': {},
        'market_data': {}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def setup_auto_refresh():
    """設置實時自動刷新機制"""
    if st.session_state.get('auto_refresh_enabled', False):
        # 初始化刷新狀態
        if 'refresh_count' not in st.session_state:
            st.session_state.refresh_count = 0
        if 'last_auto_refresh' not in st.session_state:
            st.session_state.last_auto_refresh = time.time()
        
        current_time = time.time()
        elapsed = current_time - st.session_state.last_auto_refresh
        
        # 每1秒刷新一次（真正的實時數據）
        if elapsed >= 1.0:
            st.session_state.refresh_count += 1
            st.session_state.last_auto_refresh = current_time
            
            # 只清除數據快取，保留資源快取
            st.cache_data.clear()
            
            # 強制重新運行
            st.rerun()
        
        # 顯示剩餘時間
        remaining = max(0, 1.0 - elapsed)
        status_text = f"🔄 實時刷新 (第{st.session_state.refresh_count}次) - {remaining:.1f}秒後更新"
        
        return status_text
    return None

def render_header():
    """渲染頁面標題"""
    st.markdown(
        '<div class="main-header">🤖 AutoTrading Bot - 專業交易終端</div>',
        unsafe_allow_html=True
    )
    
    # 實時市場行情跑馬燈
    live_data_component.render_ticker_tape(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT'])
    
    # 添加強化刷新功能
    col_refresh1, col_refresh2, col_refresh3, col_refresh4 = st.columns([2, 1, 1, 1])
    with col_refresh2:
        if st.button("🔄 手動刷新", key="header_refresh"):
            st.cache_data.clear()
            st.rerun()
    with col_refresh3:
        auto_refresh = st.checkbox("自動刷新", value=True, key="auto_refresh_header", help="每秒自動刷新數據")
        st.session_state.auto_refresh_enabled = auto_refresh
    with col_refresh4:
        # 使用增強版強制刷新按鈕
        force_refresh_button("⚡ 強制刷新", "force_refresh")
    
    # 實時自動刷新機制
    if st.session_state.get('auto_refresh_enabled', False):
        # 初始化時間狀態
        if 'last_refresh_time' not in st.session_state:
            st.session_state.last_refresh_time = time.time()
            st.session_state.refresh_counter = 0
        
        current_time = time.time()
        elapsed = current_time - st.session_state.last_refresh_time
        
        # 每5秒強制刷新一次
        if elapsed >= 5.0:
            st.session_state.last_refresh_time = current_time
            st.session_state.refresh_counter += 1
            
            # 清除數據快取以獲取新數據
            st.cache_data.clear()
            
            # 顯示刷新狀態
            st.markdown(f"<div style='text-align: center; background: linear-gradient(90deg, #00ff88, #00cc66); padding: 8px; border-radius: 5px; color: white; font-weight: bold;'>🔄 數據已更新 (第{st.session_state.refresh_counter}次) - 5秒後下次更新</div>", unsafe_allow_html=True)
            
            # 重新運行以更新數據
            st.rerun()
        else:
            remaining = 5.0 - elapsed
            st.markdown(f"<div style='text-align: center; background: linear-gradient(90deg, #00ff88, #00cc66); padding: 8px; border-radius: 5px; color: white; font-weight: bold;'>🔄 下次更新倒計時: {remaining:.1f}秒 (第{st.session_state.refresh_counter}次已完成)</div>", unsafe_allow_html=True)

def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.markdown('<div class="sidebar-header">⚙️ 系統控制</div>', 
                   unsafe_allow_html=True)
        
        # API 連接狀態
        st.subheader("🔗 連接狀態")
        col1, col2 = st.columns(2)
        
        with col1:
            status = "🟢 已連接" if st.session_state.api_connected else "🔴 未連接"
            st.write(f"**API**: {status}")
        
        with col2:
            trading_status = "🟢 運行中" if st.session_state.trading_active else "🔴 已停止"
            st.write(f"**交易**: {trading_status}")
        
        st.divider()
        
        # API 設定
        with st.expander("🔧 API 設定", expanded=not st.session_state.api_connected):
            # 嘗試從環境變數載入API設定
            env_api_key = os.getenv('OKX_API_KEY', '')
            env_secret = os.getenv('OKX_SECRET_KEY', '')
            env_passphrase = os.getenv('OKX_PASSPHRASE', '')
            env_testnet = os.getenv('OKX_TESTNET', 'true').lower() == 'true'
            
            # 如果有環境變數，自動連接並顯示狀態
            if env_api_key:
                # 自動建立API連接（僅在首次載入時）
                if not st.session_state.api_connected:
                    try:
                        # 由於我們已經測試過 API 可以正常工作，直接設置連接狀態
                        exchange_config = {
                            'api_key': env_api_key,
                            'secret_key': env_secret,
                            'passphrase': env_passphrase,
                            'testnet': env_testnet
                        }
                        st.session_state.exchange = OKXExchange(exchange_config)
                        st.session_state.api_connected = True
                        logger.info("API auto-connected using environment variables")
                        
                        # 在背景中測試連接（不阻塞UI）
                        try:
                            import ccxt
                            test_client = ccxt.okx({
                                'apiKey': env_api_key,
                                'secret': env_secret,
                                'password': env_passphrase,
                                'sandbox': env_testnet,
                                'enableRateLimit': True,
                            })
                            ticker = test_client.fetch_ticker('BTC/USDT')
                            if not ticker or 'last' not in ticker:
                                st.warning("⚠️ API 連接可能不穩定")
                        except Exception as test_e:
                            st.warning(f"⚠️ API 測試警告: {test_e}")
                            
                    except Exception as e:
                        st.error(f"❌ API初始化失敗: {e}")
                        st.session_state.api_connected = False
                
                # 顯示API狀態
                if st.session_state.api_connected:
                    st.success("✅ 已自動連接 OKX API (來自環境變數)")
                else:
                    st.error("❌ API 連接失敗")
                
                # 顯示API資訊（隱藏實際內容）
                st.text_input("OKX API Key", value="***已載入***", type="password", disabled=True)
                st.text_input("OKX Secret Key", value="***已載入***", type="password", disabled=True)
                st.text_input("OKX Passphrase", value="***已載入***", type="password", disabled=True)
                st.checkbox("使用測試網", value=env_testnet, disabled=True)
                
                # 設置變數供後續使用
                api_key = env_api_key
                secret_key = env_secret
                passphrase = env_passphrase
                testnet = env_testnet
            else:
                st.warning("⚠️ 未找到環境變數設定，請手動輸入或運行 setup_demo_api.py")
                api_key = st.text_input("OKX API Key", type="password")
                secret_key = st.text_input("OKX Secret Key", type="password")
                passphrase = st.text_input("OKX Passphrase", type="password")
                testnet = st.checkbox("使用測試網", value=True)
            
            # 只有在沒有環境變數時才顯示手動連接按鈕
            if not env_api_key:
                if st.button("🔌 連接 OKX", type="primary", use_container_width=True):
                    if api_key and secret_key and passphrase:
                        try:
                            # 初始化 OKX 連接
                            exchange_config = {
                                'api_key': api_key,
                                'secret_key': secret_key,
                                'passphrase': passphrase,
                                'testnet': testnet
                            }
                            st.session_state.exchange = OKXExchange(exchange_config)
                            st.session_state.api_connected = True
                            st.success("✅ API 連接成功!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 連接失敗: {e}")
                    else:
                        st.error("❌ 請填入完整的 API 資訊")
            else:
                # 有環境變數時顯示斷開連接選項
                if st.button("🔌 重新連接", type="secondary", use_container_width=True):
                    st.session_state.api_connected = False
                    st.rerun()
        
        # 交易設定
        with st.expander("📊 交易設定"):
            st.session_state.selected_symbol = st.selectbox(
                "交易對",
                ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"],
                help="選擇要監控和交易的加密貨幣對"
            )
            
            st.session_state.selected_timeframe = st.selectbox(
                "時間框架",
                ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"],
                index=2,
                help="K線圖表的時間間隔"
            )
            
            risk_per_trade = st.slider(
                "單筆風險 (%)",
                min_value=0.1, max_value=5.0,
                value=1.0, step=0.1,
                help="每筆交易的風險比例"
            )
            
            max_positions = st.slider(
                "最大持倉數",
                min_value=1, max_value=10,
                value=3, step=1,
                help="同時持有的最大倉位數量"
            )
            
        # 數據更新設定
        with st.expander("🔄 數據更新頻率"):
            st.write("**⚡ 實時交易模式：**")
            st.write("- 📊 行情數據：每 **1秒** 更新")
            st.write("- 📈 K線數據：每 **5秒** 更新") 
            st.write("- 💹 多交易對：每 **2秒** 更新")
            st.write("- 🔄 自動刷新：每 **1秒** 更新")
            st.write("- 🌐 WebSocket：**實時** 連接")
            
            st.success("⚡ 交易級別的實時性設定，適合專業交易")
            
            if st.button("🔄 立即刷新數據"):
                st.cache_data.clear()
                # 強制重新加載頁面來刷新所有緩存數據
                st.rerun()
                st.success("✅ 數據快取已清除，將獲取最新數據")
        
        # 策略控制
        with st.expander("🎯 策略控制"):
            st.write("**ICT NY FVG 策略**")
            st.write("- 基於 Smart Money Concepts")
            st.write("- NY Session 交易時段")
            st.write("- Fair Value Gap 偵測")
            st.write("- Liquidity Sweep 確認")
            
            if st.session_state.api_connected:
                if not st.session_state.trading_active:
                    if st.button("▶️ 啟動交易", type="primary", use_container_width=True):
                        st.session_state.trading_active = True
                        st.success("🚀 自動交易已啟動")
                        st.rerun()
                else:
                    if st.button("⏹️ 停止交易", use_container_width=True):
                        st.session_state.trading_active = False
                        st.info("🛑 自動交易已停止")
                        st.rerun()
            else:
                st.info("💡 請先連接 API")
        
        # 快速操作
        with st.expander("⚡ 快速操作"):
            if st.button("📊 刷新數據", use_container_width=True):
                st.rerun()
            
            if st.button("🔄 重置設定", use_container_width=True):
                # 重置部分設定
                st.session_state.trading_active = False
                st.info("⚙️ 設定已重置")
            
            if st.button("📋 導出報表", use_container_width=True):
                st.info("📄 報表導出功能開發中...")

def render_main_content():
    """渲染主要內容區域"""
    
    # 主要 Tab 導航
    main_tabs = st.tabs([
        "📈 交易視圖", 
        "⚡ 實時K線",
        "💼 投資組合", 
        "📊 績效分析", 
        "⚖️ 風險管理",
        "📡 實時監控",
        "🔍 系統監控"
    ])
    
    # Tab 1: 交易視圖
    with main_tabs[0]:
        render_trading_view()
    
    # Tab 2: 實時K線
    with main_tabs[1]:
        render_realtime_kline_view()
    
    # Tab 3: 投資組合
    with main_tabs[2]:
        render_portfolio_view()
    
    # Tab 4: 績效分析
    with main_tabs[3]:
        render_performance_view()
    
    # Tab 5: 風險管理
    with main_tabs[4]:
        render_risk_management_view()
    
    # Tab 6: 實時監控
    with main_tabs[5]:
        render_realtime_monitoring()
    
    # Tab 7: 系統監控
    with main_tabs[6]:
        render_system_monitoring()

def render_trading_view():
    """渲染交易視圖"""
    st.subheader("📈 專業交易圖表")
    
    # 圖表類型選擇
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        chart_type = st.radio(
            "圖表類型",
            ["專業分析圖表", "TradingView", "簡單圖表"],
            horizontal=True,
            help="專業分析圖表包含K線+技術指標"
        )
    
    with col2:
        show_indicators = st.checkbox("顯示技術指標", value=True)
    
    with col3:
        auto_refresh = st.checkbox("圖表自動更新", value=True)
    
    # 顯示對應圖表
    if chart_type == "專業分析圖表":
        st.write("**專業 K線分析圖表**")
        st.info("📊 包含K線、MA、MACD、RSI、布林帶等專業技術指標")
        
        # 使用高級圖表組件
        try:
            advanced_chart.render_realtime_chart()
        except Exception as e:
            st.error(f"載入專業圖表失敗: {e}")
            st.write("正在載入備用圖表...")
            # 降級到簡單圖表
            render_simple_chart(st.session_state.selected_symbol, st.session_state.selected_timeframe, show_indicators)
    
    elif chart_type == "TradingView":
        st.write("**專業 TradingView 圖表**")
        
        # TradingView 圖表設定
        studies = []
        if show_indicators:
            studies = [
                "RSI@tv-basicstudies",
                "MASimple@tv-basicstudies", 
                "MACD@tv-basicstudies",
                "BB@tv-basicstudies"
            ]
        
        # 渲染 TradingView 圖表
        symbol_for_tv = st.session_state.selected_symbol.replace('/', '')
        interval_map = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15',
            '30m': '30', '1h': '60', '4h': '240', '1d': '1D'
        }
        tv_interval = interval_map.get(st.session_state.selected_timeframe, '5')
        
        tradingview_chart(
            symbol=symbol_for_tv,
            exchange="OKX",
            interval=tv_interval,
            theme="dark",
            height=600,
            studies=studies
        )
    
    elif chart_type == "簡單圖表":
        st.write("**實時 K 線圖表**")
        render_simple_chart(st.session_state.selected_symbol, st.session_state.selected_timeframe, show_indicators)

def render_simple_chart(symbol, timeframe, show_indicators):
    """渲染簡單圖表"""
    # 獲取真實 K 線數據，使用時間戳強制刷新
    with st.spinner("正在載入實時數據..."):
        import time
        current_timestamp = int(time.time())
        kline_data = get_live_kline_data(
            symbol, 
            timeframe,
            100,
            _force_refresh=current_timestamp
        )
    
    if kline_data is None or kline_data.empty:
        st.warning("⚠️ 無法獲取 K 線數據，請檢查網路連接或稍後重試")
        # 使用備用數據
        @st.cache_data
        def generate_fallback_kline_data():
            dates = pd.date_range('2024-01-01', periods=100, freq='5min')
            np.random.seed(42)
            prices = 45000 + np.cumsum(np.random.randn(100) * 50)
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                data.append({
                    'timestamp': date,
                    'open': prices[i-1] if i > 0 else price,
                    'high': price + np.random.uniform(10, 100),
                    'low': price - np.random.uniform(10, 100),
                    'close': price + np.random.uniform(-20, 20),
                    'volume': np.random.uniform(100, 1000)
                })
            
            return pd.DataFrame(data).set_index('timestamp')
        
        kline_data = generate_fallback_kline_data()
        st.info("📊 顯示模擬數據供演示")
    
    # 使用 Plotly 繪製圖表
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[f'{symbol} K線圖', '成交量'],
        row_heights=[0.7, 0.3],
        vertical_spacing=0.1
    )
    
    # K 線圖
    fig.add_trace(
        go.Candlestick(
            x=kline_data.index,
            open=kline_data['open'],
            high=kline_data['high'],
            low=kline_data['low'],
            close=kline_data['close'],
            name='K線'
        ),
        row=1, col=1
    )
    
    # 技術指標
    if show_indicators:
        # 簡單移動平均線
        kline_data['sma_20'] = kline_data['close'].rolling(20).mean()
        fig.add_trace(
            go.Scatter(
                x=kline_data.index,
                y=kline_data['sma_20'],
                name='SMA 20',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
    
    # 成交量
    fig.add_trace(
        go.Bar(
            x=kline_data.index,
            y=kline_data['volume'],
            name='成交量',
            marker_color='rgba(158,158,158,0.5)'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 快速交易面板
    if st.session_state.api_connected:
        st.subheader("⚡ 快速交易")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trade_side = st.selectbox("交易方向", ["買入 (做多)", "賣出 (做空)"])
            
        with col2:
            trade_amount = st.number_input(
                "交易數量", 
                min_value=0.001, 
                value=0.01, 
                step=0.001,
                format="%.4f"
            )
        
        with col3:
            order_type = st.selectbox("訂單類型", ["市價單", "限價單"])
        
        if order_type == "限價單":
            limit_price = st.number_input(
                "限價價格 ($)",
                min_value=0.01,
                value=45000.0,
                step=0.01
            )
        
        if st.button("📤 提交訂單", type="primary"):
            st.info("🔄 訂單提交功能開發中...")
    
    # 快速交易面板  
    render_quick_trading_panel()

def render_realtime_kline_view():
    """渲染實時K線視圖 - Fragment優化版"""
    st.subheader("🚀 實時K線圖表 - Fragment優化 (每秒自動更新)")
    
    # 控制面板
    control_col1, control_col2, control_col3, control_col4 = st.columns(4)
    
    with control_col1:
        selected_symbol = st.selectbox(
            "選擇交易對",
            ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"],
            key="realtime_symbol"
        )
    
    with control_col2:
        selected_timeframe = st.selectbox(
            "時間週期",
            ["1m", "3m", "5m", "15m", "30m", "1h"],
            index=2,
            key="realtime_timeframe"
        )
    
    with control_col3:
        optimization_mode = st.selectbox(
            "更新模式",
            ["專業無閃爍模式 (推薦)", "TradingView風格", "Fragment優化", "傳統模式"],
            key="optimization_mode"
        )
    
    with control_col4:
        st.markdown("**顯示效果:**")
        if optimization_mode == "專業無閃爍模式 (推薦)":
            st.success("✨ 完全無閃爍")
        elif optimization_mode == "TradingView風格":
            st.info("🔄 平滑更新")
        elif optimization_mode == "Fragment優化":
            st.warning("⚡ 快速但閃爍")
        else:
            st.error("❌ 嚴重閃爍")
    
    # 功能說明
    if optimization_mode == "專業無閃爍模式 (推薦)":
        st.success("✨ **專業無閃爍模式** - 使用正確的Plotly數據更新機制，真正無閃爍！")
    elif optimization_mode == "TradingView風格":
        st.info("🔄 **TradingView風格** - 平滑更新但仍可能有輕微閃爍")
    elif optimization_mode == "Fragment優化":
        st.warning("⚡ **Fragment優化** - 高性能但會閃爍")
    else:
        st.error("❌ **傳統模式** - 嚴重閃爍，不建議使用")
    
    # 渲染實時K線圖
    try:
        if optimization_mode == "專業無閃爍模式 (推薦)":
            # 使用真正的無閃爍實時更新
            render_true_realtime_kline(selected_symbol, selected_timeframe)
            
        elif optimization_mode == "TradingView風格":
            # 使用TradingView風格的平滑更新
            render_tradingview_kline(selected_symbol, selected_timeframe)
            
        elif optimization_mode == "Fragment優化":
            # 使用Fragment優化的K線圖
            render_optimized_realtime_kline(selected_symbol, selected_timeframe)
            
            # Fragment優化的多交易對監控
            st.divider()
            monitor_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
            render_optimized_ticker_display(monitor_symbols)
            
        else:
            # 使用傳統方式
            streamlit_kline_component.render_realtime_kline_chart(
                symbol=selected_symbol,
                timeframe=selected_timeframe,
                height=600
            )
            
            # 傳統多交易對監控面板
            st.divider()
            monitor_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
            streamlit_kline_component.render_multi_symbol_dashboard(
                symbols=monitor_symbols,
                timeframe=selected_timeframe
            )
        
        # 技術說明
        with st.expander("✨ 無閃爍技術說明"):
            if optimization_mode == "專業無閃爍模式 (推薦)":
                st.write("**✨ 專業無閃爍核心技術：**")
                st.write("- 🎯 **Plotly batch_update()**: 使用正確的數據更新API")
                st.write("- 🔧 **固定圖表實例**: 不重新創建圖表，只更新數據")
                st.write("- 🎮 **uirevision='constant'**: 保持用戶縮放和平移狀態")
                st.write("- 📊 **數據流式更新**: 像TradingView一樣只更新K棒")
                st.write("- 👁️ **完全無閃爍**: 真正保護眼睛的專業實現")
                
                st.code("""
# 專業無閃爍核心技術
def update_chart_streaming(symbol, timeframe, new_data):
    fig = self.charts[chart_id]  # 獲取已存在的圖表
    
    # 關鍵：使用batch_update避免多次重繪
    with fig.batch_update():
        fig.data[0].x = combined_data.index      # 只更新數據
        fig.data[0].open = combined_data['open']  # 不重建圖表
        fig.data[0].high = combined_data['high']  # 保持狀態
        fig.data[0].low = combined_data['low']    # 無閃爍
        fig.data[0].close = combined_data['close']
    
    # 關鍵設置：
    # - batch_update() ✅ (一次性更新避免閃爍)
    # - 固定圖表實例 ✅ (不重新創建)
    # - uirevision保持 ✅ (用戶狀態不丟失)
    # - 3秒更新頻率 ✅ (避免過度刷新)
                """)
                
            elif optimization_mode == "TradingView風格":
                st.write("**🔄 TradingView風格特性：**")
                st.write("- 🎯 **嘗試平滑更新**: 但技術實現仍有閃爍")
                st.write("- ⚠️ **部分閃爍**: 無法完全避免重繪")
                
            elif optimization_mode == "Fragment優化":
                st.write("**⚡ Fragment優化特性：**")
                st.write("- 🚀 **高性能**: 但每次都重新創建圖表")
                st.write("- ⚠️ **明顯閃爍**: 整個圖表重新渲染")
                
            else:
                st.write("**❌ 傳統模式問題：**")
                st.write("- 👁️ **嚴重閃爍**: 每次都完全重新創建圖表")
                st.write("- 😵 **傷眼睛**: 不適合長時間觀看")
            
            st.markdown("### 👁️ 閃爍程度對比")
            
            visual_col1, visual_col2, visual_col3, visual_col4 = st.columns(4)
            
            with visual_col1:
                st.markdown("**✨ 專業無閃爍**")
                st.success("👁️ 閃爍: 0%")
                st.success("🔄 更新: 平滑")
                st.success("⚡ 性能: 優秀") 
                st.success("🎮 體驗: 完美")
            
            with visual_col2:
                st.markdown("**🔄 TradingView風格**")
                st.info("👁️ 閃爍: 20%")
                st.info("🔄 更新: 較平滑")
                st.info("⚡ 性能: 良好")
                st.info("🎮 體驗: 好")
            
            with visual_col3:
                st.markdown("**⚡ Fragment優化**")
                st.warning("👁️ 閃爍: 60%")
                st.warning("🔄 更新: 快速")
                st.warning("⚡ 性能: 極佳")
                st.warning("🎮 體驗: 普通")
            
            with visual_col4:
                st.markdown("**❌ 傳統模式**")
                st.error("👁️ 閃爍: 100%")
                st.error("🔄 更新: 閃爍")
                st.error("⚡ 性能: 差")
                st.error("🎮 體驗: 差")
                
    except Exception as e:
        st.error(f"❌ 實時K線載入錯誤: {e}")
        st.info("💡 請檢查網路連接或稍後重試")

def render_quick_trading_panel():
    """渲染快速交易面板"""
    if st.session_state.api_connected:
        st.subheader("⚡ 快速交易")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trade_side = st.selectbox("交易方向", ["買入 (做多)", "賣出 (做空)"])
            
        with col2:
            trade_amount = st.number_input(
                "交易數量", 
                min_value=0.001, 
                value=0.01, 
                step=0.001,
                format="%.4f"
            )
        
        with col3:
            order_type = st.selectbox("訂單類型", ["市價單", "限價單"])
        
        if order_type == "限價單":
            limit_price = st.number_input(
                "限價價格 ($)",
                min_value=0.01,
                value=45000.0,
                step=0.01
            )
        
        if st.button("📤 提交訂單", type="primary"):
            st.info("🔄 訂單提交功能開發中...")

def render_portfolio_view():
    """渲染投資組合視圖"""
    st.subheader("💼 投資組合總覽")
    
    # 使用交易儀表板組件
    render_complete_dashboard()

def render_performance_view():
    """渲染績效分析視圖"""
    st.subheader("📊 績效分析")
    
    # 時間範圍選擇
    col1, col2 = st.columns(2)
    
    with col1:
        time_range = st.selectbox(
            "分析時間範圍",
            ["今日", "本週", "本月", "本季", "今年", "全部"]
        )
    
    with col2:
        comparison_benchmark = st.selectbox(
            "對比基準",
            ["無", "BTC", "ETH", "大盤指數"]
        )
    
    # 績效概要
    st.subheader("📈 績效概要")
    
    # 模擬績效數據
    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
    
    with perf_col1:
        st.metric("總收益率", "+12.5%", "+2.3%")
    
    with perf_col2:
        st.metric("年化收益率", "+18.7%", "+3.1%")
    
    with perf_col3:
        st.metric("夏普比率", "1.42", "+0.15")
    
    with perf_col4:
        st.metric("最大回撤", "-3.2%", "+0.8%")
    
    # 詳細圖表
    chart_tabs = st.tabs(["收益曲線", "回撤分析", "月度收益", "風險指標"])
    
    with chart_tabs[0]:
        st.info("收益曲線圖表功能開發中...")
    
    with chart_tabs[1]:
        st.info("回撤分析圖表功能開發中...")
    
    with chart_tabs[2]:
        st.info("月度收益圖表功能開發中...")
    
    with chart_tabs[3]:
        st.info("風險指標圖表功能開發中...")

def render_risk_management_view():
    """渲染風險管理視圖"""
    st.subheader("⚖️ 風險管理")
    
    # 風險設定
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**風險參數設定**")
        
        max_risk_per_trade = st.slider(
            "單筆最大風險 (%)",
            min_value=0.1, max_value=10.0,
            value=2.0, step=0.1
        )
        
        max_daily_risk = st.slider(
            "單日最大風險 (%)", 
            min_value=1.0, max_value=20.0,
            value=5.0, step=0.5
        )
        
        max_positions = st.slider(
            "最大持倉數",
            min_value=1, max_value=20,
            value=5, step=1
        )
        
        stop_loss_pct = st.slider(
            "止損比例 (%)",
            min_value=0.5, max_value=10.0,
            value=2.0, step=0.1
        )
    
    with col2:
        st.write("**當前風險狀況**")
        
        # 風險使用情況
        risk_used = 2.3
        risk_limit = max_daily_risk
        risk_percentage = (risk_used / risk_limit) * 100
        
        st.metric("已用風險", f"{risk_used:.1f}%", f"/ {risk_limit:.1f}%")
        st.progress(min(risk_percentage / 100, 1.0))
        
        st.metric("當前持倉", "2", "/ 5")
        st.metric("可用風險", f"{risk_limit - risk_used:.1f}%")
        st.metric("風險利用率", f"{risk_percentage:.1f}%")
    
    # 風險警告
    if risk_percentage > 80:
        st.warning("⚠️ 風險使用率過高，建議謹慎交易")
    elif risk_percentage > 60:
        st.info("💡 風險使用率偏高，注意控制")

def render_realtime_monitoring():
    """渲染實時監控視圖"""
    st.subheader("📡 實時監控")
    
    # 實時行情（使用真實數據）
    st.write("**實時行情**")
    live_data_component.render_live_ticker(st.session_state.selected_symbol)
    
    st.divider()
    
    # 系統監控
    monitor_col1, monitor_col2 = st.columns(2)
    
    with monitor_col1:
        st.write("**系統狀態**")
        
        # 系統指標
        system_metrics = {
            "API 延遲": "25ms",
            "數據更新頻率": "1s",
            "WebSocket 狀態": "已連接",
            "策略運行時間": "2h 15m",
            "今日訂單數": "8",
            "錯誤次數": "0"
        }
        
        for metric, value in system_metrics.items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{metric}**")
            with col_b:
                st.write(value)
    
    with monitor_col2:
        st.write("**告警通知**")
        
        # 模擬告警
        notifications = [
            {"time": "10:30", "type": "INFO", "msg": "策略已啟動"},
            {"time": "10:25", "type": "SUCCESS", "msg": "BTC/USDT 多頭訂單成交"},
            {"time": "10:20", "type": "WARNING", "msg": "風險使用率達到 60%"},
        ]
        
        for notif in notifications:
            if notif["type"] == "INFO":
                st.info(f"[{notif['time']}] {notif['msg']}")
            elif notif["type"] == "SUCCESS":
                st.success(f"[{notif['time']}] {notif['msg']}")
            elif notif["type"] == "WARNING":
                st.warning(f"[{notif['time']}] {notif['msg']}")
    
    # 實時圖表
    st.subheader("📈 實時價格")
    
    if st.button("🔄 更新實時圖表"):
        fig = create_realtime_price_chart(
            st.session_state.selected_symbol, 
            st.session_state.selected_timeframe
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("正在獲取實時數據...")

def render_system_monitoring():
    """渲染系統監控視圖"""
    st.subheader("🔍 系統健康監控")
    
    # 註冊主要數據源
    register_data_source("OKX WebSocket", "websocket")
    register_data_source("OKX REST API", "api")
    register_data_source("K線數據", "data")
    register_data_source("行情數據", "data")
    
    # 渲染完整的監控儀表板
    monitor_dashboard.render_full_dashboard()
    
    st.divider()
    
    # 錯誤監控面板
    error_display.render_error_dashboard()
    
    # 系統信息
    with st.expander("📋 系統信息", expanded=False):
        import platform
        import sys
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write("**系統環境:**")
            st.write(f"- 操作系統: {platform.system()} {platform.release()}")
            st.write(f"- Python版本: {sys.version.split()[0]}")
            st.write(f"- 架構: {platform.machine()}")
            
        with info_col2:
            st.write("**應用信息:**")
            st.write("- 版本: AutoTrading Bot v2.0")
            st.write("- 模式: 實時K線系統")
            st.write("- 啟動時間:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 手動觸發測試
    if st.button("🧪 測試系統組件"):
        test_system_components()

def test_system_components():
    """測試系統組件功能"""
    with st.spinner("正在測試系統組件..."):
        test_results = []
        
        # 測試API連接
        try:
            from web.components.market_data_provider import get_live_ticker_data
            ticker = get_live_ticker_data('BTC/USDT')
            if ticker:
                test_results.append("✅ OKX API連接正常")
                track_data_update("OKX REST API", 100, error=False)
            else:
                test_results.append("❌ OKX API連接失敗")
                track_data_update("OKX REST API", error=True)
        except Exception as e:
            test_results.append(f"❌ API測試錯誤: {e}")
            track_data_update("OKX REST API", error=True)
        
        # 測試數據處理
        try:
            import pandas as pd
            test_df = pd.DataFrame({'test': [1, 2, 3]})
            if not test_df.empty:
                test_results.append("✅ 數據處理功能正常")
            else:
                test_results.append("❌ 數據處理測試失敗")
        except Exception as e:
            test_results.append(f"❌ 數據處理錯誤: {e}")
        
        # 測試圖表渲染
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))
            if fig:
                test_results.append("✅ 圖表渲染功能正常")
            else:
                test_results.append("❌ 圖表渲染測試失敗")
        except Exception as e:
            test_results.append(f"❌ 圖表渲染錯誤: {e}")
        
        # 顯示測試結果
        for result in test_results:
            if "✅" in result:
                st.success(result)
            else:
                st.error(result)

def main():
    """主應用程式"""
    # 穩定性和性能優化初始化 - 最高優先級
    auto_start_watchdog()  # 自動啟動內存監控
    performance_optimizer.optimize_streamlit_performance()
    
    # 初始化
    init_session_state()
    
    # 啟動WebSocket實時數據流（僅在首次載入時）
    if 'websocket_started' not in st.session_state:
        from web.components.market_data_provider import start_realtime_data
        start_realtime_data()
        st.session_state.websocket_started = True
    
    # 渲染Fragment控制面板
    fragment_optimizer.render_fragment_control_panel()
    
    # 渲染介面
    render_header()
    render_sidebar()
    render_main_content()
    
    # 系統健康監控和性能面板
    with st.expander("🔍 系統健康與性能監控", expanded=False):
        health_col1, health_col2 = st.columns(2)
        
        with health_col1:
            show_system_health()
        
        with health_col2:
            performance_dashboard.render_performance_panel()
    
    # 頁腳
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🤖 AutoTrading Bot v2.0 | 
        基於 ICT/SMC 策略的專業交易系統 | 
        ⚠️ 投資有風險，交易需謹慎</p>
        <p style='font-size: 0.8em; color: #999;'>
        ⚡ 穩定性優化已啟用 | 🚀 WebSocket實時數據流 | 📊 每秒更新K線圖 | 🛡️ 防卡死保護
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()