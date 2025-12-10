import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop';
  price: number;
  size: number;
  fee: number;
  feeCurrency: string;
  pnl?: number;
  pnlPercent?: number;
  timestamp: number;
  orderId: string;
}

interface TradeHistoryProps {
  trades?: Trade[];
  limit?: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchTrades(limit: number): Promise<Trade[]> {
  const response = await fetch(`${API_URL}/api/trades?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to fetch trades');
  }
  return response.json();
}

export function TradeHistory({ trades: propTrades, limit = 50 }: TradeHistoryProps) {
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell'>('all');

  const { data: queryTrades, isLoading, error } = useQuery({
    queryKey: ['trades', limit],
    queryFn: () => fetchTrades(limit),
    enabled: !propTrades,
    staleTime: 10000,
  });

  const trades = propTrades || queryTrades || [];

  // 過濾交易
  const filteredTrades = useMemo(() => {
    if (filter === 'all') return trades;
    return trades.filter((t) => t.side === filter);
  }, [trades, filter]);

  // 統計數據
  const stats = useMemo(() => {
    const buyTrades = trades.filter((t) => t.side === 'buy');
    const sellTrades = trades.filter((t) => t.side === 'sell');
    const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalFees = trades.reduce((sum, t) => sum + t.fee, 0);
    const winTrades = trades.filter((t) => (t.pnl || 0) > 0);
    const lossTrades = trades.filter((t) => (t.pnl || 0) < 0);

    return {
      totalTrades: trades.length,
      buyCount: buyTrades.length,
      sellCount: sellTrades.length,
      totalPnl,
      totalFees,
      winRate: trades.length > 0 ? (winTrades.length / trades.length) * 100 : 0,
      avgWin: winTrades.length > 0
        ? winTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / winTrades.length
        : 0,
      avgLoss: lossTrades.length > 0
        ? lossTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / lossTrades.length
        : 0,
    };
  }, [trades]);

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">交易歷史</h3>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">交易歷史</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* 標題和統計 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <h3 className="text-sm font-medium text-slate-300">交易歷史</h3>

        {/* 統計卡片 */}
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1">
            <span className="text-slate-400">總筆數:</span>
            <span className="text-white font-mono">{stats.totalTrades}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-slate-400">勝率:</span>
            <span className={`font-mono ${stats.winRate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.winRate.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-slate-400">總盈虧:</span>
            <span className={`font-mono ${stats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.totalPnl >= 0 ? '+' : ''}{stats.totalPnl.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-slate-400">手續費:</span>
            <span className="text-amber-400 font-mono">-{stats.totalFees.toFixed(4)}</span>
          </div>
        </div>
      </div>

      {/* 過濾按鈕 */}
      <div className="flex gap-2 mb-4">
        {(['all', 'buy', 'sell'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            {f === 'all' ? '全部' : f === 'buy' ? '買入' : '賣出'}
            {f !== 'all' && (
              <span className="ml-1 text-slate-500">
                ({f === 'buy' ? stats.buyCount : stats.sellCount})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 交易列表 */}
      {filteredTrades.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-sm">暫無交易記錄</div>
      ) : (
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-800">
              <tr className="text-slate-400 text-left border-b border-slate-700">
                <th className="pb-2 font-medium">時間</th>
                <th className="pb-2 font-medium">交易對</th>
                <th className="pb-2 font-medium">方向</th>
                <th className="pb-2 font-medium">類型</th>
                <th className="pb-2 font-medium text-right">價格</th>
                <th className="pb-2 font-medium text-right">數量</th>
                <th className="pb-2 font-medium text-right">手續費</th>
                <th className="pb-2 font-medium text-right">盈虧</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {filteredTrades.map((trade) => (
                <tr key={trade.id} className="hover:bg-slate-700/30">
                  <td className="py-2 text-slate-400 font-mono text-xs">
                    {new Date(trade.timestamp).toLocaleString('zh-TW', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </td>
                  <td className="py-2 font-medium text-white">{trade.symbol}</td>
                  <td className="py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        trade.side === 'buy'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {trade.side === 'buy' ? '買入' : '賣出'}
                    </span>
                  </td>
                  <td className="py-2 text-slate-400 text-xs uppercase">{trade.type}</td>
                  <td className="py-2 text-right font-mono text-slate-300">
                    ${trade.price.toLocaleString()}
                  </td>
                  <td className="py-2 text-right font-mono text-slate-300">
                    {trade.size.toFixed(4)}
                  </td>
                  <td className="py-2 text-right font-mono text-amber-400 text-xs">
                    -{trade.fee.toFixed(6)} {trade.feeCurrency}
                  </td>
                  <td className="py-2 text-right">
                    {trade.pnl !== undefined ? (
                      <span
                        className={`font-mono ${
                          trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {trade.pnl >= 0 ? '+' : ''}
                        {trade.pnl.toFixed(2)}
                        {trade.pnlPercent !== undefined && (
                          <span className="text-xs ml-1">
                            ({trade.pnlPercent >= 0 ? '+' : ''}
                            {trade.pnlPercent.toFixed(2)}%)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
