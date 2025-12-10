import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Kline } from '../store/tradingStore';

// API URL - 可透過環境變數配置
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API 回應類型
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
  bid: number | null;
  ask: number | null;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  change_24h: number;
  change_percent_24h: number;
  timestamp: number;
}

interface PriceResponse {
  success: boolean;
  data: PriceData;
}

interface HealthResponse {
  status: string;
  okx_api: string;
  redis: string;
  instance_id: string;
  active_connections: number;
  subscriptions: {
    symbols: string[];
    timeframe: string;
  };
  timestamp: string;
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

    const response = await fetch(`${API_URL}/api/historical?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch historical data: ${response.statusText}`);
    }
    return response.json();
  },

  async getCurrentPrice(symbol: string): Promise<PriceResponse> {
    const formattedSymbol = symbol.replace('/', '-');
    const response = await fetch(`${API_URL}/api/price/${formattedSymbol}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch price: ${response.statusText}`);
    }
    return response.json();
  },

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_URL}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    return response.json();
  },

  async subscribe(symbols: string[], timeframe: string) {
    const response = await fetch(`${API_URL}/api/subscribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols, timeframe }),
    });
    if (!response.ok) {
      throw new Error(`Failed to subscribe: ${response.statusText}`);
    }
    return response.json();
  },
};

// Query Keys - 用於緩存識別
export const queryKeys = {
  historicalData: (symbol: string, timeframe: string) =>
    ['historicalData', symbol, timeframe] as const,
  currentPrice: (symbol: string) =>
    ['currentPrice', symbol] as const,
  health: () => ['health'] as const,
};

/**
 * 獲取歷史 K 線數據
 */
export function useHistoricalData(
  symbol: string,
  timeframe: string,
  limit: number = 100,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: queryKeys.historicalData(symbol, timeframe),
    queryFn: () => api.getHistoricalData(symbol, timeframe, limit),
    select: (data) => data.data, // 只返回 K 線數據陣列
    staleTime: getStaleTime(timeframe), // 根據時間框架設置不同的過期時間
    enabled,
  });
}

/**
 * 獲取當前價格
 */
export function useCurrentPrice(symbol: string, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.currentPrice(symbol),
    queryFn: () => api.getCurrentPrice(symbol),
    select: (data) => data.data,
    staleTime: 1000 * 5, // 5 秒
    refetchInterval: 1000 * 30, // 每 30 秒自動刷新（備用，WebSocket 會更快）
    enabled,
  });
}

/**
 * 健康檢查
 */
export function useHealth(enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: api.getHealth,
    staleTime: 1000 * 10, // 10 秒
    refetchInterval: 1000 * 30, // 每 30 秒檢查
    enabled,
  });
}

/**
 * 預取歷史數據 Hook
 */
export function usePrefetchHistoricalData() {
  const queryClient = useQueryClient();

  return (symbol: string, timeframe: string, limit: number = 100) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.historicalData(symbol, timeframe),
      queryFn: () => api.getHistoricalData(symbol, timeframe, limit),
      staleTime: getStaleTime(timeframe),
    });
  };
}

/**
 * 使緩存失效 Hook
 */
export function useInvalidateHistoricalData() {
  const queryClient = useQueryClient();

  return (symbol?: string, timeframe?: string) => {
    if (symbol && timeframe) {
      queryClient.invalidateQueries({
        queryKey: queryKeys.historicalData(symbol, timeframe),
      });
    } else {
      queryClient.invalidateQueries({
        queryKey: ['historicalData'],
      });
    }
  };
}

/**
 * 手動更新緩存中的 K 線數據
 */
export function useUpdateKlineCache() {
  const queryClient = useQueryClient();

  return (symbol: string, timeframe: string, newKline: Kline) => {
    queryClient.setQueryData<Kline[]>(
      queryKeys.historicalData(symbol, timeframe),
      (oldData) => {
        if (!oldData) return [newKline];

        const lastIndex = oldData.length - 1;
        if (lastIndex < 0) return [newKline];

        // 如果是新的 K 線
        if (newKline.time > oldData[lastIndex].time) {
          return [...oldData.slice(-99), newKline];
        }
        // 如果是更新當前 K 線
        if (newKline.time === oldData[lastIndex].time) {
          return [...oldData.slice(0, -1), newKline];
        }

        return oldData;
      }
    );
  };
}

// 輔助函數：根據時間框架獲取過期時間
function getStaleTime(timeframe: string): number {
  const staleTimeMap: Record<string, number> = {
    '1m': 1000 * 30,    // 30 秒
    '5m': 1000 * 60,    // 1 分鐘
    '15m': 1000 * 120,  // 2 分鐘
    '1h': 1000 * 300,   // 5 分鐘
    '4h': 1000 * 600,   // 10 分鐘
    '1d': 1000 * 1800,  // 30 分鐘
  };
  return staleTimeMap[timeframe] || 1000 * 60;
}

// 導出 API 函數供直接使用
export { api };
