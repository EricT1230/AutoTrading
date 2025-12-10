import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
} from 'lucide-react';
import clsx from 'clsx';

export type SignalType = 'buy' | 'sell' | 'neutral';
export type SignalStrength = 'strong' | 'medium' | 'weak';

export interface TradingSignal {
  id: string;
  symbol: string;
  type: SignalType;
  strength: SignalStrength;
  strategy: string;
  price: number;
  targetPrice?: number;
  stopLoss?: number;
  riskReward?: number;
  confidence: number; // 0-100
  indicators: {
    name: string;
    value: string;
    signal: SignalType;
  }[];
  reason: string;
  timestamp: number;
  expiry?: number; // 信號有效期
}

interface SignalPanelProps {
  symbol?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchSignals(symbol?: string): Promise<TradingSignal[]> {
  const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
  const response = await fetch(`${API_URL}/api/signals${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch signals');
  }
  return response.json();
}

// 信號強度配置
const strengthConfig = {
  strong: { label: '強烈', bgClass: 'bg-purple-500/20', textClass: 'text-purple-400' },
  medium: { label: '中等', bgClass: 'bg-blue-500/20', textClass: 'text-blue-400' },
  weak: { label: '弱', bgClass: 'bg-slate-500/20', textClass: 'text-slate-400' },
};

// 信號類型配置
const signalTypeConfig = {
  buy: { label: '買入', icon: TrendingUp, bgClass: 'bg-green-500/20', textClass: 'text-green-400' },
  sell: { label: '賣出', icon: TrendingDown, bgClass: 'bg-red-500/20', textClass: 'text-red-400' },
  neutral: { label: '觀望', icon: Minus, bgClass: 'bg-slate-500/20', textClass: 'text-slate-400' },
};

export function SignalPanel({ symbol }: SignalPanelProps) {
  const { data: signals = [], isLoading, error } = useQuery({
    queryKey: ['signals', symbol],
    queryFn: () => fetchSignals(symbol),
    refetchInterval: 10000,
    staleTime: 5000,
  });

  // 按時間排序，最新的在前
  const sortedSignals = useMemo(() => {
    return [...signals].sort((a, b) => b.timestamp - a.timestamp);
  }, [signals]);

  // 統計信號
  const signalStats = useMemo(() => {
    const buy = signals.filter((s) => s.type === 'buy').length;
    const sell = signals.filter((s) => s.type === 'sell').length;
    const neutral = signals.filter((s) => s.type === 'neutral').length;
    return { buy, sell, neutral, total: signals.length };
  }, [signals]);

  // 計算信號是否過期
  const isExpired = (signal: TradingSignal) => {
    if (!signal.expiry) return false;
    return Date.now() > signal.expiry;
  };

  // 格式化時間
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">交易信號</h3>
        <div className="animate-pulse space-y-3">
          {Array(3).fill(0).map((_, i) => (
            <div key={i} className="h-24 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">交易信號</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
      {/* 標題和統計 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-medium text-slate-300">交易信號</h3>
        </div>
        <div className="flex gap-3 text-xs">
          <span className="text-green-400">買 {signalStats.buy}</span>
          <span className="text-red-400">賣 {signalStats.sell}</span>
          <span className="text-slate-400">觀望 {signalStats.neutral}</span>
        </div>
      </div>

      {/* 信號列表 */}
      {sortedSignals.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-sm">
          目前沒有交易信號
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {sortedSignals.map((signal) => {
            const typeConfig = signalTypeConfig[signal.type];
            const expired = isExpired(signal);
            const TypeIcon = typeConfig.icon;

            return (
              <div
                key={signal.id}
                className={clsx(
                  'p-3 rounded-lg border transition-all',
                  expired
                    ? 'bg-slate-900/50 border-slate-700/50 opacity-50'
                    : 'bg-slate-900 border-slate-700'
                )}
              >
                {/* 信號頭部 */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={clsx('p-1.5 rounded', typeConfig.bgClass)}>
                      <TypeIcon className={clsx('w-4 h-4', typeConfig.textClass)} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{signal.symbol}</span>
                        <span className={clsx('px-1.5 py-0.5 rounded text-xs', typeConfig.bgClass, typeConfig.textClass)}>
                          {typeConfig.label}
                        </span>
                        <span className={clsx('px-1.5 py-0.5 rounded text-xs', strengthConfig[signal.strength].bgClass, strengthConfig[signal.strength].textClass)}>
                          {strengthConfig[signal.strength].label}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {signal.strategy}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-xs text-slate-400">
                      <Clock className="w-3 h-3" />
                      {formatTime(signal.timestamp)}
                    </div>
                    {expired && (
                      <span className="text-xs text-red-400">已過期</span>
                    )}
                  </div>
                </div>

                {/* 價格資訊 */}
                <div className="grid grid-cols-4 gap-2 text-xs mb-2">
                  <div>
                    <span className="text-slate-400">入場價</span>
                    <div className="font-mono text-slate-200">${signal.price.toLocaleString()}</div>
                  </div>
                  {signal.targetPrice && (
                    <div>
                      <span className="text-slate-400">目標價</span>
                      <div className="font-mono text-green-400">${signal.targetPrice.toLocaleString()}</div>
                    </div>
                  )}
                  {signal.stopLoss && (
                    <div>
                      <span className="text-slate-400">止損價</span>
                      <div className="font-mono text-red-400">${signal.stopLoss.toLocaleString()}</div>
                    </div>
                  )}
                  {signal.riskReward && (
                    <div>
                      <span className="text-slate-400">風報比</span>
                      <div className="font-mono text-amber-400">1:{signal.riskReward.toFixed(1)}</div>
                    </div>
                  )}
                </div>

                {/* 信心指數 */}
                <div className="mb-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">信心指數</span>
                    <span className={clsx(
                      'font-mono',
                      signal.confidence >= 70 ? 'text-green-400' :
                      signal.confidence >= 50 ? 'text-amber-400' : 'text-red-400'
                    )}>
                      {signal.confidence}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full transition-all duration-300',
                        signal.confidence >= 70 ? 'bg-green-500' :
                        signal.confidence >= 50 ? 'bg-amber-500' : 'bg-red-500'
                      )}
                      style={{ width: `${signal.confidence}%` }}
                    />
                  </div>
                </div>

                {/* 指標分析 */}
                <div className="flex flex-wrap gap-2 mb-2">
                  {signal.indicators.map((indicator, i) => (
                    <div
                      key={i}
                      className={clsx(
                        'flex items-center gap-1 px-2 py-0.5 rounded text-xs',
                        indicator.signal === 'buy' ? 'bg-green-500/10 text-green-400' :
                        indicator.signal === 'sell' ? 'bg-red-500/10 text-red-400' :
                        'bg-slate-700 text-slate-400'
                      )}
                    >
                      {indicator.signal === 'buy' ? (
                        <CheckCircle className="w-3 h-3" />
                      ) : indicator.signal === 'sell' ? (
                        <XCircle className="w-3 h-3" />
                      ) : (
                        <Minus className="w-3 h-3" />
                      )}
                      {indicator.name}: {indicator.value}
                    </div>
                  ))}
                </div>

                {/* 信號原因 */}
                <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-800/50 rounded p-2">
                  <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
                  <span>{signal.reason}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
