import asyncio
from typing import Dict, List, Callable, Any, Awaitable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

class EventType(Enum):
    # Market Data Events
    TICKER_UPDATE = "TICKER_UPDATE"
    KLINE_UPDATE = "KLINE_UPDATE"
    ORDER_BOOK_UPDATE = "ORDER_BOOK_UPDATE"
    
    # Trading Events
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_UPDATE = "POSITION_UPDATE"
    
    # System Events
    ERROR = "ERROR"
    SYSTEM_STATUS = "SYSTEM_STATUS"

@dataclass
class Event:
    type: EventType
    data: Any
    timestamp: datetime = datetime.now()
    source: str = "system"

class EventEngine:
    """
    Central Event Engine for the trading bot.
    Handles asynchronous event dispatching and subscription.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task = None

    def start(self):
        """Start the event processing loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("Event Engine started")

    async def stop(self):
        """Stop the event processing loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event Engine stopped")

    def register(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]):
        """Register a handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.value}")

    def unregister(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]):
        """Unregister a handler."""
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    async def put(self, event: Event):
        """Put an event into the queue."""
        await self._queue.put(event)

    async def _process_queue(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = await self._queue.get()
                if event.type in self._subscribers:
                    handlers = self._subscribers[event.type]
                    # Execute handlers concurrently
                    await asyncio.gather(
                        *[self._safe_execute(handler, event) for handler in handlers],
                        return_exceptions=True
                    )
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")

    async def _safe_execute(self, handler: Callable[[Event], Awaitable[None]], event: Event):
        """Execute a handler safely, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler {handler.__name__}: {e}")
