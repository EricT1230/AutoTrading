import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import json

from ..core.event_engine import EventEngine, Event, EventType
from ..core.data_feed import DataFeed
from ..exchange.exchange_service import ExchangeService
from ..strategy.ict_ny_fvg import ICTNYFVGStrategy
from ..execution.order_manager import OrderManager

# Global Instances
event_engine = EventEngine()
exchange_service = ExchangeService(testnet=True) # Default to testnet
data_feed = DataFeed(event_engine, exchange_service)
order_manager = OrderManager(event_engine, exchange_service)
strategy = ICTNYFVGStrategy(event_engine, {"symbol": "BTC/USDT"})

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Trading Bot...")
    event_engine.start()
    order_manager.start()
    await exchange_service.initialize()
    
    # Start Data Feed & Strategy
    await data_feed.start(["BTC/USDT"])
    await strategy.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Trading Bot...")
    await strategy.stop()
    await data_feed.stop()
    order_manager.stop()
    await exchange_service.close()
    await event_engine.stop()

app = FastAPI(title="AutoTrading Bot API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Event Listener to Broadcast to Frontend
async def broadcast_event(event: Event):
    # Convert event to JSON-serializable dict
    data = {
        "type": event.type.value,
        "data": event.data,
        "timestamp": event.timestamp.isoformat(),
        "source": event.source
    }
    await manager.broadcast(json.dumps(data))

# Register Broadcast Listener
# We need to do this after event_engine is created
event_engine.register(EventType.KLINE_UPDATE, broadcast_event)
event_engine.register(EventType.SIGNAL_GENERATED, broadcast_event)
event_engine.register(EventType.ORDER_FILLED, broadcast_event)

@app.get("/")
async def root():
    return {"status": "running", "message": "AutoTrading Bot API is active"}

@app.get("/status")
async def get_status():
    return {
        "strategy": "ICT_NY_FVG",
        "active": strategy.active,
        "positions": order_manager.active_positions
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
