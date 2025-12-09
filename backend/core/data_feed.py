import asyncio
import json
from typing import Dict, List, Optional
from loguru import logger
import websockets
from datetime import datetime

from ..core.event_engine import EventEngine, Event, EventType
from ..exchange.exchange_service import ExchangeService

class DataFeed:
    """
    Real-time Data Feed.
    Uses WebSockets for real-time updates where possible, falls back to polling.
    Currently implements Binance Public WebSocket for K-lines.
    """
    
    def __init__(self, event_engine: EventEngine, exchange_service: ExchangeService):
        self.event_engine = event_engine
        self.exchange_service = exchange_service
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.subscribed_symbols: List[str] = []
        self.timeframe = "5m"
        
    async def start(self, symbols: List[str], timeframe: str = "5m"):
        """Start the data feed."""
        self.running = True
        self.subscribed_symbols = symbols
        self.timeframe = timeframe
        
        # Start WebSocket task
        self.tasks.append(asyncio.create_task(self._websocket_loop()))
        
        logger.info(f"Data Feed started for {symbols} ({timeframe})")

    async def stop(self):
        """Stop the data feed."""
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks = []
        logger.info("Data Feed stopped")

    async def _websocket_loop(self):
        """Main WebSocket loop for Binance."""
        # Construct stream names
        # Binance Future WS format: <symbol>@kline_<interval>
        # Symbol needs to be lowercase
        streams = []
        for symbol in self.subscribed_symbols:
            clean_symbol = symbol.replace("/", "").lower()
            streams.append(f"{clean_symbol}@kline_{self.timeframe}")
            
        stream_string = "/".join(streams)
        url = f"wss://fstream.binance.com/stream?streams={stream_string}"
        
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to Binance WebSocket: {url}")
                    
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        if 'data' in data:
                            await self._process_kline_message(data['data'])
                            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _process_kline_message(self, data: Dict):
        """Process incoming K-line message from WebSocket."""
        try:
            # Binance K-line format
            k = data['k']
            is_closed = k['x']
            
            # Map to our internal format
            kline_data = {
                'symbol': data['s'],  # Symbol
                'timestamp': k['t'],  # Open time
                'open': float(k['o']),
                'high': float(k['h']),
                'low': float(k['l']),
                'close': float(k['c']),
                'volume': float(k['v']),
                'closed': is_closed
            }
            
            # Dispatch event
            event = Event(
                type=EventType.KLINE_UPDATE,
                data=kline_data,
                timestamp=datetime.now(),
                source="binance_ws"
            )
            await self.event_engine.put(event)
            
            # If candle closed, maybe trigger other events?
            
        except Exception as e:
            logger.error(f"Error processing K-line message: {e}")
