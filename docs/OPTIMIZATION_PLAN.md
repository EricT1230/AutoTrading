# AutoTrading 系統優化實作計畫書

> 版本：1.0
> 日期：2025-12-10
> 優先級：P0 > P1 > P2 > P3

---

## 目錄

1. [P0: WebSocket 替代輪詢機制](#p0-websocket-替代輪詢機制)
2. [P1: Zustand 狀態管理](#p1-zustand-狀態管理)
3. [P1: Redis Pub/Sub 後端狀態共享](#p1-redis-pubsub-後端狀態共享)
4. [P2: TanStack Query 數據緩存](#p2-tanstack-query-數據緩存)
5. [P2: 移除 Streamlit 整合到 React](#p2-移除-streamlit-整合到-react)
6. [P3: Kubernetes 部署配置](#p3-kubernetes-部署配置)

---

## P0: WebSocket 替代輪詢機制

### 問題分析

當前 `Dashboard.tsx` 使用 2 秒輪詢：

```typescript
// Dashboard.tsx:140 - 效能問題
const interval = setInterval(async () => {
    const response = await fetch(`${backendUrl}/api/latest`);
    // ...
}, 2000);
```

**問題**：
- 無論是否有新數據都發送請求
- 延遲固定 2 秒，對交易系統太慢
- 伺服器負載隨用戶數線性增長
- 已安裝 `react-use-websocket` 但未使用

### 實作步驟

#### 步驟 1：安裝依賴（已完成）

```bash
# 已在 package.json 中
"react-use-websocket": "^4.13.0"
```

#### 步驟 2：建立 WebSocket Hook

**新增檔案**: `frontend/src/hooks/useTrading.ts`

```typescript
import { useCallback, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useTradingStore } from '../store/tradingStore';

const WS_URL = 'ws://localhost:8000/ws';

interface KlineMessage {
  type: 'KLINE_UPDATE' | 'TICKER_UPDATE' | 'CONNECTION_SUCCESS';
  data: {
    symbol: string;
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timeframe: string;
  };
}

export const useTrading = () => {
  const {
    updateKline,
    setConnectionStatus,
    setCurrentPrice,
    addLog
  } = useTradingStore();

  const didUnmount = useRef(false);

  const {
    sendJsonMessage,
    lastJsonMessage,
    readyState
  } = useWebSocket(WS_URL, {
    shouldReconnect: () => !didUnmount.current,
    reconnectAttempts: 10,
    reconnectInterval: (attemptNumber) =>
      Math.min(Math.pow(2, attemptNumber) * 1000, 30000),
    onOpen: () => {
      addLog('WebSocket 連接已建立', 'success');
    },
    onClose: () => {
      addLog('WebSocket 連接已關閉', 'info');
    },
    onError: () => {
      addLog('WebSocket 連接錯誤', 'error');
    },
    heartbeat: {
      message: JSON.stringify({ type: 'ping' }),
      interval: 30000,
      timeout: 60000,
    },
  });

  // 處理連接狀態
  useEffect(() => {
    const statusMap: Record<ReadyState, 'connected' | 'connecting' | 'disconnected'> = {
      [ReadyState.CONNECTING]: 'connecting',
      [ReadyState.OPEN]: 'connected',
      [ReadyState.CLOSING]: 'disconnected',
      [ReadyState.CLOSED]: 'disconnected',
      [ReadyState.UNINSTANTIATED]: 'disconnected',
    };
    setConnectionStatus(statusMap[readyState]);
  }, [readyState, setConnectionStatus]);

  // 處理接收到的消息
  useEffect(() => {
    if (!lastJsonMessage) return;

    const message = lastJsonMessage as KlineMessage;

    switch (message.type) {
      case 'KLINE_UPDATE':
        updateKline({
          time: message.data.time,
          open: message.data.open,
          high: message.data.high,
          low: message.data.low,
          close: message.data.close,
        });
        setCurrentPrice(message.data.close);
        break;

      case 'TICKER_UPDATE':
        if (message.data.price) {
          setCurrentPrice(message.data.price);
        }
        break;

      case 'CONNECTION_SUCCESS':
        addLog('已成功連接到交易伺服器', 'success');
        break;
    }
  }, [lastJsonMessage, updateKline, setCurrentPrice, addLog]);

  // 訂閱交易對
  const subscribe = useCallback((symbols: string[], timeframe: string) => {
    sendJsonMessage({
      type: 'subscribe',
      symbols,
      timeframe,
    });
  }, [sendJsonMessage]);

  // 取消訂閱
  const unsubscribe = useCallback(() => {
    sendJsonMessage({
      type: 'unsubscribe',
    });
  }, [sendJsonMessage]);

  // 清理
  useEffect(() => {
    return () => {
      didUnmount.current = true;
    };
  }, []);

  return {
    subscribe,
    unsubscribe,
    isConnected: readyState === ReadyState.OPEN,
  };
};
```

#### 步驟 3：修改後端 WebSocket 處理

**修改檔案**: `backend/main.py`

```python
# 在 websocket_endpoint 函數中添加訂閱處理

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_SUCCESS",
            "data": {
                "message": "WebSocket 連接已建立",
                "timestamp": datetime.now().isoformat(),
            }
        }))

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))

                elif message.get('type') == 'subscribe':
                    # 處理訂閱請求
                    symbols = message.get('symbols', ['BTC/USDT'])
                    timeframe = message.get('timeframe', '5m')

                    # 更新訂閱
                    current_subscriptions['symbols'] = symbols
                    current_subscriptions['timeframe'] = timeframe

                    # 啟動實時數據
                    def on_kline_update(kline: KlineData):
                        asyncio.create_task(websocket.send_text(json.dumps({
                            "type": "KLINE_UPDATE",
                            "data": {
                                "symbol": kline.symbol,
                                "time": kline.timestamp // 1000,
                                "open": kline.open,
                                "high": kline.high,
                                "low": kline.low,
                                "close": kline.close,
                                "volume": kline.volume,
                                "timeframe": kline.timeframe
                            }
                        })))

                    okx_feed.set_kline_callback(on_kline_update)
                    okx_feed.start_realtime_feed(symbols, timeframe)

                    await websocket.send_text(json.dumps({
                        "type": "SUBSCRIBED",
                        "data": {"symbols": symbols, "timeframe": timeframe}
                    }))

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket 消息處理錯誤: {e}")

    finally:
        manager.disconnect(websocket)
```

#### 步驟 4：修改 Dashboard 組件

**修改檔案**: `frontend/src/components/Dashboard.tsx`

```typescript
// 移除輪詢代碼，改用 WebSocket Hook
import { useTrading } from '../hooks/useTrading';
import { useTradingStore } from '../store/tradingStore';

export const Dashboard: React.FC = () => {
  const { subscribe, isConnected } = useTrading();
  const {
    klines,
    currentPrice,
    connectionStatus,
    logs,
    selectedTimeframe,
    setSelectedTimeframe
  } = useTradingStore();

  // 初始化訂閱
  useEffect(() => {
    if (isConnected) {
      subscribe(['BTC/USDT'], selectedTimeframe);
    }
  }, [isConnected, selectedTimeframe, subscribe]);

  // 移除 setInterval 輪詢代碼
  // ...其餘 JSX
};
```

### 效能對比

| 指標 | 輪詢 (現狀) | WebSocket (優化後) |
|------|-----------|-------------------|
| 延遲 | 2000ms | <100ms |
| 請求數/分鐘 | 30 | 只推送變化 |
| 伺服器負載 | O(n) 用戶數 | O(1) |
| 網路流量 | 高 | 低 |

---

## P1: Zustand 狀態管理

### 問題分析

當前 `Dashboard.tsx` 有過多的 useState：

```typescript
const [klines, setKlines] = useState<Kline[]>([]);
const [logs, setLogs] = useState<LogEntry[]>([]);
const [status, setStatus] = useState({ ... });
const [currentPrice, setCurrentPrice] = useState<number>(0);
const [connectionStatus, setConnectionStatus] = useState(...);
// ... 超過 10 個 useState
```

**問題**：
- 狀態分散難以維護
- 跨組件共享困難
- 無法持久化
- 測試困難

### 實作步驟

#### 步驟 1：安裝 Zustand

```bash
cd frontend
npm install zustand immer
```

#### 步驟 2：建立 Store

**新增檔案**: `frontend/src/store/tradingStore.ts`

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// 類型定義
interface Kline {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'error' | 'success';
}

interface TradingState {
  // 市場數據
  klines: Kline[];
  currentPrice: number;
  priceChange: number;

  // 連接狀態
  connectionStatus: 'connected' | 'connecting' | 'disconnected';

  // UI 狀態
  selectedTimeframe: string;
  isLoading: boolean;

  // 系統狀態
  status: {
    active: boolean;
    strategy: string;
  };

  // 日誌
  logs: LogEntry[];

  // 統計
  updateCount: number;
  lastUpdateTime: Date | null;
}

interface TradingActions {
  // 市場數據操作
  updateKline: (kline: Kline) => void;
  setKlines: (klines: Kline[]) => void;
  setCurrentPrice: (price: number) => void;

  // 連接狀態操作
  setConnectionStatus: (status: TradingState['connectionStatus']) => void;

  // UI 操作
  setSelectedTimeframe: (timeframe: string) => void;
  setIsLoading: (loading: boolean) => void;

  // 系統操作
  setStatus: (status: TradingState['status']) => void;

  // 日誌操作
  addLog: (message: string, type: LogEntry['type']) => void;
  clearLogs: () => void;

  // 重置
  reset: () => void;
}

const initialState: TradingState = {
  klines: [],
  currentPrice: 0,
  priceChange: 0,
  connectionStatus: 'disconnected',
  selectedTimeframe: '5m',
  isLoading: false,
  status: { active: false, strategy: 'ICT NY FVG' },
  logs: [],
  updateCount: 0,
  lastUpdateTime: null,
};

export const useTradingStore = create<TradingState & TradingActions>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // 更新單根 K 線（實時更新用）
        updateKline: (kline) => set((state) => {
          const lastIndex = state.klines.length - 1;

          if (lastIndex < 0) {
            state.klines.push(kline);
          } else if (kline.time > state.klines[lastIndex].time) {
            // 新 K 線
            if (state.klines.length >= 100) {
              state.klines.shift();
            }
            state.klines.push(kline);
          } else if (kline.time === state.klines[lastIndex].time) {
            // 更新當前 K 線
            state.klines[lastIndex] = kline;
          }

          state.currentPrice = kline.close;
          state.updateCount += 1;
          state.lastUpdateTime = new Date();
        }),

        // 設置完整 K 線數據（初始化用）
        setKlines: (klines) => set((state) => {
          state.klines = klines;
          if (klines.length > 0) {
            state.currentPrice = klines[klines.length - 1].close;
          }
        }),

        setCurrentPrice: (price) => set((state) => {
          const prevPrice = state.currentPrice;
          state.currentPrice = price;
          if (prevPrice > 0) {
            state.priceChange = ((price - prevPrice) / prevPrice) * 100;
          }
        }),

        setConnectionStatus: (status) => set((state) => {
          state.connectionStatus = status;
        }),

        setSelectedTimeframe: (timeframe) => set((state) => {
          state.selectedTimeframe = timeframe;
        }),

        setIsLoading: (loading) => set((state) => {
          state.isLoading = loading;
        }),

        setStatus: (status) => set((state) => {
          state.status = status;
        }),

        addLog: (message, type) => set((state) => {
          const newLog: LogEntry = {
            timestamp: new Date().toLocaleTimeString(),
            message,
            type,
          };
          state.logs.unshift(newLog);
          // 保留最近 50 條日誌
          if (state.logs.length > 50) {
            state.logs.pop();
          }
        }),

        clearLogs: () => set((state) => {
          state.logs = [];
        }),

        reset: () => set(initialState),
      })),
      {
        name: 'trading-store',
        // 只持久化部分狀態
        partialize: (state) => ({
          selectedTimeframe: state.selectedTimeframe,
        }),
      }
    ),
    { name: 'TradingStore' }
  )
);

// 選擇器（優化性能）
export const selectKlines = (state: TradingState) => state.klines;
export const selectCurrentPrice = (state: TradingState) => state.currentPrice;
export const selectConnectionStatus = (state: TradingState) => state.connectionStatus;
export const selectLogs = (state: TradingState) => state.logs;
```

#### 步驟 3：建立其他 Store（可選）

**新增檔案**: `frontend/src/store/settingsStore.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Settings {
  theme: 'dark' | 'light';
  riskPerTrade: number;
  maxPositions: number;
  notifications: boolean;
}

interface SettingsActions {
  setTheme: (theme: Settings['theme']) => void;
  setRiskPerTrade: (risk: number) => void;
  setMaxPositions: (max: number) => void;
  toggleNotifications: () => void;
}

export const useSettingsStore = create<Settings & SettingsActions>()(
  persist(
    (set) => ({
      theme: 'dark',
      riskPerTrade: 1.0,
      maxPositions: 3,
      notifications: true,

      setTheme: (theme) => set({ theme }),
      setRiskPerTrade: (risk) => set({ riskPerTrade: risk }),
      setMaxPositions: (max) => set({ maxPositions: max }),
      toggleNotifications: () => set((state) => ({
        notifications: !state.notifications
      })),
    }),
    { name: 'settings-store' }
  )
);
```

#### 步驟 4：修改組件使用 Store

**修改檔案**: `frontend/src/components/Dashboard.tsx`

```typescript
import { useTradingStore } from '../store/tradingStore';
import { useShallow } from 'zustand/react/shallow';

export const Dashboard: React.FC = () => {
  // 使用 shallow 比較避免不必要的重新渲染
  const {
    klines,
    currentPrice,
    connectionStatus,
    logs,
    selectedTimeframe,
    isLoading,
    status,
    updateCount,
    lastUpdateTime,
  } = useTradingStore(
    useShallow((state) => ({
      klines: state.klines,
      currentPrice: state.currentPrice,
      connectionStatus: state.connectionStatus,
      logs: state.logs,
      selectedTimeframe: state.selectedTimeframe,
      isLoading: state.isLoading,
      status: state.status,
      updateCount: state.updateCount,
      lastUpdateTime: state.lastUpdateTime,
    }))
  );

  const {
    setSelectedTimeframe,
    addLog,
    setIsLoading
  } = useTradingStore();

  // 移除所有 useState
  // 直接使用 store 中的狀態和方法

  return (
    // ...JSX 保持不變
  );
};
```

### 目錄結構

```
frontend/src/
├── store/
│   ├── index.ts              # 導出所有 store
│   ├── tradingStore.ts       # 交易相關狀態
│   └── settingsStore.ts      # 設置相關狀態
├── hooks/
│   ├── useTrading.ts         # WebSocket hook
│   └── useApi.ts             # API hook
└── components/
    ├── Dashboard.tsx         # 使用 store
    └── Chart.tsx
```

---

## P1: Redis Pub/Sub 後端狀態共享

### 問題分析

當前後端使用全域變數：

```python
# main.py
okx_feed = OKXDataFeed()  # 單例
connected_clients: List[WebSocket] = []  # 全域列表
current_subscriptions = { ... }  # 全域狀態
```

**問題**：
- 無法水平擴展（多實例部署）
- 狀態不同步
- 單點故障

### 實作步驟

#### 步驟 1：安裝依賴

```bash
cd backend
pip install aioredis
```

**更新 requirements.txt**:

```txt
aioredis>=2.0.0
```

#### 步驟 2：建立 Redis 連接管理器

**新增檔案**: `backend/core/redis_manager.py`

```python
"""
Redis Pub/Sub 管理器
用於多實例部署時的狀態同步
"""

import asyncio
import json
from typing import Callable, Dict, Optional, Set
import aioredis
from loguru import logger


class RedisManager:
    """Redis 連接和 Pub/Sub 管理器"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.subscribers: Dict[str, Set[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self):
        """建立 Redis 連接"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis.pubsub()
            logger.info(f"Redis 連接成功: {self.redis_url}")
            return True
        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            return False

    async def disconnect(self):
        """關閉 Redis 連接"""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()

        if self.redis:
            await self.redis.close()

        logger.info("Redis 連接已關閉")

    async def publish(self, channel: str, message: Dict):
        """發布消息到頻道"""
        if not self.redis:
            logger.error("Redis 未連接")
            return False

        try:
            message_str = json.dumps(message)
            await self.redis.publish(channel, message_str)
            logger.debug(f"發布消息到 {channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"發布消息失敗: {e}")
            return False

    async def subscribe(self, channel: str, callback: Callable):
        """訂閱頻道"""
        if not self.pubsub:
            logger.error("Redis Pub/Sub 未初始化")
            return

        if channel not in self.subscribers:
            self.subscribers[channel] = set()
            await self.pubsub.subscribe(channel)
            logger.info(f"已訂閱頻道: {channel}")

        self.subscribers[channel].add(callback)

    async def unsubscribe(self, channel: str, callback: Callable = None):
        """取消訂閱頻道"""
        if channel not in self.subscribers:
            return

        if callback:
            self.subscribers[channel].discard(callback)
            if not self.subscribers[channel]:
                await self.pubsub.unsubscribe(channel)
                del self.subscribers[channel]
        else:
            await self.pubsub.unsubscribe(channel)
            del self.subscribers[channel]

    async def start_listener(self):
        """啟動消息監聽器"""
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("Redis 消息監聽器已啟動")

    async def _listen(self):
        """監聽消息的內部方法"""
        while self._running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message and message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])

                    if channel in self.subscribers:
                        for callback in self.subscribers[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"回調處理錯誤: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"監聽消息錯誤: {e}")
                await asyncio.sleep(1)

    # 緩存操作
    async def set_cache(self, key: str, value: Dict, expire: int = 3600):
        """設置緩存"""
        if not self.redis:
            return False

        try:
            await self.redis.setex(key, expire, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"設置緩存失敗: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Dict]:
        """獲取緩存"""
        if not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"獲取緩存失敗: {e}")
            return None

    async def delete_cache(self, key: str):
        """刪除緩存"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"刪除緩存失敗: {e}")
            return False


# 頻道常量
class Channels:
    KLINE_UPDATE = "kline:update"
    TICKER_UPDATE = "ticker:update"
    ORDER_UPDATE = "order:update"
    SIGNAL_UPDATE = "signal:update"
    SYSTEM_STATUS = "system:status"


# 全域實例
redis_manager = RedisManager()
```

#### 步驟 3：修改 WebSocket 連接管理器

**修改檔案**: `backend/main.py`

```python
from core.redis_manager import redis_manager, Channels

class ConnectionManager:
    """WebSocket 連接管理器（支持多實例）"""

    def __init__(self):
        self.local_connections: List[WebSocket] = []
        self.instance_id = str(uuid.uuid4())[:8]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.local_connections.append(websocket)
        logger.info(f"[{self.instance_id}] 新連接，本地連接數: {len(self.local_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.local_connections:
            self.local_connections.remove(websocket)

    async def broadcast_local(self, message: Dict):
        """廣播到本地連接"""
        for connection in self.local_connections[:]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

    async def broadcast_global(self, channel: str, message: Dict):
        """通過 Redis 廣播到所有實例"""
        await redis_manager.publish(channel, {
            "instance_id": self.instance_id,
            "message": message
        })

    async def handle_redis_message(self, data: Dict):
        """處理 Redis 消息"""
        # 避免處理自己發出的消息
        if data.get("instance_id") == self.instance_id:
            return

        message = data.get("message", {})
        await self.broadcast_local(message)


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    # 連接 Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    await redis_manager.connect()

    # 訂閱 Redis 頻道
    await redis_manager.subscribe(
        Channels.KLINE_UPDATE,
        manager.handle_redis_message
    )
    await redis_manager.subscribe(
        Channels.TICKER_UPDATE,
        manager.handle_redis_message
    )

    # 啟動監聽器
    await redis_manager.start_listener()

    logger.info(f"實例 {manager.instance_id} 啟動完成")


@app.on_event("shutdown")
async def shutdown_event():
    await redis_manager.disconnect()
```

#### 步驟 4：修改數據推送邏輯

```python
# 在 OKX 數據回調中使用 Redis 廣播
def on_kline_update(kline: KlineData):
    message = {
        "type": "KLINE_UPDATE",
        "data": {
            "symbol": kline.symbol,
            "time": kline.timestamp // 1000,
            "open": kline.open,
            "high": kline.high,
            "low": kline.low,
            "close": kline.close,
            "volume": kline.volume,
            "timeframe": kline.timeframe
        }
    }

    # 通過 Redis 廣播到所有實例
    asyncio.create_task(
        redis_manager.publish(Channels.KLINE_UPDATE, message)
    )

    # 同時本地廣播（減少延遲）
    asyncio.create_task(manager.broadcast_local(message))
```

### 架構圖

```
┌─────────────────┐     ┌─────────────────┐
│  Backend #1     │     │  Backend #2     │
│  ┌───────────┐  │     │  ┌───────────┐  │
│  │WebSocket  │  │     │  │WebSocket  │  │
│  │Manager    │  │     │  │Manager    │  │
│  └─────┬─────┘  │     │  └─────┬─────┘  │
└────────┼────────┘     └────────┼────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────┴──────┐
              │    Redis    │
              │  Pub/Sub    │
              └─────────────┘
```

---

## P2: TanStack Query 數據緩存

### 問題分析

當前每次都重新請求歷史數據，沒有緩存：

```typescript
// Dashboard.tsx:45
const loadHistoricalData = async (timeframe: string) => {
    const response = await fetch(`${backendUrl}/api/historical?...`);
    // 沒有緩存，每次都重新請求
};
```

### 實作步驟

#### 步驟 1：安裝依賴

```bash
cd frontend
npm install @tanstack/react-query
```

#### 步驟 2：設置 QueryClient

**新增檔案**: `frontend/src/lib/queryClient.ts`

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 分鐘內數據視為新鮮
      gcTime: 1000 * 60 * 5, // 5 分鐘後垃圾回收
      refetchOnWindowFocus: false,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});
```

#### 步驟 3：建立 API Hooks

**新增檔案**: `frontend/src/hooks/useApi.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8000';

// 類型定義
interface Kline {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface HistoricalDataResponse {
  success: boolean;
  data: Kline[];
  symbol: string;
  timeframe: string;
  count: number;
}

interface PriceData {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  change_24h: number;
  change_percent_24h: number;
}

// API 函數
const api = {
  async getHistoricalData(
    symbol: string,
    timeframe: string,
    limit: number = 100
  ): Promise<HistoricalDataResponse> {
    const params = new URLSearchParams({
      symbol,
      timeframe,
      limit: limit.toString(),
    });

    const response = await fetch(`${API_BASE}/api/historical?${params}`);
    if (!response.ok) {
      throw new Error('Failed to fetch historical data');
    }
    return response.json();
  },

  async getCurrentPrice(symbol: string): Promise<PriceData> {
    const response = await fetch(`${API_BASE}/api/price/${symbol}`);
    if (!response.ok) {
      throw new Error('Failed to fetch price');
    }
    const result = await response.json();
    return result.data;
  },

  async subscribe(symbols: string[], timeframe: string) {
    const response = await fetch(`${API_BASE}/api/subscribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols, timeframe }),
    });
    return response.json();
  },
};

// Query Keys
export const queryKeys = {
  historicalData: (symbol: string, timeframe: string) =>
    ['historicalData', symbol, timeframe] as const,
  currentPrice: (symbol: string) =>
    ['currentPrice', symbol] as const,
};

// Hooks
export function useHistoricalData(
  symbol: string,
  timeframe: string,
  limit: number = 100
) {
  return useQuery({
    queryKey: queryKeys.historicalData(symbol, timeframe),
    queryFn: () => api.getHistoricalData(symbol, timeframe, limit),
    select: (data) => data.data, // 只返回 K 線數據
    staleTime: 1000 * 30, // 30 秒
    refetchInterval: false, // WebSocket 會處理更新
  });
}

export function useCurrentPrice(symbol: string) {
  return useQuery({
    queryKey: queryKeys.currentPrice(symbol),
    queryFn: () => api.getCurrentPrice(symbol),
    staleTime: 1000 * 5, // 5 秒
    refetchInterval: 1000 * 10, // 每 10 秒刷新（備用）
  });
}

export function useSubscribe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ symbols, timeframe }: { symbols: string[]; timeframe: string }) =>
      api.subscribe(symbols, timeframe),
    onSuccess: (_, variables) => {
      // 訂閱成功後，使相關查詢失效
      queryClient.invalidateQueries({
        queryKey: ['historicalData', variables.symbols[0]],
      });
    },
  });
}

// 預取 Hook
export function usePrefetchHistoricalData() {
  const queryClient = useQueryClient();

  return (symbol: string, timeframe: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.historicalData(symbol, timeframe),
      queryFn: () => api.getHistoricalData(symbol, timeframe, 100),
      staleTime: 1000 * 30,
    });
  };
}
```

#### 步驟 4：修改 App 入口

**修改檔案**: `frontend/src/App.tsx`

```typescript
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './lib/queryClient';
import { Dashboard } from './components/Dashboard';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
```

#### 步驟 5：修改 Dashboard 使用 TanStack Query

```typescript
import { useHistoricalData, usePrefetchHistoricalData } from '../hooks/useApi';

export const Dashboard: React.FC = () => {
  const { selectedTimeframe } = useTradingStore();

  // 使用 TanStack Query 獲取歷史數據
  const {
    data: historicalKlines,
    isLoading,
    error,
    refetch
  } = useHistoricalData('BTC/USDT', selectedTimeframe);

  // 預取其他時間框架的數據
  const prefetch = usePrefetchHistoricalData();

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];

  // 滑鼠懸停時預取
  const handleTimeframeHover = (tf: string) => {
    prefetch('BTC/USDT', tf);
  };

  // 合併歷史數據和實時數據
  const { klines: realtimeKlines } = useTradingStore();

  const displayKlines = useMemo(() => {
    if (!historicalKlines) return realtimeKlines;

    // 合併歷史和實時數據，去重
    const combined = [...historicalKlines];
    for (const kline of realtimeKlines) {
      const existingIndex = combined.findIndex(k => k.time === kline.time);
      if (existingIndex >= 0) {
        combined[existingIndex] = kline;
      } else {
        combined.push(kline);
      }
    }
    return combined.sort((a, b) => a.time - b.time);
  }, [historicalKlines, realtimeKlines]);

  return (
    // ...
    <div className="flex gap-1">
      {timeframes.map((tf) => (
        <button
          key={tf}
          onMouseEnter={() => handleTimeframeHover(tf)}
          // ...
        >
          {tf}
        </button>
      ))}
    </div>
    // ...
  );
};
```

### 功能對比

| 功能 | 現狀 | TanStack Query |
|------|-----|----------------|
| 緩存 | 無 | 自動緩存 |
| 去重 | 手動 | 自動 |
| 重試 | 無 | 自動重試 |
| 預取 | 無 | 支持 |
| 開發工具 | 無 | DevTools |
| 背景刷新 | 無 | 支持 |

---

## P2: 移除 Streamlit 整合到 React

### 問題分析

當前有兩套 UI：
1. React Dashboard (`frontend/`)
2. Streamlit Dashboard (`trading-bot/web/`)

**問題**：
- 維護兩套代碼
- 功能重疊
- 用戶體驗不一致
- 資源浪費

### 整合計畫

#### 階段 1：功能對照

| Streamlit 功能 | React 對應 | 狀態 |
|---------------|-----------|------|
| K 線圖表 | Chart.tsx | ✅ 已有 |
| 技術指標 (RSI/MACD) | 需新增 | ⏳ 待實現 |
| 策略控制 | Dashboard.tsx | ✅ 已有 |
| 持倉顯示 | 需新增 | ⏳ 待實現 |
| 交易歷史 | 需新增 | ⏳ 待實現 |
| 風險管理設置 | 需新增 | ⏳ 待實現 |
| API 配置 | 需新增 | ⏳ 待實現 |

#### 階段 2：新增組件

**新增檔案**: `frontend/src/components/TechnicalIndicators.tsx`

```typescript
import React, { useMemo } from 'react';
import { createChart, ColorType, LineSeries, HistogramSeries } from 'lightweight-charts';

interface IndicatorProps {
  data: { time: number; close: number }[];
  type: 'RSI' | 'MACD';
}

// RSI 計算
function calculateRSI(data: number[], period: number = 14): number[] {
  const rsi: number[] = [];
  let gains = 0;
  let losses = 0;

  for (let i = 1; i < data.length; i++) {
    const change = data[i] - data[i - 1];

    if (i <= period) {
      if (change > 0) gains += change;
      else losses -= change;

      if (i === period) {
        const avgGain = gains / period;
        const avgLoss = losses / period;
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        rsi.push(100 - (100 / (1 + rs)));
      }
    } else {
      const avgGain = gains / period;
      const avgLoss = losses / period;

      if (change > 0) {
        gains = (avgGain * (period - 1) + change);
        losses = avgLoss * (period - 1);
      } else {
        gains = avgGain * (period - 1);
        losses = (avgLoss * (period - 1) - change);
      }

      const rs = losses === 0 ? 100 : gains / losses;
      rsi.push(100 - (100 / (1 + rs)));
    }
  }

  return rsi;
}

// MACD 計算
function calculateMACD(
  data: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
) {
  const ema = (arr: number[], period: number): number[] => {
    const k = 2 / (period + 1);
    const result: number[] = [arr[0]];
    for (let i = 1; i < arr.length; i++) {
      result.push(arr[i] * k + result[i - 1] * (1 - k));
    }
    return result;
  };

  const fastEMA = ema(data, fastPeriod);
  const slowEMA = ema(data, slowPeriod);

  const macdLine = fastEMA.map((fast, i) => fast - slowEMA[i]);
  const signalLine = ema(macdLine.slice(slowPeriod - 1), signalPeriod);
  const histogram = macdLine.slice(slowPeriod - 1).map((macd, i) =>
    i < signalLine.length ? macd - signalLine[i] : 0
  );

  return { macdLine: macdLine.slice(slowPeriod - 1), signalLine, histogram };
}

export const RSIIndicator: React.FC<{ data: { time: number; close: number }[] }> = ({ data }) => {
  const chartContainerRef = React.useRef<HTMLDivElement>(null);

  const rsiData = useMemo(() => {
    const closes = data.map(d => d.close);
    const rsi = calculateRSI(closes);
    return data.slice(14).map((d, i) => ({
      time: d.time,
      value: rsi[i],
    }));
  }, [data]);

  React.useEffect(() => {
    if (!chartContainerRef.current || rsiData.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#d1d5db',
      },
      width: chartContainerRef.current.clientWidth,
      height: 150,
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
    });

    const series = chart.addSeries(LineSeries, {
      color: '#8b5cf6',
      lineWidth: 2,
    });

    series.setData(rsiData);

    // 超買超賣線
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [rsiData]);

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <h3 className="text-sm font-medium text-slate-300 mb-2">RSI (14)</h3>
      <div ref={chartContainerRef} className="w-full" />
      <div className="flex justify-between text-xs text-slate-400 mt-1">
        <span>超賣 &lt;30</span>
        <span>超買 &gt;70</span>
      </div>
    </div>
  );
};

export const MACDIndicator: React.FC<{ data: { time: number; close: number }[] }> = ({ data }) => {
  const chartContainerRef = React.useRef<HTMLDivElement>(null);

  const macdData = useMemo(() => {
    const closes = data.map(d => d.close);
    const { macdLine, signalLine, histogram } = calculateMACD(closes);
    const startIndex = 25; // 26 - 1

    return {
      macd: data.slice(startIndex).map((d, i) => ({
        time: d.time,
        value: macdLine[i] || 0,
      })),
      signal: data.slice(startIndex).map((d, i) => ({
        time: d.time,
        value: signalLine[i] || 0,
      })),
      histogram: data.slice(startIndex).map((d, i) => ({
        time: d.time,
        value: histogram[i] || 0,
        color: (histogram[i] || 0) >= 0 ? '#22c55e' : '#ef4444',
      })),
    };
  }, [data]);

  React.useEffect(() => {
    if (!chartContainerRef.current || macdData.macd.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#d1d5db',
      },
      width: chartContainerRef.current.clientWidth,
      height: 150,
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
    });

    // 柱狀圖
    const histogramSeries = chart.addSeries(HistogramSeries, {
      priceLineVisible: false,
    });
    histogramSeries.setData(macdData.histogram);

    // MACD 線
    const macdSeries = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 2,
    });
    macdSeries.setData(macdData.macd);

    // 信號線
    const signalSeries = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 2,
    });
    signalSeries.setData(macdData.signal);

    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [macdData]);

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <h3 className="text-sm font-medium text-slate-300 mb-2">MACD (12, 26, 9)</h3>
      <div ref={chartContainerRef} className="w-full" />
      <div className="flex gap-4 text-xs text-slate-400 mt-1">
        <span className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-blue-500" /> MACD
        </span>
        <span className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-amber-500" /> Signal
        </span>
      </div>
    </div>
  );
};
```

**新增檔案**: `frontend/src/components/PositionsTable.tsx`

```typescript
import React from 'react';
import clsx from 'clsx';

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  stopLoss?: number;
  takeProfit?: number;
}

interface PositionsTableProps {
  positions: Position[];
  onClose?: (id: string) => void;
}

export const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  onClose
}) => {
  if (positions.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        目前沒有持倉
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-400 border-b border-slate-700">
            <th className="text-left py-3 px-2">交易對</th>
            <th className="text-left py-3 px-2">方向</th>
            <th className="text-right py-3 px-2">數量</th>
            <th className="text-right py-3 px-2">進場價</th>
            <th className="text-right py-3 px-2">當前價</th>
            <th className="text-right py-3 px-2">未實現盈虧</th>
            <th className="text-right py-3 px-2">止損/止盈</th>
            <th className="text-center py-3 px-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr
              key={position.id}
              className="border-b border-slate-700/50 hover:bg-slate-700/30"
            >
              <td className="py-3 px-2 font-medium">{position.symbol}</td>
              <td className="py-3 px-2">
                <span className={clsx(
                  "px-2 py-0.5 rounded text-xs font-medium",
                  position.side === 'long'
                    ? "bg-green-500/20 text-green-400"
                    : "bg-red-500/20 text-red-400"
                )}>
                  {position.side === 'long' ? '多頭' : '空頭'}
                </span>
              </td>
              <td className="py-3 px-2 text-right">{position.size}</td>
              <td className="py-3 px-2 text-right">
                ${position.entryPrice.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right">
                ${position.currentPrice.toLocaleString()}
              </td>
              <td className={clsx(
                "py-3 px-2 text-right font-medium",
                position.unrealizedPnl >= 0 ? "text-green-400" : "text-red-400"
              )}>
                {position.unrealizedPnl >= 0 ? '+' : ''}
                ${position.unrealizedPnl.toFixed(2)}
                <span className="text-xs ml-1">
                  ({position.unrealizedPnlPercent >= 0 ? '+' : ''}
                  {position.unrealizedPnlPercent.toFixed(2)}%)
                </span>
              </td>
              <td className="py-3 px-2 text-right text-xs text-slate-400">
                {position.stopLoss && (
                  <div>SL: ${position.stopLoss.toLocaleString()}</div>
                )}
                {position.takeProfit && (
                  <div>TP: ${position.takeProfit.toLocaleString()}</div>
                )}
              </td>
              <td className="py-3 px-2 text-center">
                <button
                  onClick={() => onClose?.(position.id)}
                  className="px-3 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 text-xs"
                >
                  平倉
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

**新增檔案**: `frontend/src/components/TradeHistory.tsx`

```typescript
import React from 'react';
import clsx from 'clsx';

interface Trade {
  id: string;
  time: Date;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPercent: number;
  fee: number;
}

interface TradeHistoryProps {
  trades: Trade[];
}

export const TradeHistory: React.FC<TradeHistoryProps> = ({ trades }) => {
  const stats = React.useMemo(() => {
    if (trades.length === 0) return null;

    const wins = trades.filter(t => t.pnl > 0);
    const totalPnl = trades.reduce((sum, t) => sum + t.pnl, 0);
    const totalFees = trades.reduce((sum, t) => sum + t.fee, 0);

    return {
      totalTrades: trades.length,
      winRate: (wins.length / trades.length) * 100,
      totalPnl,
      totalFees,
      netPnl: totalPnl - totalFees,
      avgPnl: totalPnl / trades.length,
    };
  }, [trades]);

  return (
    <div className="space-y-4">
      {/* 統計卡片 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs">總交易</div>
            <div className="text-xl font-bold">{stats.totalTrades}</div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs">勝率</div>
            <div className="text-xl font-bold text-green-400">
              {stats.winRate.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs">總盈虧</div>
            <div className={clsx(
              "text-xl font-bold",
              stats.netPnl >= 0 ? "text-green-400" : "text-red-400"
            )}>
              {stats.netPnl >= 0 ? '+' : ''}${stats.netPnl.toFixed(2)}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs">平均盈虧</div>
            <div className={clsx(
              "text-xl font-bold",
              stats.avgPnl >= 0 ? "text-green-400" : "text-red-400"
            )}>
              {stats.avgPnl >= 0 ? '+' : ''}${stats.avgPnl.toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* 交易列表 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-3 px-2">時間</th>
              <th className="text-left py-3 px-2">交易對</th>
              <th className="text-left py-3 px-2">方向</th>
              <th className="text-right py-3 px-2">數量</th>
              <th className="text-right py-3 px-2">進場</th>
              <th className="text-right py-3 px-2">出場</th>
              <th className="text-right py-3 px-2">盈虧</th>
              <th className="text-right py-3 px-2">手續費</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr
                key={trade.id}
                className="border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                <td className="py-3 px-2 text-slate-400 text-xs">
                  {trade.time.toLocaleString()}
                </td>
                <td className="py-3 px-2">{trade.symbol}</td>
                <td className="py-3 px-2">
                  <span className={clsx(
                    "px-2 py-0.5 rounded text-xs",
                    trade.side === 'long'
                      ? "bg-green-500/20 text-green-400"
                      : "bg-red-500/20 text-red-400"
                  )}>
                    {trade.side === 'long' ? '多' : '空'}
                  </span>
                </td>
                <td className="py-3 px-2 text-right">{trade.size}</td>
                <td className="py-3 px-2 text-right">
                  ${trade.entryPrice.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right">
                  ${trade.exitPrice.toLocaleString()}
                </td>
                <td className={clsx(
                  "py-3 px-2 text-right font-medium",
                  trade.pnl >= 0 ? "text-green-400" : "text-red-400"
                )}>
                  {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                </td>
                <td className="py-3 px-2 text-right text-slate-400">
                  ${trade.fee.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

#### 階段 3：修改 Docker Compose

移除 Streamlit 服務：

```yaml
# docker-compose.yml
services:
  # 移除 web-ui 服務
  # web-ui:
  #   build:
  #     context: ./trading-bot
  #   ...

  # 保留其他服務
  frontend:
    # ...
```

#### 階段 4：更新的目錄結構

```
frontend/src/
├── components/
│   ├── Dashboard.tsx           # 主儀表板
│   ├── Chart.tsx               # K 線圖
│   ├── TechnicalIndicators.tsx # RSI/MACD
│   ├── PositionsTable.tsx      # 持倉表
│   ├── TradeHistory.tsx        # 交易歷史
│   ├── RiskSettings.tsx        # 風險設置
│   └── ApiConfig.tsx           # API 配置
├── hooks/
│   ├── useTrading.ts           # WebSocket
│   └── useApi.ts               # TanStack Query
├── store/
│   ├── tradingStore.ts         # 交易狀態
│   └── settingsStore.ts        # 設置狀態
└── lib/
    └── queryClient.ts          # Query Client
```

---

## P3: Kubernetes 部署配置

### 現狀分析

目前使用 Docker Compose，適合單機部署，但無法：
- 水平擴展
- 自動故障恢復
- 滾動更新
- 資源限制

### Kubernetes 架構設計

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Ingress   │  │   Ingress   │  │   Ingress   │              │
│  │   /         │  │   /api      │  │   /ws       │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐              │
│  │  Frontend   │  │   Backend   │  │   Backend   │              │
│  │  Service    │  │   Service   │  │  (WebSocket)│              │
│  │  (3 pods)   │  │  (3 pods)   │  │  (3 pods)   │              │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘              │
│                          │                │                      │
│                   ┌──────▼────────────────▼──────┐              │
│                   │         Redis Cluster         │              │
│                   │          (3 nodes)            │              │
│                   └───────────────────────────────┘              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Trading Bot (StatefulSet)                 │ │
│  │                         (1 pod)                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │  Prometheus  │  │   Grafana    │           │
│  │ (StatefulSet)│  │  (Deployment)│  │ (Deployment) │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Kubernetes 配置文件

#### 步驟 1：建立目錄結構

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── trading-bot/
│   │   └── statefulset.yaml
│   ├── redis/
│   │   └── statefulset.yaml
│   ├── postgres/
│   │   └── statefulset.yaml
│   └── ingress/
│       └── ingress.yaml
├── overlays/
│   ├── development/
│   │   └── kustomization.yaml
│   └── production/
│       └── kustomization.yaml
└── secrets/
    └── secrets.yaml.example
```

#### 步驟 2：Namespace

**檔案**: `k8s/base/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: autotrading
  labels:
    name: autotrading
```

#### 步驟 3：Frontend Deployment

**檔案**: `k8s/base/frontend/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: autotrading
  labels:
    app: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: autotrading/frontend:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
          livenessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: autotrading
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: autotrading
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

#### 步驟 4：Backend Deployment

**檔案**: `k8s/base/backend/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: autotrading
  labels:
    app: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: autotrading/backend:latest
          ports:
            - containerPort: 8000
          env:
            - name: REDIS_URL
              value: "redis://redis:6379"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: api-key
            - name: API_SECRET
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: api-secret
            - name: API_PASSPHRASE
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: passphrase
          resources:
            requests:
              memory: "256Mi"
              cpu: "200m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: autotrading
spec:
  selector:
    app: backend
  ports:
    - name: http
      port: 8000
      targetPort: 8000
    - name: ws
      port: 8001
      targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: autotrading
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

#### 步驟 5：Trading Bot StatefulSet

**檔案**: `k8s/base/trading-bot/statefulset.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: trading-bot
  namespace: autotrading
spec:
  serviceName: trading-bot
  replicas: 1  # 交易機器人應該只有一個實例
  selector:
    matchLabels:
      app: trading-bot
  template:
    metadata:
      labels:
        app: trading-bot
    spec:
      containers:
        - name: trading-bot
          image: autotrading/trading-bot:latest
          env:
            - name: REDIS_URL
              value: "redis://redis:6379"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: api-key
            - name: API_SECRET
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: api-secret
            - name: API_PASSPHRASE
              valueFrom:
                secretKeyRef:
                  name: okx-credentials
                  key: passphrase
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: logs
              mountPath: /app/logs
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
    - metadata:
        name: logs
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
```

#### 步驟 6：Redis StatefulSet

**檔案**: `k8s/base/redis/statefulset.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: autotrading
spec:
  serviceName: redis
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command:
            - redis-server
            - --appendonly
            - "yes"
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
          volumeMounts:
            - name: data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: autotrading
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
  clusterIP: None
```

#### 步驟 7：Ingress

**檔案**: `k8s/base/ingress/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: autotrading-ingress
  namespace: autotrading
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/websocket-services: "backend"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - trading.example.com
      secretName: trading-tls
  rules:
    - host: trading.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /ws
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
```

#### 步驟 8：Kustomization

**檔案**: `k8s/base/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: autotrading

resources:
  - namespace.yaml
  - frontend/deployment.yaml
  - backend/deployment.yaml
  - trading-bot/statefulset.yaml
  - redis/statefulset.yaml
  - ingress/ingress.yaml

commonLabels:
  app.kubernetes.io/name: autotrading
  app.kubernetes.io/managed-by: kustomize
```

**檔案**: `k8s/overlays/production/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: autotrading-prod

patchesStrategicMerge:
  - replica-patch.yaml
  - resource-patch.yaml

configMapGenerator:
  - name: app-config
    literals:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO

images:
  - name: autotrading/frontend
    newTag: v1.0.0
  - name: autotrading/backend
    newTag: v1.0.0
  - name: autotrading/trading-bot
    newTag: v1.0.0
```

### 部署命令

```bash
# 開發環境
kubectl apply -k k8s/overlays/development

# 生產環境
kubectl apply -k k8s/overlays/production

# 查看狀態
kubectl get all -n autotrading

# 查看日誌
kubectl logs -f deployment/backend -n autotrading

# 擴展副本
kubectl scale deployment/backend --replicas=5 -n autotrading
```

---

## 實施時間表

| 優先級 | 任務 | 預估工作量 |
|--------|------|-----------|
| **P0** | WebSocket 替代輪詢 | 1-2 天 |
| **P1** | Zustand 狀態管理 | 2-3 天 |
| **P1** | Redis Pub/Sub | 2-3 天 |
| **P2** | TanStack Query | 1-2 天 |
| **P2** | 移除 Streamlit | 3-5 天 |
| **P3** | Kubernetes 部署 | 3-5 天 |

**總計**：12-20 天

---

## 總結

這份優化計畫涵蓋了從前端到後端、從開發到部署的完整優化路徑。按照優先級實施，可以顯著提升系統的：

1. **效能**：WebSocket 替代輪詢，延遲從 2000ms 降至 <100ms
2. **可維護性**：Zustand 統一狀態管理，代碼更清晰
3. **可擴展性**：Redis Pub/Sub + Kubernetes 支持水平擴展
4. **用戶體驗**：TanStack Query 緩存，頁面載入更快
5. **運維效率**：Kubernetes 自動擴縮容、故障恢復

建議按 P0 → P1 → P2 → P3 順序實施，每完成一個階段進行測試驗證。
