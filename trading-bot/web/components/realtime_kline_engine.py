"""
实时K线引擎 - 每秒更新的K线数据处理
基于WebSocket实现真正的实时K线更新
"""

import asyncio
import json
# 兼容性導入 - 支援不同的WebSocket庫
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    print("⚠️ websockets 包未安裝，將使用 websocket-client 作為備用")
    WEBSOCKETS_AVAILABLE = False
    import websocket
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import time
import threading
from collections import defaultdict
import streamlit as st
from loguru import logger


class RealtimeKlineEngine:
    """实时K线引擎 - 每秒更新"""
    
    def __init__(self):
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.connections = {}
        self.kline_data = defaultdict(lambda: defaultdict(pd.DataFrame))
        self.current_candles = defaultdict(dict)  # 当前正在形成的K线
        self.callbacks = defaultdict(list)
        self.running = False
        self.update_threads = {}
        
        # 支持的时间周期
        self.timeframes = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900,
            '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400
        }
        
    async def subscribe_kline(self, symbol: str, timeframe: str, callback: Callable = None):
        """订阅实时K线数据"""
        try:
            okx_symbol = symbol.replace('/', '-')
            channel = f"candle{timeframe}"
            
            # WebSocket订阅消息
            subscribe_msg = {
                "op": "subscribe",
                "args": [{
                    "channel": channel,
                    "instId": okx_symbol
                }]
            }
            
            # 建立WebSocket连接
            if okx_symbol not in self.connections:
                if WEBSOCKETS_AVAILABLE:
                    # 使用 websockets 庫
                    ws = await websockets.connect(self.ws_url)
                    self.connections[okx_symbol] = ws
                    
                    # 发送订阅消息
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"Subscribed to {symbol} {timeframe} klines (websockets)")
                    
                    # 启动消息监听
                    asyncio.create_task(self._listen_kline_updates(ws, symbol, timeframe))
                else:
                    # 備用：使用 websocket-client
                    logger.info(f"Using websocket-client for {symbol} {timeframe}")
                    self._setup_fallback_websocket(okx_symbol, subscribe_msg, symbol, timeframe)
            
            # 注册回调函数
            if callback:
                self.callbacks[f"{symbol}_{timeframe}"].append(callback)
                
        except Exception as e:
            logger.error(f"Failed to subscribe kline {symbol} {timeframe}: {e}")
            # 嘗試降級到REST API輪詢
            self._setup_fallback_polling(symbol, timeframe)
    
    async def _listen_kline_updates(self, ws, symbol: str, timeframe: str):
        """监听K线更新"""
        try:
            async for message in ws:
                data = json.loads(message)
                
                if 'data' in data and data.get('arg', {}).get('channel', '').startswith('candle'):
                    await self._process_kline_data(data, symbol, timeframe)
                    
        except Exception as e:
            logger.error(f"Error listening kline updates {symbol}: {e}")
    
    async def _process_kline_data(self, data: dict, symbol: str, timeframe: str):
        """处理K线数据更新"""
        try:
            for kline_info in data.get('data', []):
                # OKX K线数据格式: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
                timestamp = pd.to_datetime(int(kline_info[0]), unit='ms')
                
                kline_row = {
                    'timestamp': timestamp,
                    'open': float(kline_info[1]),
                    'high': float(kline_info[2]),
                    'low': float(kline_info[3]),
                    'close': float(kline_info[4]),
                    'volume': float(kline_info[5]),
                    'is_confirmed': kline_info[8] == '1'  # 是否确认的K线
                }
                
                # 更新K线数据
                await self._update_kline_dataframe(symbol, timeframe, kline_row)
                
                # 调用回调函数
                for callback in self.callbacks.get(f"{symbol}_{timeframe}", []):
                    try:
                        callback(symbol, timeframe, kline_row)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing kline data: {e}")
    
    async def _update_kline_dataframe(self, symbol: str, timeframe: str, kline_row: dict):
        """更新K线DataFrame"""
        try:
            df_key = f"{symbol}_{timeframe}"
            
            # 获取或创建DataFrame
            if df_key not in self.kline_data or self.kline_data[df_key].empty:
                # 初始化空DataFrame
                self.kline_data[df_key] = pd.DataFrame(columns=[
                    'open', 'high', 'low', 'close', 'volume', 'is_confirmed'
                ])
                self.kline_data[df_key].index.name = 'timestamp'
            
            df = self.kline_data[df_key]
            timestamp = kline_row['timestamp']
            
            # 检查是否是新K线或更新现有K线
            if timestamp in df.index:
                # 更新现有K线
                df.loc[timestamp] = [
                    kline_row['open'], kline_row['high'], kline_row['low'],
                    kline_row['close'], kline_row['volume'], kline_row['is_confirmed']
                ]
            else:
                # 添加新K线
                new_row = pd.DataFrame([{
                    'open': kline_row['open'],
                    'high': kline_row['high'],
                    'low': kline_row['low'],
                    'close': kline_row['close'],
                    'volume': kline_row['volume'],
                    'is_confirmed': kline_row['is_confirmed']
                }], index=[timestamp])
                
                # 合并到主DataFrame
                df = pd.concat([df, new_row])
                df = df.sort_index()
                
                # 保持最新1000条数据
                if len(df) > 1000:
                    df = df.tail(1000)
                
                self.kline_data[df_key] = df
                
        except Exception as e:
            logger.error(f"Error updating kline dataframe: {e}")
    
    def get_latest_klines(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """获取最新K线数据"""
        try:
            df_key = f"{symbol}_{timeframe}"
            
            if df_key in self.kline_data and not self.kline_data[df_key].empty:
                df = self.kline_data[df_key].copy()
                return df.tail(limit) if len(df) > limit else df
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest klines: {e}")
            return None
    
    def _setup_fallback_websocket(self, okx_symbol: str, subscribe_msg: dict, symbol: str, timeframe: str):
        """設置備用WebSocket連接"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                asyncio.create_task(self._process_kline_data(data, symbol, timeframe))
            except Exception as e:
                logger.error(f"Fallback websocket message error: {e}")
        
        def on_error(ws, error):
            logger.error(f"Fallback websocket error: {error}")
        
        def on_open(ws):
            ws.send(json.dumps(subscribe_msg))
            logger.info(f"Fallback websocket opened for {symbol}")
        
        # 在背景線程中運行
        def run_websocket():
            ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_open=on_open
            )
            ws.run_forever()
        
        import threading
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
    
    def _setup_fallback_polling(self, symbol: str, timeframe: str):
        """設置備用REST API輪詢"""
        def polling_task():
            import time
            from .market_data_provider import get_live_kline_data
            
            while self.running:
                try:
                    # 每5秒輪詢一次
                    kline_data = get_live_kline_data(symbol, timeframe, 1)
                    if kline_data is not None and not kline_data.empty:
                        latest = kline_data.iloc[-1]
                        kline_row = {
                            'timestamp': kline_data.index[-1],
                            'open': latest['open'],
                            'high': latest['high'],
                            'low': latest['low'],
                            'close': latest['close'],
                            'volume': latest['volume'],
                            'is_confirmed': True
                        }
                        
                        # 模擬WebSocket回調
                        asyncio.create_task(self._update_kline_dataframe(symbol, timeframe, kline_row))
                        
                        # 觸發回調
                        for callback in self.callbacks.get(f"{symbol}_{timeframe}", []):
                            try:
                                callback(symbol, timeframe, kline_row)
                            except Exception as e:
                                logger.error(f"Polling callback error: {e}")
                    
                    time.sleep(5)  # 每5秒更新
                    
                except Exception as e:
                    logger.error(f"Polling task error: {e}")
                    time.sleep(10)  # 錯誤時等待更久
        
        import threading
        thread = threading.Thread(target=polling_task, daemon=True)
        thread.start()
        logger.info(f"Started fallback polling for {symbol} {timeframe}")
    
    def start_realtime_updates(self, symbols: List[str], timeframes: List[str]):
        """启动实时更新"""
        if self.running:
            return
            
        self.running = True
        
        async def run_updates():
            tasks = []
            for symbol in symbols:
                for timeframe in timeframes:
                    task = self.subscribe_kline(symbol, timeframe)
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # 在新线程中运行异步任务
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_updates())
            except Exception as e:
                logger.error(f"Error in realtime updates: {e}")
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        logger.info(f"Started realtime kline updates for {symbols} with timeframes {timeframes}")
    
    def stop_realtime_updates(self):
        """停止实时更新"""
        self.running = False
        
        # 关闭所有WebSocket连接
        async def close_connections():
            for ws in self.connections.values():
                try:
                    await ws.close()
                except Exception as e:
                    logger.error(f"Error closing websocket: {e}")
        
        if self.connections:
            asyncio.create_task(close_connections())
        
        self.connections.clear()
        logger.info("Stopped realtime kline updates")


class StreamlitRealtimeKlineComponent:
    """Streamlit实时K线组件"""
    
    def __init__(self):
        self.engine = RealtimeKlineEngine()
        self.chart_containers = {}
        self.last_update = {}
        
    def initialize_realtime_klines(self, symbols: List[str], timeframes: List[str]):
        """初始化实时K线系统"""
        if 'kline_engine_started' not in st.session_state:
            self.engine.start_realtime_updates(symbols, timeframes)
            st.session_state.kline_engine_started = True
            st.session_state.kline_engine = self.engine
    
    def render_realtime_kline_chart(self, symbol: str, timeframe: str = "5m", height: int = 600):
        """渲染实时K线图表"""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 确保引擎已启动
        if 'kline_engine' in st.session_state:
            engine = st.session_state.kline_engine
        else:
            engine = self.engine
            self.initialize_realtime_klines([symbol], [timeframe])
        
        # 创建图表容器
        chart_key = f"kline_chart_{symbol}_{timeframe}"
        if chart_key not in self.chart_containers:
            self.chart_containers[chart_key] = st.empty()
        
        # 获取最新数据
        kline_data = engine.get_latest_klines(symbol, timeframe, 200)
        
        if kline_data is not None and not kline_data.empty:
            # 创建K线图
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=[f'{symbol} {timeframe} K线图 (实时)', '成交量'],
                row_heights=[0.7, 0.3],
                vertical_spacing=0.1
            )
            
            # K线图
            fig.add_trace(
                go.Candlestick(
                    x=kline_data.index,
                    open=kline_data['open'],
                    high=kline_data['high'],
                    low=kline_data['low'],
                    close=kline_data['close'],
                    name='K线',
                    increasing_line_color='#26a69a',
                    decreasing_line_color='#ef5350'
                ),
                row=1, col=1
            )
            
            # 成交量
            colors = ['red' if kline_data['close'].iloc[i] < kline_data['open'].iloc[i] else 'green' 
                     for i in range(len(kline_data))]
            
            fig.add_trace(
                go.Bar(
                    x=kline_data.index,
                    y=kline_data['volume'],
                    name='成交量',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            # 更新布局
            fig.update_layout(
                title=f'{symbol} 实时K线图 - {timeframe} | 更新时间: {datetime.now().strftime("%H:%M:%S")}',
                height=height,
                showlegend=True,
                xaxis_rangeslider_visible=False,
                template='plotly_dark'
            )
            
            # 显示图表
            with self.chart_containers[chart_key]:
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_key}_{int(time.time())}")
                
                # 显示最新数据指标
                if len(kline_data) > 0:
                    latest = kline_data.iloc[-1]
                    prev = kline_data.iloc[-2] if len(kline_data) > 1 else latest
                    
                    change = latest['close'] - prev['close']
                    change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("最新价格", f"${latest['close']:.4f}", f"{change:+.4f} ({change_pct:+.2f}%)")
                    
                    with col2:
                        st.metric("24h最高", f"${latest['high']:.4f}")
                    
                    with col3:
                        st.metric("24h最低", f"${latest['low']:.4f}")
                    
                    with col4:
                        volume_k = latest['volume'] / 1000
                        st.metric("成交量", f"{volume_k:.1f}K")
                        
        else:
            with self.chart_containers[chart_key]:
                st.info(f"正在获取 {symbol} {timeframe} 的实时K线数据...")
    
    def render_multi_symbol_dashboard(self, symbols: List[str], timeframe: str = "5m"):
        """多交易对仪表盘"""
        st.subheader(f"🔥 多交易对实时监控 - {timeframe}")
        
        # 初始化所有交易对的实时数据
        self.initialize_realtime_klines(symbols, [timeframe])
        
        # 获取引擎实例
        engine = st.session_state.get('kline_engine', self.engine)
        
        cols = st.columns(min(len(symbols), 4))
        
        for i, symbol in enumerate(symbols):
            with cols[i % len(cols)]:
                kline_data = engine.get_latest_klines(symbol, timeframe, 50)
                
                if kline_data is not None and not kline_data.empty:
                    latest = kline_data.iloc[-1]
                    prev = kline_data.iloc[-2] if len(kline_data) > 1 else latest
                    
                    change = latest['close'] - prev['close']
                    change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
                    
                    color = "🟢" if change >= 0 else "🔴"
                    
                    with st.container():
                        st.markdown(f"### {color} {symbol}")
                        st.metric(
                            "价格",
                            f"${latest['close']:.4f}",
                            f"{change:+.4f} ({change_pct:+.2f}%)"
                        )
                        
                        # 迷你图表
                        if len(kline_data) >= 20:
                            mini_chart_data = kline_data.tail(20)
                            st.line_chart(mini_chart_data['close'], height=100)
                else:
                    st.info(f"载入中...")


# 全局实例
realtime_kline_engine = RealtimeKlineEngine()
streamlit_kline_component = StreamlitRealtimeKlineComponent()


# 测试函数
async def test_realtime_klines():
    """测试实时K线功能"""
    engine = RealtimeKlineEngine()
    
    def on_kline_update(symbol, timeframe, kline_data):
        print(f"[{datetime.now()}] {symbol} {timeframe} - Price: {kline_data['close']}")
    
    # 启动实时订阅
    await engine.subscribe_kline('BTC/USDT', '5m', on_kline_update)
    
    # 运行30秒
    await asyncio.sleep(30)
    
    # 获取数据
    data = engine.get_latest_klines('BTC/USDT', '5m', 10)
    print(f"Retrieved {len(data)} klines")
    print(data)


if __name__ == "__main__":
    # 测试实时K线引擎
    asyncio.run(test_realtime_klines())