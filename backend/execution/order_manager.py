import asyncio
from typing import Dict, Optional, List
from loguru import logger
from datetime import datetime

from ..core.event_engine import EventEngine, Event, EventType
from ..exchange.exchange_service import ExchangeService

class OrderManager:
    """
    Manages order execution and position tracking.
    """
    
    def __init__(self, event_engine: EventEngine, exchange_service: ExchangeService):
        self.event_engine = event_engine
        self.exchange_service = exchange_service
        self.active_positions: Dict[str, Dict] = {} # Symbol -> Position Data
        self.open_orders: List[Dict] = []
        
    def start(self):
        """Start the order manager."""
        self.event_engine.register(EventType.SIGNAL_GENERATED, self.on_signal)
        logger.info("Order Manager started")

    def stop(self):
        """Stop the order manager."""
        self.event_engine.unregister(EventType.SIGNAL_GENERATED, self.on_signal)
        logger.info("Order Manager stopped")

    async def on_signal(self, event: Event):
        """Handle trading signals."""
        signal = event.data
        symbol = "BTC/USDT" # TODO: Get from signal or config
        
        logger.info(f"Received signal: {signal}")
        
        # Basic Risk Check: Don't open if already have position
        if symbol in self.active_positions and signal['type'] == "ENTRY":
            logger.warning(f"Ignored ENTRY signal for {symbol}: Position already exists")
            return
            
        if signal['type'] == "ENTRY":
            await self._execute_entry(signal, symbol)
        elif signal['type'] == "EXIT":
            await self._execute_exit(signal, symbol)

    async def _execute_entry(self, signal: Dict, symbol: str):
        """Execute entry order."""
        try:
            # Calculate quantity (Simplified: Fixed 0.001 BTC for now)
            # In production, this should use Risk Management logic
            quantity = 0.001 
            side = "buy" if signal['direction'] == "LONG" else "sell"
            
            # Execute Market Order
            order = await self.exchange_service.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=quantity
            )
            
            # Record Position
            self.active_positions[symbol] = {
                "direction": signal['direction'],
                "entry_price": order.get('average', signal['price']),
                "quantity": quantity,
                "stop_loss": signal.get('stop_loss'),
                "take_profit": signal.get('take_profit'),
                "timestamp": datetime.now()
            }
            
            # Emit Order Event
            await self.event_engine.put(Event(
                type=EventType.ORDER_FILLED,
                data=order,
                source="OrderManager"
            ))
            
            logger.info(f"Opened {signal['direction']} position for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to execute entry: {e}")

    async def _execute_exit(self, signal: Dict, symbol: str):
        """Execute exit order."""
        if symbol not in self.active_positions:
            return
            
        try:
            position = self.active_positions[symbol]
            side = "sell" if position['direction'] == "LONG" else "buy"
            quantity = position['quantity']
            
            # Execute Market Order
            order = await self.exchange_service.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=quantity
            )
            
            # Clear Position
            del self.active_positions[symbol]
            
            # Emit Order Event
            await self.event_engine.put(Event(
                type=EventType.ORDER_FILLED,
                data=order,
                source="OrderManager"
            ))
            
            logger.info(f"Closed position for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to execute exit: {e}")
