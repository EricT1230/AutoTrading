"""
風險管理模組

提供倉位計算、風控檢查等功能
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from .strategy_base import TradingSignal, SignalType


@dataclass
class RiskLimits:
    """風險限制設定"""
    max_risk_per_trade: float = 0.02  # 單筆最大風險 2%
    max_daily_loss: float = 0.05      # 單日最大虧損 5%
    max_positions: int = 3            # 最大同時持倉數
    max_leverage: float = 10.0        # 最大槓桿
    min_risk_reward_ratio: float = 1.5  # 最小風險收益比


@dataclass
class AccountState:
    """帳戶狀態"""
    total_balance: float
    available_balance: float
    daily_pnl: float
    open_positions: int
    current_risk: float


class RiskManager:
    """風險管理器"""
    
    def __init__(self, limits: RiskLimits):
        """
        初始化風險管理器
        
        Args:
            limits: 風險限制設定
        """
        self.limits = limits
        
    def calculate_position_size(self, 
                               signal: TradingSignal,
                               account_balance: float,
                               risk_per_trade: Optional[float] = None) -> float:
        """
        計算合適的倉位大小
        
        Args:
            signal: 交易信號
            account_balance: 帳戶餘額
            risk_per_trade: 風險比例（可覆蓋預設值）
            
        Returns:
            建議的倉位大小
        """
        
        # 使用指定風險或預設風險
        risk_ratio = risk_per_trade or self.limits.max_risk_per_trade
        
        # 計算風險金額
        risk_amount = account_balance * risk_ratio
        
        # 計算每單位風險
        if signal.stop_loss:
            if signal.signal_type == SignalType.LONG:
                risk_per_unit = signal.entry_price - signal.stop_loss
            else:
                risk_per_unit = signal.stop_loss - signal.entry_price
                
            if risk_per_unit <= 0:
                return 0.0
                
            # 計算倉位大小
            position_size = risk_amount / risk_per_unit
        else:
            # 沒有止損時，使用固定風險百分比
            position_size = risk_amount / signal.entry_price * 0.1  # 10% 作為預設
        
        # 應用槓桿限制
        max_position = account_balance * self.limits.max_leverage
        position_size = min(position_size, max_position)
        
        return max(0.0, position_size)
    
    def check_risk_limits(self, 
                         signal: TradingSignal,
                         account_state: AccountState) -> Tuple[bool, str]:
        """
        檢查風險限制
        
        Args:
            signal: 交易信號
            account_state: 當前帳戶狀態
            
        Returns:
            (是否通過, 失敗原因)
        """
        
        # 檢查日虧損限制
        daily_loss_ratio = abs(account_state.daily_pnl) / account_state.total_balance
        if daily_loss_ratio >= self.limits.max_daily_loss:
            return False, f"達到單日最大虧損限制 {self.limits.max_daily_loss*100:.1f}%"
        
        # 檢查持倉數限制
        if account_state.open_positions >= self.limits.max_positions:
            return False, f"達到最大持倉數限制 {self.limits.max_positions}"
        
        # 檢查風險收益比
        if signal.stop_loss and signal.take_profit:
            if signal.signal_type == SignalType.LONG:
                risk = signal.entry_price - signal.stop_loss
                reward = signal.take_profit - signal.entry_price
            else:
                risk = signal.stop_loss - signal.entry_price
                reward = signal.entry_price - signal.take_profit
                
            if risk > 0 and reward > 0:
                rr_ratio = reward / risk
                if rr_ratio < self.limits.min_risk_reward_ratio:
                    return False, f"風險收益比過低: {rr_ratio:.2f} < {self.limits.min_risk_reward_ratio}"
        
        # 檢查可用餘額
        if account_state.available_balance <= account_state.total_balance * 0.1:
            return False, "可用餘額不足"
        
        return True, ""
    
    def calculate_drawdown_protection(self, 
                                    current_balance: float,
                                    peak_balance: float) -> float:
        """
        計算回撤保護倍數
        
        Args:
            current_balance: 當前餘額
            peak_balance: 歷史最高餘額
            
        Returns:
            風險調整倍數 (0.0-1.0)
        """
        
        if peak_balance <= 0:
            return 1.0
            
        drawdown = (peak_balance - current_balance) / peak_balance
        
        # 根據回撤程度調整風險
        if drawdown < 0.05:  # 5%以內
            return 1.0
        elif drawdown < 0.10:  # 5-10%
            return 0.8
        elif drawdown < 0.15:  # 10-15%
            return 0.6
        elif drawdown < 0.20:  # 15-20%
            return 0.4
        else:  # 超過20%
            return 0.2
    
    def get_emergency_stop_conditions(self) -> Dict[str, float]:
        """
        獲取緊急停止條件
        
        Returns:
            緊急停止條件字典
        """
        return {
            "max_daily_loss": self.limits.max_daily_loss,
            "max_drawdown": 0.25,  # 25% 最大回撤
            "consecutive_losses": 5,  # 連續虧損筆數
            "api_error_count": 10,   # API錯誤次數
        }
    
    def update_risk_parameters(self, 
                              performance_metrics: Dict) -> RiskLimits:
        """
        根據歷史表現動態調整風險參數
        
        Args:
            performance_metrics: 績效指標
            
        Returns:
            調整後的風險限制
        """
        
        new_limits = RiskLimits(
            max_risk_per_trade=self.limits.max_risk_per_trade,
            max_daily_loss=self.limits.max_daily_loss,
            max_positions=self.limits.max_positions,
            max_leverage=self.limits.max_leverage,
            min_risk_reward_ratio=self.limits.min_risk_reward_ratio
        )
        
        # 根據勝率調整
        win_rate = performance_metrics.get("win_rate", 0.5)
        if win_rate > 0.6:
            # 高勝率時可以稍微增加風險
            new_limits.max_risk_per_trade = min(
                self.limits.max_risk_per_trade * 1.2, 0.03
            )
        elif win_rate < 0.4:
            # 低勝率時降低風險
            new_limits.max_risk_per_trade = max(
                self.limits.max_risk_per_trade * 0.8, 0.005
            )
        
        # 根據夏普比率調整
        sharpe_ratio = performance_metrics.get("sharpe_ratio", 0.0)
        if sharpe_ratio > 1.5:
            new_limits.max_positions = min(self.limits.max_positions + 1, 5)
        elif sharpe_ratio < 0.5:
            new_limits.max_positions = max(self.limits.max_positions - 1, 1)
        
        return new_limits