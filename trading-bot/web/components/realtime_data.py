"""
實時數據更新模組

提供 WebSocket 連接、數據快取和實時更新功能
"""

import streamlit as st
import asyncio
import json
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
import queue
from loguru import logger


class RealtimeDataManager:
    """實時數據管理器"""
    
    def __init__(self):
        self.data_queue = queue.Queue()
        self.subscribers = {}
        self.is_running = False
        self.update_thread = None
        self.websocket_thread = None
        
        # 數據快取
        self.ticker_cache = {}
        self.orderbook_cache = {}
        self.kline_cache = {}
        self.account_cache = {}
        
    def start(self):
        """啟動實時數據管理器"""
        if not self.is_running:
            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            logger.info("RealtimeDataManager started")
    
    def stop(self):
        """停止實時數據管理器"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1)
        logger.info("RealtimeDataManager stopped")
    
    def subscribe(self, data_type: str, callback: Callable):
        """訂閱數據更新"""
        if data_type not in self.subscribers:
            self.subscribers[data_type] = []
        self.subscribers[data_type].append(callback)
        logger.info(f"Subscribed to {data_type}")
    
    def unsubscribe(self, data_type: str, callback: Callable):
        """取消訂閱"""
        if data_type in self.subscribers:
            if callback in self.subscribers[data_type]:
                self.subscribers[data_type].remove(callback)
    
    def _update_loop(self):
        """數據更新循環"""
        while self.is_running:
            try:
                # 處理隊列中的數據
                while not self.data_queue.empty():
                    try:
                        data = self.data_queue.get_nowait()
                        self._process_data(data)
                    except queue.Empty:
                        break
                
                # 模擬數據更新（在實際應用中會從 WebSocket 獲取）
                self._simulate_data_update()
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
    
    def _process_data(self, data: Dict):
        """處理接收到的數據"""
        data_type = data.get('type')
        
        if data_type == 'ticker':
            self._process_ticker(data)
        elif data_type == 'orderbook':
            self._process_orderbook(data)
        elif data_type == 'kline':
            self._process_kline(data)
        elif data_type == 'account':
            self._process_account(data)
    
    def _process_ticker(self, data: Dict):
        """處理行情數據"""
        symbol = data.get('symbol')
        if symbol:
            self.ticker_cache[symbol] = {
                'last_price': data.get('last_price'),
                'bid': data.get('bid'),
                'ask': data.get('ask'),
                'volume': data.get('volume'),
                'change_24h': data.get('change_24h'),
                'change_pct_24h': data.get('change_pct_24h'),
                'timestamp': time.time()
            }
            self._notify_subscribers('ticker', symbol, self.ticker_cache[symbol])
    
    def _process_orderbook(self, data: Dict):
        """處理訂單簿數據"""
        symbol = data.get('symbol')
        if symbol:
            self.orderbook_cache[symbol] = {
                'bids': data.get('bids', []),
                'asks': data.get('asks', []),
                'timestamp': time.time()
            }
            self._notify_subscribers('orderbook', symbol, self.orderbook_cache[symbol])
    
    def _process_kline(self, data: Dict):
        """處理 K 線數據"""
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        key = f"{symbol}_{timeframe}"
        
        if symbol and timeframe:
            if key not in self.kline_cache:
                self.kline_cache[key] = []
            
            kline = {
                'timestamp': data.get('timestamp'),
                'open': data.get('open'),
                'high': data.get('high'),
                'low': data.get('low'),
                'close': data.get('close'),
                'volume': data.get('volume')
            }
            
            # 保持最近 1000 根 K 線
            self.kline_cache[key].append(kline)
            if len(self.kline_cache[key]) > 1000:
                self.kline_cache[key] = self.kline_cache[key][-1000:]
            
            self._notify_subscribers('kline', key, kline)
    
    def _process_account(self, data: Dict):
        """處理帳戶數據"""
        self.account_cache = {
            'balance': data.get('balance'),
            'equity': data.get('equity'),
            'margin': data.get('margin'),
            'positions': data.get('positions', []),
            'orders': data.get('orders', []),
            'timestamp': time.time()
        }
        self._notify_subscribers('account', None, self.account_cache)
    
    def _notify_subscribers(self, data_type: str, key: Optional[str], data: Dict):
        """通知訂閱者"""
        if data_type in self.subscribers:
            for callback in self.subscribers[data_type]:
                try:
                    callback(key, data)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
    
    def _simulate_data_update(self):
        """模擬數據更新（用於演示）"""
        import random
        
        # 模擬行情數據
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        for symbol in symbols:
            if symbol in self.ticker_cache:
                last_price = self.ticker_cache[symbol].get('last_price', 45000)
            else:
                last_price = 45000 if symbol == 'BTC/USDT' else 3000
            
            # 隨機價格變動
            change = random.uniform(-0.001, 0.001)  # ±0.1%
            new_price = last_price * (1 + change)
            
            ticker_data = {
                'type': 'ticker',
                'symbol': symbol,
                'last_price': new_price,
                'bid': new_price - random.uniform(0.1, 2.0),
                'ask': new_price + random.uniform(0.1, 2.0),
                'volume': random.uniform(1000, 5000),
                'change_24h': random.uniform(-500, 500),
                'change_pct_24h': random.uniform(-5, 5)
            }
            
            self.data_queue.put(ticker_data)
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """獲取行情數據"""
        return self.ticker_cache.get(symbol)
    
    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """獲取訂單簿數據"""
        return self.orderbook_cache.get(symbol)
    
    def get_klines(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """獲取 K 線數據"""
        key = f"{symbol}_{timeframe}"
        klines = self.kline_cache.get(key, [])
        return klines[-limit:] if klines else []
    
    def get_account(self) -> Optional[Dict]:
        """獲取帳戶數據"""
        return self.account_cache


# 全域實時數據管理器
realtime_manager = RealtimeDataManager()


class StreamlitRealtimeComponent:
    """Streamlit 實時組件基類"""
    
    def __init__(self, component_id: str):
        self.component_id = component_id
        self.last_update = 0
        self.update_interval = 1  # 秒
        
    def should_update(self) -> bool:
        """檢查是否需要更新"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            return True
        return False
    
    def render(self):
        """渲染組件（子類需實作）"""
        raise NotImplementedError


class RealtimeTickerComponent(StreamlitRealtimeComponent):
    """實時行情組件"""
    
    def __init__(self, symbol: str, component_id: str = None):
        super().__init__(component_id or f"ticker_{symbol}")
        self.symbol = symbol
        self.placeholder = None
        
    def render(self, placeholder=None):
        """渲染實時行情"""
        if placeholder is None:
            placeholder = st.empty()
        
        self.placeholder = placeholder
        
        # 獲取實時數據
        ticker = realtime_manager.get_ticker(self.symbol)
        
        if ticker:
            with placeholder.container():
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "最新價格",
                        f"${ticker['last_price']:,.2f}",
                        f"{ticker['change_pct_24h']:+.2f}%"
                    )
                
                with col2:
                    st.metric(
                        "24h 成交量",
                        f"{ticker['volume']:,.0f}",
                        help="24小時成交量"
                    )
                
                with col3:
                    st.metric(
                        "買價",
                        f"${ticker['bid']:,.2f}",
                        help="最佳買價"
                    )
                
                with col4:
                    st.metric(
                        "賣價", 
                        f"${ticker['ask']:,.2f}",
                        help="最佳賣價"
                    )
        else:
            with placeholder.container():
                st.info(f"等待 {self.symbol} 行情數據...")


class RealtimeOrderbookComponent(StreamlitRealtimeComponent):
    """實時訂單簿組件"""
    
    def __init__(self, symbol: str, depth: int = 10):
        super().__init__(f"orderbook_{symbol}")
        self.symbol = symbol
        self.depth = depth
        
    def render(self, placeholder=None):
        """渲染實時訂單簿"""
        if placeholder is None:
            placeholder = st.empty()
            
        orderbook = realtime_manager.get_orderbook(self.symbol)
        
        if orderbook:
            with placeholder.container():
                st.subheader(f"📋 {self.symbol} 訂單簿")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**賣盤 (Asks)**")
                    asks = orderbook['asks'][:self.depth]
                    asks_df = pd.DataFrame(asks, columns=['價格', '數量'])
                    asks_df = asks_df.sort_values('價格', ascending=False)
                    st.dataframe(
                        asks_df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            '價格': st.column_config.NumberColumn(format="$%.2f"),
                            '數量': st.column_config.NumberColumn(format="%.4f")
                        }
                    )
                
                with col2:
                    st.write("**買盤 (Bids)**")
                    bids = orderbook['bids'][:self.depth]
                    bids_df = pd.DataFrame(bids, columns=['價格', '數量'])
                    st.dataframe(
                        bids_df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            '價格': st.column_config.NumberColumn(format="$%.2f"),
                            '數量': st.column_config.NumberColumn(format="%.4f")
                        }
                    )
        else:
            with placeholder.container():
                st.info(f"等待 {self.symbol} 訂單簿數據...")


def init_realtime_data():
    """初始化實時數據系統"""
    if 'realtime_initialized' not in st.session_state:
        realtime_manager.start()
        st.session_state.realtime_initialized = True
        logger.info("Realtime data system initialized")


def auto_refresh_component(component, interval: int = 1):
    """自動刷新組件"""
    
    # 使用 JavaScript 實現自動刷新
    refresh_js = f"""
    <script>
    function autoRefresh() {{
        // 觸發 Streamlit 重新運行
        window.parent.document.dispatchEvent(new KeyboardEvent('keydown', {{
            'key': 'R',
            'ctrlKey': true
        }}));
    }}
    
    // 設定定時器
    setInterval(autoRefresh, {interval * 1000});
    </script>
    """
    
    st.components.v1.html(refresh_js, height=0)


def create_realtime_price_chart(symbol: str, timeframe: str = "1m"):
    """建立實時價格圖表"""
    import plotly.graph_objects as go
    
    # 獲取 K 線數據
    klines = realtime_manager.get_klines(symbol, timeframe, limit=50)
    
    if not klines:
        st.info(f"等待 {symbol} K 線數據...")
        return None
    
    # 轉換為 DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 建立圖表
    fig = go.Figure()
    
    # 添加 K 線
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    ))
    
    # 添加最新價格線
    latest_price = df['close'].iloc[-1]
    fig.add_hline(
        y=latest_price,
        line_dash="dash",
        line_color="yellow",
        annotation_text=f"最新: ${latest_price:,.2f}"
    )
    
    # 更新布局
    fig.update_layout(
        title=f"{symbol} 實時價格 ({timeframe})",
        xaxis_title="時間",
        yaxis_title="價格",
        height=400,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig


# WebSocket 連接管理
class WebSocketManager:
    """WebSocket 連接管理器"""
    
    def __init__(self):
        self.connections = {}
        self.is_running = False
        
    def connect(self, exchange: str, symbols: List[str]):
        """連接到交易所 WebSocket"""
        if exchange == "OKX":
            self._connect_okx(symbols)
        # 可以添加其他交易所
    
    def _connect_okx(self, symbols: List[str]):
        """連接 OKX WebSocket"""
        # 這裡會實作實際的 WebSocket 連接
        # 目前使用模擬數據
        logger.info(f"Connecting to OKX WebSocket for symbols: {symbols}")
    
    def disconnect(self, exchange: str):
        """斷開連接"""
        if exchange in self.connections:
            # 關閉連接
            logger.info(f"Disconnecting from {exchange}")


# 全域 WebSocket 管理器
websocket_manager = WebSocketManager()


def render_realtime_demo():
    """實時數據演示"""
    st.title("📡 實時數據演示")
    
    # 初始化實時數據系統
    init_realtime_data()
    
    # 選擇交易對
    symbol = st.selectbox("選擇交易對", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    
    # 實時行情
    st.subheader("💰 實時行情")
    ticker_placeholder = st.empty()
    ticker_component = RealtimeTickerComponent(symbol)
    ticker_component.render(ticker_placeholder)
    
    # 實時價格圖表
    st.subheader("📈 實時價格圖表")
    chart_placeholder = st.empty()
    
    if st.button("刷新圖表"):
        fig = create_realtime_price_chart(symbol)
        if fig:
            chart_placeholder.plotly_chart(fig, use_container_width=True)
    
    # 控制面板
    st.subheader("🎛️ 控制面板")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("啟動實時更新"):
            realtime_manager.start()
            st.success("實時更新已啟動")
    
    with col2:
        if st.button("停止實時更新"):
            realtime_manager.stop()
            st.info("實時更新已停止")
    
    with col3:
        if st.button("清除快取"):
            realtime_manager.ticker_cache.clear()
            realtime_manager.orderbook_cache.clear() 
            realtime_manager.kline_cache.clear()
            st.info("快取已清除")


if __name__ == "__main__":
    render_realtime_demo()