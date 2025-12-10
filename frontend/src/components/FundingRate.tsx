import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Clock, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

export interface FundingRateData {
  symbol: string;
  fundingRate: number; // 當前費率
  predictedRate: number; // 預測費率
  fundingTime: number; // 下次結算時間 (timestamp)
  markPrice: number;
  indexPrice: number;
}

interface FundingRateProps {
  symbols?: string[];
  showPredicted?: boolean;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 預設監控的幣種
const DEFAULT_SYMBOLS = [
  'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ARB/USDT', 'OP/USDT',
  'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT', 'DOT/USDT'
];

async function fetchFundingRates(symbols: string[]): Promise<FundingRateData[]> {
  const params = new URLSearchParams();
  symbols.forEach((s) => params.append('symbols', s));
  const response = await fetch(`${API_URL}/api/funding-rates?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch funding rates');
  }
  return response.json();
}

export function FundingRate({ symbols = DEFAULT_SYMBOLS, showPredicted = true }: FundingRateProps) {
  const { data: rates = [], isLoading, error } = useQuery({
    queryKey: ['fundingRates', symbols],
    queryFn: () => fetchFundingRates(symbols),
    refetchInterval: 30000, // 30秒更新
    staleTime: 10000,
  });

  // 按費率排序（正負分開）
  const sortedRates = useMemo(() => {
    return [...rates].sort((a, b) => b.fundingRate - a.fundingRate);
  }, [rates]);

  // 計算倒計時
  const getCountdown = (timestamp: number) => {
    const now = Date.now();
    const diff = timestamp - now;
    if (diff <= 0) return '即將結算';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  // 費率顏色（正費率=多頭付費=做空有利，負費率=空頭付費=做多有利）
  const getRateColor = (rate: number) => {
    if (Math.abs(rate) < 0.01) return 'text-slate-400'; // 中性
    return rate > 0 ? 'text-red-400' : 'text-green-400';
  };

  // 費率強度指示
  const getRateIntensity = (rate: number) => {
    const absRate = Math.abs(rate);
    if (absRate >= 0.1) return 'extreme';
    if (absRate >= 0.05) return 'high';
    if (absRate >= 0.02) return 'medium';
    return 'low';
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">資金費率</h3>
        <div className="animate-pulse space-y-2">
          {Array(5).fill(0).map((_, i) => (
            <div key={i} className="h-10 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">資金費率</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  // 極端費率警告
  const extremeRates = sortedRates.filter((r) => Math.abs(r.fundingRate) >= 0.05);

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-300">資金費率監控</h3>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock className="w-3 h-3" />
          每 8 小時結算
        </div>
      </div>

      {/* 極端費率警告 */}
      {extremeRates.length > 0 && (
        <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-medium mb-1">
            <AlertTriangle className="w-4 h-4" />
            極端費率警告
          </div>
          <div className="text-xs text-slate-300">
            {extremeRates.map((r) => (
              <span key={r.symbol} className="mr-3">
                {r.symbol.split('/')[0]}: {(r.fundingRate * 100).toFixed(4)}%
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 費率列表 */}
      <div className="space-y-1">
        <div className="grid grid-cols-4 text-xs text-slate-400 px-2 pb-2 border-b border-slate-700">
          <span>幣種</span>
          <span className="text-right">當前費率</span>
          {showPredicted && <span className="text-right">預測費率</span>}
          <span className="text-right">結算倒計時</span>
        </div>

        {sortedRates.map((rate) => {
          const intensity = getRateIntensity(rate.fundingRate);
          return (
            <div
              key={rate.symbol}
              className={clsx(
                'grid text-sm py-2 px-2 rounded transition-colors',
                showPredicted ? 'grid-cols-4' : 'grid-cols-3',
                intensity === 'extreme' && 'bg-amber-500/10',
                intensity === 'high' && 'bg-slate-700/50'
              )}
            >
              <div className="flex items-center gap-2">
                <span className="font-medium text-white">
                  {rate.symbol.split('/')[0]}
                </span>
                {intensity === 'extreme' && (
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                )}
              </div>

              <div className={clsx('text-right font-mono flex items-center justify-end gap-1', getRateColor(rate.fundingRate))}>
                {rate.fundingRate > 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : rate.fundingRate < 0 ? (
                  <TrendingDown className="w-3 h-3" />
                ) : null}
                {(rate.fundingRate * 100).toFixed(4)}%
              </div>

              {showPredicted && (
                <div className={clsx('text-right font-mono', getRateColor(rate.predictedRate))}>
                  {(rate.predictedRate * 100).toFixed(4)}%
                </div>
              )}

              <div className="text-right text-slate-400 font-mono text-xs">
                {getCountdown(rate.fundingTime)}
              </div>
            </div>
          );
        })}
      </div>

      {/* 費率說明 */}
      <div className="mt-4 pt-3 border-t border-slate-700 text-xs text-slate-500">
        <div className="flex justify-between">
          <span className="text-red-400">正費率 → 多頭付費給空頭</span>
          <span className="text-green-400">負費率 → 空頭付費給多頭</span>
        </div>
      </div>
    </div>
  );
}
