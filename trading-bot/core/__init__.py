"""
AutoTrading Core Module

提供策略、交易所、風控等核心功能的模組化實作
"""

from .strategy_base import StrategyBase
from .exchange_base import ExchangeBase
from .utils_logging import setup_logging

__version__ = "0.1.0"
__author__ = "Trading Bot Team"

__all__ = [
    "StrategyBase",
    "ExchangeBase", 
    "setup_logging"
]