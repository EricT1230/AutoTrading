import ccxt.async_support as ccxt
import asyncio
from typing import Dict, Optional, List, Any
from loguru import logger
from datetime import datetime

class ExchangeService:
    """
    Async wrapper for CCXT exchange interactions.
    Handles connection, authentication, and error management.
    """
    
    def __init__(self, exchange_id: str = "binance", testnet: bool = False, api_key: str = None, secret: str = None):
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.api_key = api_key
        self.secret = secret
        self.exchange: Optional[ccxt.Exchange] = None
        
    async def initialize(self):
        """Initialize the exchange connection."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Default to futures for trading
                }
            })
            
            if self.testnet:
                self.exchange.set_sandbox_mode(True)
                
            # Load markets to verify connection
            await self.exchange.load_markets()
            logger.info(f"Successfully connected to {self.exchange_id} (Testnet: {self.testnet})")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise

    async def close(self):
        """Close the exchange connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("Exchange connection closed")

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List[List[Any]]:
        """Fetch OHLCV data."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
            
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
            
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
            
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise

    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None) -> Dict:
        """Create a new order."""
        if not self.exchange:
            raise RuntimeError("Exchange not initialized")
            
        try:
            params = {}
            order = await self.exchange.create_order(symbol, type, side, amount, price, params)
            logger.info(f"Order created: {side} {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
