"""
增強數據提供者

整合多個專業數據源，包括技術指標計算
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
import yfinance as yf
import talib
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime, timedelta
import json
from loguru import logger
import streamlit as st


class EnhancedDataProvider:
    """增強數據提供者 - 整合多個數據源"""
    
    def __init__(self):
        self.data_sources = {
            'okx': 'https://www.okx.com/api/v5',
            'binance': 'https://api.binance.com/api/v3',
            'coingecko': 'https://api.coingecko.com/api/v3',
            'twelvedata': 'https://api.twelvedata.com',  # 免費技術指標API
            'finhub': 'https://finnhub.io/api/v1'  # 免費金融數據API
        }
        self.session = None
        
    async def get_session(self):
        """獲取 aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def fetch_enhanced_ticker(self, symbol: str = "BTC-USDT") -> Optional[Dict]:
        """獲取增強行情數據（包含技術指標）"""
        try:
            # 基礎行情數據
            basic_ticker = await self._fetch_okx_ticker(symbol)
            if not basic_ticker:
                return None
            
            # 獲取K線數據計算技術指標
            klines = await self._fetch_okx_klines(symbol, "1h", 100)
            if klines is not None:
                # 計算技術指標
                indicators = self._calculate_indicators(klines)
                basic_ticker.update(indicators)
            
            return basic_ticker
            
        except Exception as e:
            logger.error(f"Error fetching enhanced ticker: {e}")
            return None
    
    async def _fetch_okx_ticker(self, symbol: str) -> Optional[Dict]:
        """從 OKX 獲取基礎行情"""
        try:
            session = await self.get_session()
            url = f"{self.data_sources['okx']}/market/ticker"
            params = {"instId": symbol}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        ticker_data = data['data'][0]
                        return {
                            'symbol': symbol,
                            'last_price': float(ticker_data.get('last', 0)),
                            'bid': float(ticker_data.get('bidPx', 0)),
                            'ask': float(ticker_data.get('askPx', 0)),
                            'high_24h': float(ticker_data.get('high24h', 0)),
                            'low_24h': float(ticker_data.get('low24h', 0)),
                            'volume_24h': float(ticker_data.get('vol24h', 0)),
                            'change_24h': float(ticker_data.get('chg24h', 0)) * 100,
                            'timestamp': int(ticker_data.get('ts', time.time() * 1000))
                        }
        except Exception as e:
            logger.error(f"Error fetching OKX ticker: {e}")
            return None
    
    async def _fetch_okx_klines(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """從 OKX 獲取 K 線數據"""
        try:
            session = await self.get_session()
            url = f"{self.data_sources['okx']}/market/candles"
            
            tf_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1H', '4h': '4H', '1d': '1D'
            }
            
            params = {
                "instId": symbol,
                "bar": tf_map.get(timeframe, '1H'),
                "limit": str(limit)
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        klines = data['data']
                        
                        df_data = []
                        for kline in klines:
                            df_data.append({
                                'timestamp': pd.to_datetime(int(kline[0]), unit='ms'),
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5])
                            })
                        
                        df = pd.DataFrame(df_data)
                        df.set_index('timestamp', inplace=True)
                        return df.sort_index()
                        
        except Exception as e:
            logger.error(f"Error fetching OKX klines: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """計算技術指標"""
        try:
            if len(df) < 50:  # 需要足夠數據
                return {}
            
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values
            
            indicators = {}
            
            # RSI
            try:
                rsi = talib.RSI(close, timeperiod=14)
                indicators['rsi'] = float(rsi[-1]) if not np.isnan(rsi[-1]) else None
                indicators['rsi_signal'] = self._get_rsi_signal(rsi[-1])
            except:
                indicators['rsi'] = self._simple_rsi(close, 14)
                indicators['rsi_signal'] = self._get_rsi_signal(indicators['rsi'])
            
            # MACD
            try:
                macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                indicators['macd'] = float(macd[-1]) if not np.isnan(macd[-1]) else None
                indicators['macd_signal'] = float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else None
                indicators['macd_histogram'] = float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else None
                indicators['macd_trend'] = self._get_macd_trend(macd[-1], macd_signal[-1])
            except:
                macd_data = self._simple_macd(close)
                indicators.update(macd_data)
            
            # 移動平均線
            try:
                sma_20 = talib.SMA(close, timeperiod=20)
                sma_50 = talib.SMA(close, timeperiod=50)
                indicators['sma_20'] = float(sma_20[-1]) if not np.isnan(sma_20[-1]) else None
                indicators['sma_50'] = float(sma_50[-1]) if not np.isnan(sma_50[-1]) else None
                indicators['price_vs_sma20'] = ((close[-1] - sma_20[-1]) / sma_20[-1] * 100) if not np.isnan(sma_20[-1]) else None
            except:
                indicators['sma_20'] = np.mean(close[-20:]) if len(close) >= 20 else None
                indicators['sma_50'] = np.mean(close[-50:]) if len(close) >= 50 else None
            
            # 布林帶
            try:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
                indicators['bb_upper'] = float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else None
                indicators['bb_lower'] = float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else None
                indicators['bb_position'] = self._get_bb_position(close[-1], bb_upper[-1], bb_lower[-1])
            except:
                bb_data = self._simple_bollinger_bands(close, 20, 2)
                indicators.update(bb_data)
            
            # 成交量指標
            if len(volume) >= 20:
                indicators['volume_sma'] = float(np.mean(volume[-20:]))
                indicators['volume_ratio'] = float(volume[-1] / indicators['volume_sma'])
            
            # 波動率
            if len(close) >= 20:
                returns = np.diff(close) / close[:-1]
                indicators['volatility'] = float(np.std(returns[-20:]) * np.sqrt(24) * 100)  # 日化波動率
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def _simple_rsi(self, prices: np.array, period: int = 14) -> Optional[float]:
        """簡單 RSI 計算"""
        try:
            if len(prices) < period + 1:
                return None
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi)
        except:
            return None
    
    def _simple_macd(self, prices: np.array) -> Dict:
        """簡單 MACD 計算"""
        try:
            if len(prices) < 26:
                return {}
            
            ema_12 = self._ema(prices, 12)
            ema_26 = self._ema(prices, 26)
            
            if ema_12 is None or ema_26 is None:
                return {}
            
            macd = ema_12 - ema_26
            signal = self._ema(np.array([macd] * 9), 9)  # 簡化信號線
            
            return {
                'macd': float(macd),
                'macd_signal': float(signal) if signal else None,
                'macd_histogram': float(macd - (signal or 0)),
                'macd_trend': 'bullish' if macd > (signal or 0) else 'bearish'
            }
        except:
            return {}
    
    def _ema(self, prices: np.array, period: int) -> Optional[float]:
        """計算指數移動平均"""
        try:
            if len(prices) < period:
                return None
            
            alpha = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = alpha * price + (1 - alpha) * ema
            
            return float(ema)
        except:
            return None
    
    def _simple_bollinger_bands(self, prices: np.array, period: int, std_dev: float) -> Dict:
        """簡單布林帶計算"""
        try:
            if len(prices) < period:
                return {}
            
            sma = np.mean(prices[-period:])
            std = np.std(prices[-period:])
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return {
                'bb_upper': float(upper),
                'bb_lower': float(lower),
                'bb_position': self._get_bb_position(prices[-1], upper, lower)
            }
        except:
            return {}
    
    def _get_rsi_signal(self, rsi: Optional[float]) -> str:
        """RSI 信號判斷"""
        if rsi is None:
            return "neutral"
        
        if rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        else:
            return "neutral"
    
    def _get_macd_trend(self, macd: Optional[float], signal: Optional[float]) -> str:
        """MACD 趨勢判斷"""
        if macd is None or signal is None:
            return "neutral"
        
        return "bullish" if macd > signal else "bearish"
    
    def _get_bb_position(self, price: float, upper: Optional[float], lower: Optional[float]) -> str:
        """布林帶位置判斷"""
        if upper is None or lower is None:
            return "neutral"
        
        if price > upper:
            return "above"
        elif price < lower:
            return "below"
        else:
            return "middle"
    
    async def close_session(self):
        """關閉 session"""
        if self.session:
            await self.session.close()
            self.session = None


class TechnicalAnalysisComponent:
    """技術分析組件"""
    
    @staticmethod
    def render_enhanced_ticker(symbol: str, placeholder=None):
        """渲染增強行情顯示"""
        if placeholder is None:
            placeholder = st.empty()
        
        with placeholder.container():
            # 獲取增強數據
            enhanced_data = get_enhanced_ticker_data(symbol)
            
            if enhanced_data:
                # 基本價格信息
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    price = enhanced_data['last_price']
                    change = enhanced_data['change_24h']
                    delta_color = "normal" if change >= 0 else "inverse"
                    st.metric(
                        "當前價格",
                        f"${price:,.2f}",
                        f"{change:+.2f}%",
                        delta_color=delta_color
                    )
                
                with col2:
                    rsi = enhanced_data.get('rsi')
                    rsi_signal = enhanced_data.get('rsi_signal', 'neutral')
                    rsi_color = "🟢" if rsi_signal == "oversold" else "🔴" if rsi_signal == "overbought" else "🟡"
                    st.metric(
                        f"RSI {rsi_color}",
                        f"{rsi:.1f}" if rsi else "N/A",
                        rsi_signal.title()
                    )
                
                with col3:
                    macd_trend = enhanced_data.get('macd_trend', 'neutral')
                    macd_color = "🟢" if macd_trend == "bullish" else "🔴" if macd_trend == "bearish" else "🟡"
                    st.metric(
                        f"MACD {macd_color}",
                        macd_trend.title(),
                        help="MACD 趨勢指標"
                    )
                
                with col4:
                    bb_position = enhanced_data.get('bb_position', 'neutral')
                    bb_color = "🟢" if bb_position == "below" else "🔴" if bb_position == "above" else "🟡"
                    st.metric(
                        f"布林帶 {bb_color}",
                        bb_position.title(),
                        help="價格在布林帶中的位置"
                    )
                
                # 詳細技術指標
                with st.expander("📊 詳細技術指標"):
                    ind_col1, ind_col2 = st.columns(2)
                    
                    with ind_col1:
                        st.write("**趨勢指標**")
                        if enhanced_data.get('sma_20'):
                            st.write(f"SMA 20: ${enhanced_data['sma_20']:,.2f}")
                        if enhanced_data.get('sma_50'):
                            st.write(f"SMA 50: ${enhanced_data['sma_50']:,.2f}")
                        if enhanced_data.get('price_vs_sma20'):
                            st.write(f"vs SMA20: {enhanced_data['price_vs_sma20']:+.2f}%")
                    
                    with ind_col2:
                        st.write("**波動指標**")
                        if enhanced_data.get('volatility'):
                            st.write(f"日化波動率: {enhanced_data['volatility']:.2f}%")
                        if enhanced_data.get('volume_ratio'):
                            st.write(f"成交量比: {enhanced_data['volume_ratio']:.2f}x")
                
            else:
                st.warning("⚠️ 無法獲取增強數據")


# Streamlit 快取版本
@st.cache_data(ttl=30)  # 30秒快取
def get_enhanced_ticker_data(symbol: str) -> Optional[Dict]:
    """獲取增強行情數據（有快取）"""
    async def fetch_data():
        provider = EnhancedDataProvider()
        try:
            okx_symbol = symbol.replace('/', '-')
            data = await provider.fetch_enhanced_ticker(okx_symbol)
            return data
        finally:
            await provider.close_session()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fetch_data())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in get_enhanced_ticker_data: {e}")
        return None


# 全域實例
enhanced_provider = EnhancedDataProvider()
technical_analysis_component = TechnicalAnalysisComponent()


# 測試函數
async def test_enhanced_data():
    """測試增強數據功能"""
    provider = EnhancedDataProvider()
    
    try:
        print("Testing enhanced ticker...")
        ticker = await provider.fetch_enhanced_ticker("BTC-USDT")
        
        if ticker:
            print(f"Price: ${ticker['last_price']:,.2f}")
            print(f"RSI: {ticker.get('rsi', 'N/A')}")
            print(f"MACD Trend: {ticker.get('macd_trend', 'N/A')}")
            print(f"BB Position: {ticker.get('bb_position', 'N/A')}")
        else:
            print("Failed to fetch data")
            
    finally:
        await provider.close_session()


if __name__ == "__main__":
    # 測試增強數據功能
    asyncio.run(test_enhanced_data())