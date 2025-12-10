import { useCallback, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useTradingStore } from '../store/tradingStore';
import type { Kline } from '../store/tradingStore';

// WebSocket URL - 可透過環境變數配置
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface KlineMessage {
  type: 'KLINE_UPDATE' | 'TICKER_UPDATE' | 'CONNECTION_SUCCESS' | 'SUBSCRIBED' | 'pong';
  data?: {
    symbol?: string;
    time?: number;
    timestamp?: number;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
    timeframe?: string;
    price?: number;
    message?: string;
    symbols?: string[];
  };
}

export const useTrading = () => {
  const {
    updateKline,
    setKlines,
    setConnectionStatus,
    setCurrentPrice,
    setIsLoading,
    setStatus,
    addLog,
    selectedTimeframe,
  } = useTradingStore();

  const didUnmount = useRef(false);
  const reconnectCount = useRef(0);

  const {
    sendJsonMessage,
    lastJsonMessage,
    readyState,
  } = useWebSocket(WS_URL, {
    shouldReconnect: () => {
      if (didUnmount.current) return false;
      reconnectCount.current += 1;
      addLog(`嘗試重新連接... (${reconnectCount.current})`, 'info');
      return true;
    },
    reconnectAttempts: 10,
    reconnectInterval: (attemptNumber) =>
      Math.min(Math.pow(2, attemptNumber) * 1000, 30000),
    onOpen: () => {
      reconnectCount.current = 0;
      addLog('WebSocket 連接已建立', 'success');
    },
    onClose: () => {
      addLog('WebSocket 連接已關閉', 'info');
    },
    onError: (event) => {
      console.error('WebSocket error:', event);
      addLog('WebSocket 連接錯誤', 'error');
    },
    heartbeat: {
      message: JSON.stringify({ type: 'ping' }),
      interval: 30000,
      timeout: 60000,
    },
  });

  // 處理連接狀態變化
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

  // 處理接收到的 WebSocket 消息
  useEffect(() => {
    if (!lastJsonMessage) return;

    const message = lastJsonMessage as KlineMessage;

    switch (message.type) {
      case 'KLINE_UPDATE':
        if (message.data) {
          const kline: Kline = {
            time: message.data.time || Math.floor((message.data.timestamp || 0) / 1000),
            open: message.data.open || 0,
            high: message.data.high || 0,
            low: message.data.low || 0,
            close: message.data.close || 0,
          };
          updateKline(kline);
        }
        break;

      case 'TICKER_UPDATE':
        if (message.data?.price) {
          setCurrentPrice(message.data.price);
        }
        break;

      case 'CONNECTION_SUCCESS':
        addLog('已成功連接到交易伺服器', 'success');
        setStatus({ active: true, strategy: 'ICT NY FVG' });
        break;

      case 'SUBSCRIBED':
        if (message.data?.symbols) {
          addLog(`已訂閱: ${message.data.symbols.join(', ')}`, 'success');
        }
        break;

      case 'pong':
        // 心跳回應，不需要處理
        break;

      default:
        console.log('Unknown message type:', message);
    }
  }, [lastJsonMessage, updateKline, setCurrentPrice, addLog, setStatus]);

  // 載入歷史數據
  const loadHistoricalData = useCallback(async (
    symbol: string = 'BTC/USDT',
    timeframe: string = selectedTimeframe,
    limit: number = 100
  ) => {
    setIsLoading(true);
    addLog(`載入 ${timeframe} K線數據...`, 'info');

    try {
      const params = new URLSearchParams({
        symbol,
        timeframe,
        limit: limit.toString(),
      });

      const response = await fetch(`${API_URL}/api/historical?${params}`);
      const data = await response.json();

      if (data.success && data.data) {
        const formattedKlines: Kline[] = data.data.map((item: { time: number; open: number; high: number; low: number; close: number }) => ({
          time: item.time,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
        }));

        setKlines(formattedKlines);
        addLog(`成功載入 ${data.count} 根 ${timeframe} K線數據`, 'success');
        return true;
      } else {
        addLog('載入歷史數據失敗', 'error');
        return false;
      }
    } catch (error) {
      addLog(`載入歷史數據錯誤: ${error}`, 'error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [selectedTimeframe, setKlines, setIsLoading, addLog]);

  // 訂閱交易對
  const subscribe = useCallback((symbols: string[], timeframe: string) => {
    if (readyState !== ReadyState.OPEN) {
      addLog('WebSocket 未連接，無法訂閱', 'error');
      return;
    }

    sendJsonMessage({
      type: 'subscribe',
      symbols,
      timeframe,
    });

    addLog(`正在訂閱 ${symbols.join(', ')} (${timeframe})...`, 'info');
  }, [readyState, sendJsonMessage, addLog]);

  // 取消訂閱
  const unsubscribe = useCallback(() => {
    if (readyState !== ReadyState.OPEN) return;

    sendJsonMessage({
      type: 'unsubscribe',
    });

    addLog('已取消訂閱', 'info');
  }, [readyState, sendJsonMessage, addLog]);

  // 清理
  useEffect(() => {
    return () => {
      didUnmount.current = true;
    };
  }, []);

  return {
    // 方法
    subscribe,
    unsubscribe,
    loadHistoricalData,
    // 狀態
    isConnected: readyState === ReadyState.OPEN,
    isConnecting: readyState === ReadyState.CONNECTING,
  };
};
