"""
交易所基礎類別

提供統一的交易所介面，支援多個交易所的無縫切換
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
from dataclasses import dataclass


class OrderType(Enum):
    """訂單類型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """訂單方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """訂單狀態"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class Order:
    """訂單數據結構"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: float = 0.0
    remaining_amount: float = 0.0
    timestamp: Optional[pd.Timestamp] = None


@dataclass
class Balance:
    """餘額數據結構"""
    currency: str
    total: float
    free: float
    used: float


@dataclass
class Position:
    """持倉數據結構"""
    symbol: str
    size: float  # 正數=多頭，負數=空頭
    entry_price: float
    mark_price: float
    pnl: float
    percentage: float


class ExchangeBase(ABC):
    """
    交易所基礎抽象類別
    
    定義所有交易所實作必須遵循的介面
    """
    
    def __init__(self, config: Dict):
        """
        初始化交易所連線
        
        Args:
            config: 交易所配置（API金鑰等）
        """
        self.config = config
        self.name = config.get("name", "BaseExchange")
        self.testnet = config.get("testnet", True)
        
    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str, 
                          limit: int = 100) -> pd.DataFrame:
        """
        獲取歷史K線數據
        
        Args:
            symbol: 交易對符號 (e.g., 'BTCUSDT')
            timeframe: 時間框架 (e.g., '5m', '1h')
            limit: 返回數據筆數
            
        Returns:
            包含 OHLCV 數據的 DataFrame
        """
        pass
    
    @abstractmethod
    async def create_order(self, symbol: str, order_type: OrderType,
                          side: OrderSide, amount: float,
                          price: Optional[float] = None) -> Order:
        """
        建立訂單
        
        Args:
            symbol: 交易對符號
            order_type: 訂單類型
            side: 買賣方向
            amount: 交易數量
            price: 限價單價格（市價單可為None）
            
        Returns:
            Order 物件
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消訂單
        
        Args:
            order_id: 訂單ID
            symbol: 交易對符號
            
        Returns:
            取消是否成功
        """
        pass
    
    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """
        查詢訂單狀態
        
        Args:
            order_id: 訂單ID
            symbol: 交易對符號
            
        Returns:
            Order 物件
        """
        pass
    
    @abstractmethod
    async def fetch_balance(self) -> Dict[str, Balance]:
        """
        獲取帳戶餘額
        
        Returns:
            幣種餘額字典
        """
        pass
    
    @abstractmethod
    async def fetch_positions(self) -> List[Position]:
        """
        獲取持倉資訊
        
        Returns:
            Position 列表
        """
        pass
    
    async def get_account_info(self) -> Dict:
        """獲取帳戶基本資訊"""
        balance = await self.fetch_balance()
        positions = await self.fetch_positions()
        
        total_balance = sum(b.total for b in balance.values())
        total_pnl = sum(p.pnl for p in positions)
        
        return {
            "total_balance": total_balance,
            "total_pnl": total_pnl,
            "positions_count": len(positions),
            "currencies": list(balance.keys())
        }
    
    def validate_symbol(self, symbol: str) -> bool:
        """驗證交易對格式"""
        # 基本格式驗證
        if not symbol or "/" not in symbol:
            return False
        return True
    
    def get_exchange_info(self) -> Dict:
        """返回交易所基本資訊"""
        return {
            "name": self.name,
            "testnet": self.testnet,
            "status": "connected"
        }