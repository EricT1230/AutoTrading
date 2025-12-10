import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// 類型定義
export interface Kline {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LogEntry {
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
      immer((set) => ({
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
