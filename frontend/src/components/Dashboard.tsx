import React, { useState, useEffect } from 'react';
import { Chart } from './Chart';
import { Activity, Play, Square } from 'lucide-react';
import clsx from 'clsx';

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

export const Dashboard: React.FC = () => {
    const [backendUrl] = useState('http://localhost:8003'); // 快速 OKX 後端
    const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

    const [klines, setKlines] = useState<Kline[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [status, setStatus] = useState({ active: false, strategy: 'ICT NY FVG' });
    const [currentPrice, setCurrentPrice] = useState<number>(0);
    const [priceChange] = useState<number>(0);
    const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
    const [updateCount, setUpdateCount] = useState<number>(0);
    const [selectedTimeframe, setSelectedTimeframe] = useState<string>('5m');
    const [isLoading, setIsLoading] = useState<boolean>(false);

    // 可用的時間框架選項
    const timeframes = [
        { value: '1m', label: '1分鐘', interval: 10 },
        { value: '5m', label: '5分鐘', interval: 15 },
        { value: '15m', label: '15分鐘', interval: 30 },
        { value: '1h', label: '1小時', interval: 60 },
        { value: '4h', label: '4小時', interval: 120 },
        { value: '1d', label: '1天', interval: 300 }
    ];

    // 載入歷史數據的函數
    const loadHistoricalData = async (timeframe: string = selectedTimeframe) => {
        try {
            setIsLoading(true);
            addLog(`載入 ${timeframe} K線數據...`, 'info');
            
            const response = await fetch(`${backendUrl}/api/historical?symbol=BTC/USDT&timeframe=${timeframe}&limit=100`);
            const data = await response.json();
            
            if (data.success && data.data) {
                const formattedKlines = data.data.map((item: any) => ({
                    time: item.time,
                    open: item.open,
                    high: item.high,
                    low: item.low,
                    close: item.close,
                }));
                
                setKlines(formattedKlines);
                setCurrentPrice(formattedKlines[formattedKlines.length - 1]?.close || 0);
                addLog(`成功載入 ${data.count} 根 ${timeframe} K線數據`, 'success');
                setConnectionStatus('connected');
            } else {
                addLog('載入歷史數據失敗', 'error');
                setConnectionStatus('disconnected');
            }
        } catch (error) {
            addLog(`載入歷史數據錯誤: ${error}`, 'error');
            setConnectionStatus('disconnected');
        } finally {
            setIsLoading(false);
        }
    };

    // 時間框架切換處理
    const handleTimeframeChange = async (timeframe: string) => {
        if (timeframe === selectedTimeframe || isLoading) return;
        
        setSelectedTimeframe(timeframe);
        addLog(`切換到 ${timeframe} 時間框架`, 'info');
        
        // 重新載入數據
        await loadHistoricalData(timeframe);
        
        // 重新訂閱實時數據
        try {
            const response = await fetch(`${backendUrl}/api/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbols: ['BTC/USDT'],
                    timeframe: timeframe
                }),
            });
            
            const result = await response.json();
            if (result.success) {
                addLog(`已切換到 ${timeframe} 實時數據 (每${result.update_interval_seconds}秒更新)`, 'success');
            }
        } catch (error) {
            addLog(`切換實時數據失敗: ${error}`, 'error');
        }
    };

    // 初始化和實時數據更新
    useEffect(() => {
        const initializeData = async () => {
            // 載入初始歷史數據
            await loadHistoricalData(selectedTimeframe);
            
            // 訂閱實時數據
            try {
                const response = await fetch(`${backendUrl}/api/subscribe`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        symbols: ['BTC/USDT'],
                        timeframe: selectedTimeframe
                    }),
                });
                
                const result = await response.json();
                if (result.success) {
                    addLog(`已訂閱 ${selectedTimeframe} 快速數據 (每${result.update_interval_seconds}秒)`, 'success');
                    setStatus({ active: true, strategy: 'ICT NY FVG' });
                    setConnectionStatus('connected');
                }
            } catch (error) {
                addLog(`訂閱實時數據失敗: ${error}`, 'error');
                setConnectionStatus('disconnected');
            }
        };

        initializeData();

        // 快速輪詢機制 - 每2秒檢查
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`${backendUrl}/api/latest`);
                const data = await response.json();
                
                if (data.success) {
                    setConnectionStatus('connected');
                    
                    if (data.data && Object.keys(data.data).length > 0) {
                        // 處理最新的K線數據
                        Object.values(data.data).forEach((klineData: any) => {
                            if (klineData.symbol === 'BTC/USDT' && klineData.timeframe === selectedTimeframe) {
                                const newKline = {
                                    time: klineData.time,
                                    open: klineData.open,
                                    high: klineData.high,
                                    low: klineData.low,
                                    close: klineData.close,
                                };

                                setKlines(prev => {
                                    if (prev.length === 0) return [newKline];
                                    const last = prev[prev.length - 1];
                                    
                                    if (newKline.time > last.time) {
                                        return [...prev.slice(-99), newKline];
                                    } else if (newKline.time === last.time) {
                                        return [...prev.slice(0, -1), newKline];
                                    }
                                    return prev;
                                });

                                setCurrentPrice(klineData.close);
                                setLastUpdateTime(new Date());
                                setUpdateCount(prev => prev + 1);
                            }
                        });
                        
                        if (data.system_status) {
                            const systemStatus = data.system_status;
                            if (systemStatus.running) {
                                setStatus({ active: true, strategy: 'ICT NY FVG' });
                            }
                        }
                    }
                } else {
                    setConnectionStatus('disconnected');
                }
            } catch (error) {
                console.error('輪詢更新失敗:', error);
                setConnectionStatus('disconnected');
            }
        }, 2000); // 每2秒快速檢查

        return () => clearInterval(interval);
    }, [backendUrl, selectedTimeframe]);

    const addLog = (message: string, type: 'info' | 'error' | 'success') => {
        setLogs(prev => [{ timestamp: new Date().toLocaleTimeString(), message, type }, ...prev.slice(0, 49)]);
    };

    return (
        <div className="min-h-screen bg-slate-900 p-6 text-slate-200 font-sans">
            {/* Header */}
            <header className="flex justify-between items-center mb-8">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                        <Activity className="w-6 h-6 text-blue-500" />
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">AutoTrading Bot <span className="text-blue-500">Pro</span></h1>
                </div>

                <div className="flex items-center gap-4">
                    <div className={clsx("flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium",
                        connectionStatus === 'connected' ? "bg-green-500/10 text-green-500" : 
                        connectionStatus === 'connecting' ? "bg-yellow-500/10 text-yellow-500" :
                        "bg-red-500/10 text-red-500"
                    )}>
                        <div className={clsx("w-2 h-2 rounded-full", 
                            connectionStatus === 'connected' ? "bg-green-500" : 
                            connectionStatus === 'connecting' ? "bg-yellow-500" :
                            "bg-red-500"
                        )} />
                        {connectionStatus === 'connected' ? 'Connected' : 
                         connectionStatus === 'connecting' ? 'Connecting' : 'Disconnected'}
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
                                    <span className="text-2xl font-bold text-slate-100">${currentPrice.toLocaleString()}</span>
                                    <span className={`text-sm px-2 py-1 rounded ${
                                        priceChange >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                                    }`}>
                                        {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                            <div className="flex flex-col gap-2">
                                {/* 時間框架選擇器 */}
                                <div className="flex gap-1">
                                    {timeframes.map((tf) => (
                                        <button
                                            key={tf.value}
                                            onClick={() => handleTimeframeChange(tf.value)}
                                            disabled={isLoading}
                                            className={clsx(
                                                "px-2 py-1 rounded text-xs font-medium transition-colors",
                                                selectedTimeframe === tf.value
                                                    ? "bg-blue-500 text-white"
                                                    : "bg-slate-700 text-slate-300 hover:bg-slate-600",
                                                isLoading && "opacity-50 cursor-not-allowed"
                                            )}
                                            title={`${tf.label} - 每${tf.interval}秒更新`}
                                        >
                                            {tf.value}
                                        </button>
                                    ))}
                                </div>
                                {/* 狀態指示器 */}
                                <div className="flex gap-2 justify-end">
                                    <span className="px-2 py-1 bg-blue-500/20 text-blue-500 rounded text-xs">
                                        快速模式
                                    </span>
                                    {lastUpdateTime && (
                                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                                            {lastUpdateTime.toLocaleTimeString()}
                                        </span>
                                    )}
                                    {isLoading && (
                                        <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                                            載入中...
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <Chart data={klines} />
                    </div>

                    {/* Quick Stats */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
                            <div className="text-slate-400 text-sm mb-1">當前價格</div>
                            <div className="text-2xl font-bold text-green-500">${currentPrice.toLocaleString()}</div>
                        </div>
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
                            <div className="text-slate-400 text-sm mb-1">數據更新</div>
                            <div className="text-2xl font-bold text-blue-500">#{updateCount}</div>
                        </div>
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700/50">
                            <div className="text-slate-400 text-sm mb-1">系統狀態</div>
                            <div className={`text-2xl font-bold ${status.active ? 'text-green-500' : 'text-yellow-500'}`}>
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
                                <span className="text-slate-200 font-medium">ICT NY FVG</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">時間框架</span>
                                <span className="text-blue-500 font-medium">{selectedTimeframe}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">更新頻率</span>
                                <span className="text-green-400 font-medium">
                                    每{timeframes.find(tf => tf.value === selectedTimeframe)?.interval || 15}秒
                                </span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">Risk per Trade</span>
                                <span className="text-slate-200 font-medium">1.0%</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">Status</span>
                                <span className={`font-medium ${status.active ? 'text-green-500' : 'text-yellow-500'}`}>
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
                                    <span className="text-slate-500 font-mono text-xs mt-0.5">{log.timestamp}</span>
                                    <span className={clsx(
                                        log.type === 'info' && "text-slate-300",
                                        log.type === 'success' && "text-green-400",
                                        log.type === 'error' && "text-red-400",
                                    )}>{log.message}</span>
                                </div>
                            ))}
                            {logs.length === 0 && (
                                <div className="text-slate-500 text-center py-8 italic">No activity yet...</div>
                            )}
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};