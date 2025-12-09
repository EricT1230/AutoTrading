"""
策略基礎類別

定義所有交易策略必須實作的介面，確保策略邏輯與交易執行解耦
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
from dataclasses import dataclass


class SignalType(Enum):
    """交易信號類型"""
    LONG = "LONG"
    SHORT = "SHORT" 
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"
    FLAT = "FLAT"


@dataclass
class TradingSignal:
    """交易信號數據結構"""
    signal_type: SignalType
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 1.0  # 信號強度 0-1
    reason: str = ""  # 信號產生原因
    

@dataclass
class BarData:
    """K線數據結構"""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    

class StrategyBase(ABC):
    """
    策略基礎抽象類別
    
    所有具體策略都必須繼承此類別並實作核心方法
    """
    
    def __init__(self, config: Dict):
        """
        初始化策略
        
        Args:
            config: 策略配置參數
        """
        self.config = config
        self.name = config.get("name", "BaseStrategy")
        self.parameters = config.get("parameters", {})
        
    @abstractmethod
    def on_bar(self, bar: BarData, history: pd.DataFrame) -> Optional[TradingSignal]:
        """
        處理新的K線數據
        
        Args:
            bar: 當前K線數據
            history: 歷史K線數據 DataFrame
            
        Returns:
            TradingSignal或None
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: TradingSignal, 
                               account_balance: float,
                               risk_per_trade: float) -> float:
        """
        計算開倉大小
        
        Args:
            signal: 交易信號
            account_balance: 帳戶餘額
            risk_per_trade: 每筆交易風險比例
            
        Returns:
            開倉數量
        """
        pass
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        驗證交易信號的有效性
        
        Args:
            signal: 待驗證的信號
            
        Returns:
            信號是否有效
        """
        if signal is None:
            return False
            
        # 基本驗證
        if signal.entry_price <= 0:
            return False
            
        if signal.stop_loss and signal.take_profit:
            # 檢查風險收益比是否合理
            if signal.signal_type == SignalType.LONG:
                risk = signal.entry_price - signal.stop_loss
                reward = signal.take_profit - signal.entry_price
            else:
                risk = signal.stop_loss - signal.entry_price  
                reward = signal.entry_price - signal.take_profit
                
            if risk <= 0 or reward <= 0:
                return False
                
            # 風險收益比至少 1:1
            if reward / risk < 1.0:
                return False
                
        return True
    
    def get_strategy_info(self) -> Dict:
        """返回策略基本資訊"""
        return {
            "name": self.name,
            "parameters": self.parameters,
            "version": "1.0.0"
        }