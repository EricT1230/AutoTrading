import { useEffect, useMemo } from 'react';
import { Chart } from './Chart';
import { Activity, Play, Square, RefreshCw, Database } from 'lucide-react';
import clsx from 'clsx';
import { useTradingStore } from '../store/tradingStore';
import { useTrading } from '../hooks/useTrading';
import { useHistoricalData, usePrefetchHistoricalData } from '../hooks/useApi';

// 可用的時間框架選項
const timeframes = [
  { value: '1m', label: '1分鐘' },
  { value: '5m', label: '5分鐘' },
  { value: '15m', label: '15分鐘' },
  { value: '1h', label: '1小時' },
  { value: '4h', label: '4小時' },
  { value: '1d', label: '1天' },
];

export const Dashboard: React.FC = () => {
  // 從 Zustand store 取得狀態
  const {
    klines: realtimeKlines,
    currentPrice,
    priceChange,
    connectionStatus,
    selectedTimeframe,
    status,
    logs,
    updateCount,
    lastUpdateTime,
    setSelectedTimeframe,
    setKlines,
    addLog,
  } = useTradingStore();

  // 使用 WebSocket hook
  const { subscribe, isConnected } = useTrading();

  // 使用 TanStack Query 獲取歷史數據（帶緩存）
  const {
    data: historicalKlines,
    isLoading,
    isFetching,
    refetch,
  } = useHistoricalData('BTC/USDT', selectedTimeframe, 100);

  // 預取其他時間框架的數據
  const prefetchData = usePrefetchHistoricalData();

  // 合併歷史數據和實時數據
  const displayKlines = useMemo(() => {
    // 如果有歷史數據，使用歷史數據為基礎
    if (historicalKlines && historicalKlines.length > 0) {
      // 如果沒有實時數據，直接返回歷史數據
      if (realtimeKlines.length === 0) {
        return historicalKlines;
      }

      // 合併：以歷史數據為主，實時數據更新最新的 K 線
      const combined = [...historicalKlines];
      const lastHistoricalTime = combined[combined.length - 1]?.time || 0;

      for (const kline of realtimeKlines) {
        if (kline.time > lastHistoricalTime) {
          // 新的 K 線
          combined.push(kline);
        } else if (kline.time === lastHistoricalTime) {
          // 更新最後一根 K 線
          combined[combined.length - 1] = kline;
        }
      }

      // 保持最多 100 根
      return combined.slice(-100);
    }

    // 沒有歷史數據，使用實時數據
    return realtimeKlines;
  }, [historicalKlines, realtimeKlines]);

  // 當歷史數據載入完成時，同步到 store
  useEffect(() => {
    if (historicalKlines && historicalKlines.length > 0) {
      setKlines(historicalKlines);
      addLog(`已載入 ${historicalKlines.length} 根 K 線數據 (緩存)`, 'success');
    }
  }, [historicalKlines, setKlines, addLog]);

  // WebSocket 連接成功後訂閱
  useEffect(() => {
    if (isConnected) {
      subscribe(['BTC/USDT'], selectedTimeframe);
    }
  }, [isConnected, selectedTimeframe, subscribe]);

  // 時間框架變更
  const handleTimeframeChange = (timeframe: string) => {
    if (timeframe === selectedTimeframe || isLoading) return;
    setSelectedTimeframe(timeframe);

    // 重新訂閱 WebSocket
    if (isConnected) {
      subscribe(['BTC/USDT'], timeframe);
    }
  };

  // 滑鼠懸停時預取數據
  const handleTimeframeHover = (timeframe: string) => {
    if (timeframe !== selectedTimeframe) {
      prefetchData('BTC/USDT', timeframe);
    }
  };

  // 手動刷新
  const handleRefresh = () => {
    if (isLoading || isFetching) return;
    refetch();
    addLog('手動刷新數據...', 'info');
  };

  const isLoadingData = isLoading || isFetching;

  return (
    <div className="min-h-screen bg-slate-900 p-6 text-slate-200 font-sans">
      {/* Header */}
      <header className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Activity className="w-6 h-6 text-blue-500" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            AutoTrading Bot <span className="text-blue-500">Pro</span>
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {/* 刷新按鈕 */}
          <button
            onClick={handleRefresh}
            disabled={isLoadingData}
            className={clsx(
              "p-2 rounded-lg transition-colors",
              isLoadingData
                ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            )}
            title="刷新數據"
          >
            <RefreshCw className={clsx("w-4 h-4", isLoadingData && "animate-spin")} />
          </button>

          {/* 連接狀態指示器 */}
          <div className={clsx(
            "flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium",
            connectionStatus === 'connected' ? "bg-green-500/10 text-green-500" :
            connectionStatus === 'connecting' ? "bg-yellow-500/10 text-yellow-500" :
            "bg-red-500/10 text-red-500"
          )}>
            <div className={clsx(
              "w-2 h-2 rounded-full",
              connectionStatus === 'connected' ? "bg-green-500 animate-pulse" :
              connectionStatus === 'connecting' ? "bg-yellow-500 animate-pulse" :
              "bg-red-500"
            )} />
            {connectionStatus === 'connected' ? 'WebSocket Connected' :
             connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Chart & Stats */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          {/* Chart Card */}
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">BTC/USDT</h2>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-slate-100">
                    ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className={clsx(
                    "text-sm px-2 py-1 rounded",
                    priceChange >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  )}>
                    {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(4)}%
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                {/* 時間框架選擇器（帶預取） */}
                <div className="flex gap-1">
                  {timeframes.map((tf) => (
                    <button
                      key={tf.value}
                      onClick={() => handleTimeframeChange(tf.value)}
                      onMouseEnter={() => handleTimeframeHover(tf.value)}
                      disabled={isLoadingData}
                      className={clsx(
                        "px-2 py-1 rounded text-xs font-medium transition-colors",
                        selectedTimeframe === tf.value
                          ? "bg-blue-500 text-white"
                          : "bg-slate-700 text-slate-300 hover:bg-slate-600",
                        isLoadingData && "opacity-50 cursor-not-allowed"
                      )}
                      title={tf.label}
                    >
                      {tf.value}
                    </button>
                  ))}
                </div>

                {/* 狀態指示器 */}
                <div className="flex gap-2 justify-end">
                  <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs flex items-center gap-1">
                    <Database className="w-3 h-3" />
                    Query Cache
                  </span>
                  {lastUpdateTime && (
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                      {lastUpdateTime.toLocaleTimeString()}
                    </span>
                  )}
                  {isLoadingData && (
                    <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs animate-pulse">
                      載入中...
                    </span>
                  )}
                </div>
              </div>
            </div>
            <Chart data={displayKlines} />
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
              <div className="text-slate-400 text-sm mb-1">當前價格</div>
              <div className="text-2xl font-bold text-green-500">
                ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
              <div className="text-slate-400 text-sm mb-1">實時更新</div>
              <div className="text-2xl font-bold text-blue-500">#{updateCount}</div>
              <div className="text-xs text-slate-500 mt-1">via WebSocket + Query</div>
            </div>
            <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
              <div className="text-slate-400 text-sm mb-1">系統狀態</div>
              <div className={clsx(
                "text-2xl font-bold",
                status.active ? 'text-green-500' : 'text-yellow-500'
              )}>
                {status.active ? '運行中' : '連接中'}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Controls & Logs */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Control Panel */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold mb-4">Strategy Control</h3>
            <div className="flex gap-3 mb-6">
              <button className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white py-2 rounded-lg transition-colors font-medium">
                <Play className="w-4 h-4" /> Start
              </button>
              <button className="flex-1 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-500 text-white py-2 rounded-lg transition-colors font-medium">
                <Square className="w-4 h-4" /> Stop
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Strategy</span>
                <span className="text-slate-200 font-medium">{status.strategy}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">時間框架</span>
                <span className="text-blue-500 font-medium">{selectedTimeframe}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">數據來源</span>
                <span className="text-green-400 font-medium">WebSocket + Cache</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Risk per Trade</span>
                <span className="text-slate-200 font-medium">1.0%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Status</span>
                <span className={clsx(
                  "font-medium",
                  status.active ? 'text-green-500' : 'text-yellow-500'
                )}>
                  {status.active ? 'Running' : 'Connecting'}
                </span>
              </div>
            </div>
          </div>

          {/* Activity Log */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700/50 h-[400px] flex flex-col">
            <h3 className="text-lg font-semibold mb-4">System Logs</h3>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
              {logs.map((log, i) => (
                <div key={i} className="flex gap-3 text-sm">
                  <span className="text-slate-500 font-mono text-xs mt-0.5 shrink-0">
                    {log.timestamp}
                  </span>
                  <span className={clsx(
                    log.type === 'info' && "text-slate-300",
                    log.type === 'success' && "text-green-400",
                    log.type === 'error' && "text-red-400",
                  )}>
                    {log.message}
                  </span>
                </div>
              ))}
              {logs.length === 0 && (
                <div className="text-slate-500 text-center py-8 italic">
                  Waiting for connection...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
