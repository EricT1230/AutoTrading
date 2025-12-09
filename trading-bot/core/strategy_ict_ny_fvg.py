"""
ICT NY FVG 策略實作

基於 Smart Money Concepts (SMC) / Inner Circle Trader (ICT) 理論的交易策略
核心邏輯：NY Session + Liquidity Sweep + Fair Value Gap + 1:3 風險收益比
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import pytz
from datetime import datetime, time

from .strategy_base import StrategyBase, TradingSignal, SignalType, BarData


class ICTNYFVGStrategy(StrategyBase):
    """
    ICT NY FVG 策略
    
    交易邏輯：
    1. 限制在 NY Session 時間內 (09:30-11:30 EST)
    2. 偵測 Liquidity Sweep（掃高/掃低）
    3. 等待 Bullish/Bearish Engulfing
    4. 識別 Fair Value Gap (FVG)
    5. 在 FVG 中點進場，SL 設在 FVG 邊緣，TP 為 1:3
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # 策略參數
        params = self.parameters
        self.session_start = params.get("session_start", "09:30")
        self.session_end = params.get("session_end", "11:30")
        self.timezone = params.get("timezone", "America/New_York")
        
        self.min_fvg_size_pips = params.get("min_fvg_size_pips", 10)
        self.max_fvg_size_pips = params.get("max_fvg_size_pips", 100)
        self.fvg_timeout_bars = params.get("fvg_timeout_bars", 10)
        
        self.lookback_bars = params.get("lookback_bars", 5)
        self.sweep_confirmation_bars = params.get("sweep_confirmation_bars", 1)
        
        self.risk_reward_ratio = params.get("risk_reward_ratio", 3.0)
        self.stop_loss_buffer_pips = params.get("stop_loss_buffer_pips", 2)
        self.take_profit_buffer_pips = params.get("take_profit_buffer_pips", 1)
        
        # 內部狀態
        self.last_signals = []  # 記錄最近的信號
        
    def on_bar(self, bar: BarData, history: pd.DataFrame) -> Optional[TradingSignal]:
        """
        處理新的K線數據並產生交易信號
        """
        
        # 檢查是否在 NY Session 內
        if not self._is_ny_session(bar.timestamp):
            return None
            
        # 確保有足夠的歷史數據
        if len(history) < max(20, self.lookback_bars + 5):
            return None
            
        # 偵測流動性掃蕩 (Liquidity Sweep)
        sweep_direction = self._detect_liquidity_sweep(history)
        if sweep_direction is None:
            return None
            
        # 檢查是否有 Engulfing Pattern
        engulfing_direction = self._detect_engulfing_pattern(history)
        if engulfing_direction != sweep_direction:
            return None
            
        # 識別 Fair Value Gap
        fvg_data = self._detect_fair_value_gap(history, sweep_direction)
        if fvg_data is None:
            return None
            
        # 生成交易信號
        signal = self._generate_signal(bar, fvg_data, sweep_direction)
        
        return signal
    
    def _is_ny_session(self, timestamp: pd.Timestamp) -> bool:
        """檢查是否在 NY Session 時間內"""
        
        try:
            # 轉換到 NY 時區
            ny_tz = pytz.timezone(self.timezone)
            ny_time = timestamp.tz_convert(ny_tz)
            
            # 解析開始和結束時間
            start_time = time(*[int(x) for x in self.session_start.split(":")])
            end_time = time(*[int(x) for x in self.session_end.split(":")])
            
            current_time = ny_time.time()
            
            return start_time <= current_time <= end_time
            
        except Exception:
            # 如果時區轉換失敗，假設在交易時間內
            return True
    
    def _detect_liquidity_sweep(self, history: pd.DataFrame) -> Optional[str]:
        """
        偵測流動性掃蕩
        
        Returns:
            "BULLISH" (掃低後看多) 或 "BEARISH" (掃高後看空) 或 None
        """
        
        if len(history) < self.lookback_bars + 2:
            return None
            
        recent_bars = history.tail(self.lookback_bars + 2)
        
        # 檢查掃低 (Bullish Sweep)
        # 邏輯：最近一根 K 線的最低點 < 之前幾根 K 線的最低點
        current_low = recent_bars.iloc[-1]['low']
        previous_lows = recent_bars.iloc[:-1]['low']
        
        if current_low < previous_lows.min():
            # 確認後續有反彈
            current_close = recent_bars.iloc[-1]['close']
            if current_close > current_low:
                return "BULLISH"
        
        # 檢查掃高 (Bearish Sweep)  
        # 邏輯：最近一根 K 線的最高點 > 之前幾根 K 線的最高點
        current_high = recent_bars.iloc[-1]['high']
        previous_highs = recent_bars.iloc[:-1]['high']
        
        if current_high > previous_highs.max():
            # 確認後續有回落
            current_close = recent_bars.iloc[-1]['close']
            if current_close < current_high:
                return "BEARISH"
                
        return None
    
    def _detect_engulfing_pattern(self, history: pd.DataFrame) -> Optional[str]:
        """
        偵測 Engulfing Pattern（吞噬型態）
        
        Returns:
            "BULLISH" 或 "BEARISH" 或 None
        """
        
        if len(history) < 2:
            return None
            
        prev_bar = history.iloc[-2]
        curr_bar = history.iloc[-1]
        
        # Bullish Engulfing
        # 前一根是空方K，當前根是多方K，且當前K的實體完全包覆前一根
        if (prev_bar['close'] < prev_bar['open'] and  # 前一根空方
            curr_bar['close'] > curr_bar['open'] and  # 當前根多方
            curr_bar['open'] < prev_bar['close'] and  # 當前開盤 < 前一收盤
            curr_bar['close'] > prev_bar['open']):    # 當前收盤 > 前一開盤
            return "BULLISH"
            
        # Bearish Engulfing
        # 前一根是多方K，當前根是空方K，且當前K的實體完全包覆前一根
        if (prev_bar['close'] > prev_bar['open'] and  # 前一根多方
            curr_bar['close'] < curr_bar['open'] and  # 當前根空方
            curr_bar['open'] > prev_bar['close'] and  # 當前開盤 > 前一收盤
            curr_bar['close'] < prev_bar['open']):    # 當前收盤 < 前一開盤
            return "BEARISH"
            
        return None
    
    def _detect_fair_value_gap(self, history: pd.DataFrame, 
                              direction: str) -> Optional[Dict]:
        """
        偵測 Fair Value Gap (FVG)
        
        Args:
            history: 歷史數據
            direction: 方向 ("BULLISH" or "BEARISH")
            
        Returns:
            FVG 數據字典或 None
        """
        
        if len(history) < 3:
            return None
            
        # 取最近三根K線
        bars = history.tail(3)
        bar1, bar2, bar3 = bars.iloc[0], bars.iloc[1], bars.iloc[2]
        
        if direction == "BULLISH":
            # Bullish FVG: bar3.low > bar1.high
            # Gap 區間: [bar1.high, bar3.low]
            if bar3['low'] > bar1['high']:
                gap_size_pips = (bar3['low'] - bar1['high']) * 10000  # 轉換成 pips
                
                if self.min_fvg_size_pips <= gap_size_pips <= self.max_fvg_size_pips:
                    return {
                        "direction": "BULLISH",
                        "top": bar3['low'],
                        "bottom": bar1['high'],
                        "size_pips": gap_size_pips,
                        "timestamp": bar3.name
                    }
                    
        elif direction == "BEARISH":
            # Bearish FVG: bar3.high < bar1.low  
            # Gap 區間: [bar3.high, bar1.low]
            if bar3['high'] < bar1['low']:
                gap_size_pips = (bar1['low'] - bar3['high']) * 10000
                
                if self.min_fvg_size_pips <= gap_size_pips <= self.max_fvg_size_pips:
                    return {
                        "direction": "BEARISH", 
                        "top": bar1['low'],
                        "bottom": bar3['high'],
                        "size_pips": gap_size_pips,
                        "timestamp": bar3.name
                    }
                    
        return None
    
    def _generate_signal(self, bar: BarData, fvg_data: Dict, 
                        direction: str) -> TradingSignal:
        """
        基於 FVG 數據生成交易信號
        """
        
        # 計算進場價格（FVG 中點）
        entry_price = (fvg_data["top"] + fvg_data["bottom"]) / 2
        
        if direction == "BULLISH":
            # 多頭信號
            stop_loss = fvg_data["bottom"] - (self.stop_loss_buffer_pips / 10000)
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.risk_reward_ratio) + (self.take_profit_buffer_pips / 10000)
            
            signal = TradingSignal(
                signal_type=SignalType.LONG,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=0.8,
                reason=f"ICT Bullish Setup: Liquidity Sweep + FVG ({fvg_data['size_pips']:.1f} pips)"
            )
            
        else:  # BEARISH
            # 空頭信號
            stop_loss = fvg_data["top"] + (self.stop_loss_buffer_pips / 10000)
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio) - (self.take_profit_buffer_pips / 10000)
            
            signal = TradingSignal(
                signal_type=SignalType.SHORT,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=0.8,
                reason=f"ICT Bearish Setup: Liquidity Sweep + FVG ({fvg_data['size_pips']:.1f} pips)"
            )
            
        return signal
    
    def calculate_position_size(self, signal: TradingSignal, 
                               account_balance: float,
                               risk_per_trade: float) -> float:
        """
        計算倉位大小
        """
        
        if not signal.stop_loss:
            return 0.0
            
        # 計算風險金額
        risk_amount = account_balance * risk_per_trade
        
        # 計算每單位風險
        if signal.signal_type == SignalType.LONG:
            risk_per_unit = signal.entry_price - signal.stop_loss
        else:
            risk_per_unit = signal.stop_loss - signal.entry_price
            
        if risk_per_unit <= 0:
            return 0.0
            
        # 計算倉位大小
        position_size = risk_amount / risk_per_unit
        
        return max(0.0, position_size)
    
    def get_strategy_status(self) -> Dict:
        """獲取策略狀態資訊"""
        return {
            "name": self.name,
            "session_active": True,  # 在實際使用時會檢查當前時間
            "parameters": self.parameters,
            "last_signals_count": len(self.last_signals),
            "risk_reward_ratio": self.risk_reward_ratio
        }