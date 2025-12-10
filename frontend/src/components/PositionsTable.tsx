import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

export interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  leverage: number;
  marginMode: 'cross' | 'isolated';
  liquidationPrice: number;
  openTime: number;
}

interface PositionsTableProps {
  positions?: Position[];
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchPositions(): Promise<Position[]> {
  const response = await fetch(`${API_URL}/api/positions`);
  if (!response.ok) {
    throw new Error('Failed to fetch positions');
  }
  return response.json();
}

export function PositionsTable({ positions: propPositions }: PositionsTableProps) {
  // 使用 TanStack Query 獲取持倉數據（如果未透過 props 傳入）
  const { data: queryPositions, isLoading, error } = useQuery({
    queryKey: ['positions'],
    queryFn: fetchPositions,
    enabled: !propPositions,
    refetchInterval: 5000, // 每 5 秒刷新
    staleTime: 2000,
  });

  const positions = propPositions || queryPositions || [];

  // 計算總計
  const totals = useMemo(() => {
    return positions.reduce(
      (acc, pos) => ({
        totalPnl: acc.totalPnl + pos.unrealizedPnl,
        totalValue: acc.totalValue + pos.size * pos.currentPrice,
      }),
      { totalPnl: 0, totalValue: 0 }
    );
  }, [positions]);

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">持倉</h3>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">持倉</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-300">持倉</h3>
        <div className="flex gap-4 text-xs">
          <span className="text-slate-400">
            總市值: <span className="text-white font-mono">${totals.totalValue.toLocaleString()}</span>
          </span>
          <span className={totals.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}>
            總盈虧: {totals.totalPnl >= 0 ? '+' : ''}{totals.totalPnl.toFixed(2)} USD
          </span>
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-sm">
          暫無持倉
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-left border-b border-slate-700">
                <th className="pb-2 font-medium">交易對</th>
                <th className="pb-2 font-medium">方向</th>
                <th className="pb-2 font-medium text-right">數量</th>
                <th className="pb-2 font-medium text-right">開倉價</th>
                <th className="pb-2 font-medium text-right">現價</th>
                <th className="pb-2 font-medium text-right">未實現盈虧</th>
                <th className="pb-2 font-medium text-right">槓桿</th>
                <th className="pb-2 font-medium text-right">強平價</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {positions.map((position) => (
                <tr key={position.id} className="hover:bg-slate-700/50">
                  <td className="py-3 font-medium text-white">{position.symbol}</td>
                  <td className="py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        position.side === 'long'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {position.side === 'long' ? '做多' : '做空'}
                    </span>
                  </td>
                  <td className="py-3 text-right font-mono text-slate-300">
                    {position.size.toFixed(4)}
                  </td>
                  <td className="py-3 text-right font-mono text-slate-300">
                    ${position.entryPrice.toLocaleString()}
                  </td>
                  <td className="py-3 text-right font-mono text-white">
                    ${position.currentPrice.toLocaleString()}
                  </td>
                  <td className="py-3 text-right">
                    <div
                      className={`font-mono ${
                        position.unrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {position.unrealizedPnl >= 0 ? '+' : ''}
                      {position.unrealizedPnl.toFixed(2)}
                      <span className="text-xs ml-1">
                        ({position.unrealizedPnlPercent >= 0 ? '+' : ''}
                        {position.unrealizedPnlPercent.toFixed(2)}%)
                      </span>
                    </div>
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-amber-400 font-mono">{position.leverage}x</span>
                    <span className="text-slate-500 text-xs ml-1">
                      {position.marginMode === 'cross' ? '全倉' : '逐倉'}
                    </span>
                  </td>
                  <td className="py-3 text-right font-mono text-slate-400">
                    ${position.liquidationPrice.toLocaleString()}
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
