import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  BarChart2,
} from 'lucide-react';
import clsx from 'clsx';

interface TimeframeAnalysis {
  timeframe: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  strength: number; // 0-100
  rsi: number;
  macd: {
    value: number;
    signal: number;
    histogram: number;
  };
  ema: {
    ema20: number;
    ema50: number;
    ema200: number;
  };
  support: number;
  resistance: number;
  volume: {
    current: number;
    average: number;
    ratio: number;
  };
}

interface MultiTimeframeAnalysisProps {
  symbol: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TIMEFRAMES = [
  { value: '5m', label: '5分' },
  { value: '15m', label: '15分' },
  { value: '1h', label: '1小時' },
  { value: '4h', label: '4小時' },
  { value: '1d', label: '日線' },
];

async function fetchTimeframeAnalysis(symbol: string, timeframe: string): Promise<TimeframeAnalysis> {
  const response = await fetch(
    `${API_URL}/api/analysis?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch analysis');
  }
  return response.json();
}

type TrendType = 'bullish' | 'bearish' | 'neutral';

// 趨勢配置
const trendConfig: Record<TrendType, { label: string; icon: typeof TrendingUp; color: string; bg: string }> = {
  bullish: { label: '看漲', icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-500/20' },
  bearish: { label: '看跌', icon: TrendingDown, color: 'text-red-400', bg: 'bg-red-500/20' },
  neutral: { label: '中性', icon: Minus, color: 'text-slate-400', bg: 'bg-slate-500/20' },
};

export function MultiTimeframeAnalysis({ symbol }: MultiTimeframeAnalysisProps) {
  // 併發查詢所有時間框架
  const results = useQueries({
    queries: TIMEFRAMES.map((tf) => ({
      queryKey: ['analysis', symbol, tf.value],
      queryFn: () => fetchTimeframeAnalysis(symbol, tf.value),
      staleTime: tf.value === '5m' ? 30000 : tf.value === '1d' ? 300000 : 60000,
      refetchInterval: tf.value === '5m' ? 30000 : tf.value === '1d' ? 300000 : 60000,
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const analyses = results.map((r) => r.data).filter(Boolean) as TimeframeAnalysis[];

  // 計算整體趨勢（加權平均）
  const overallTrend = useMemo(() => {
    if (analyses.length === 0) return null;

    // 時間框架權重（較大時間框架權重較高）
    const weights = { '5m': 1, '15m': 2, '1h': 3, '4h': 4, '1d': 5 };
    let totalWeight = 0;
    let weightedScore = 0;

    analyses.forEach((a) => {
      const weight = weights[a.timeframe as keyof typeof weights] || 1;
      const score = a.trend === 'bullish' ? 1 : a.trend === 'bearish' ? -1 : 0;
      weightedScore += score * weight * a.strength;
      totalWeight += weight;
    });

    const avgScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
    const trend = avgScore > 20 ? 'bullish' : avgScore < -20 ? 'bearish' : 'neutral';
    const confidence = Math.min(Math.abs(avgScore), 100);

    return { trend, confidence };
  }, [analyses]);

  // RSI 狀態
  const getRsiStatus = (rsi: number) => {
    if (rsi > 70) return { label: '超買', color: 'text-red-400' };
    if (rsi < 30) return { label: '超賣', color: 'text-green-400' };
    return { label: '中性', color: 'text-slate-400' };
  };

  // MACD 狀態
  const getMacdStatus = (macd: TimeframeAnalysis['macd']) => {
    if (macd.histogram > 0 && macd.value > macd.signal) {
      return { label: '多頭', color: 'text-green-400' };
    }
    if (macd.histogram < 0 && macd.value < macd.signal) {
      return { label: '空頭', color: 'text-red-400' };
    }
    return { label: '轉換', color: 'text-amber-400' };
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">多時間框架分析</h3>
        <div className="animate-pulse space-y-2">
          {TIMEFRAMES.map((tf) => (
            <div key={tf.value} className="h-16 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-medium text-slate-300">多時間框架分析</h3>
        </div>
        <span className="text-xs text-slate-400">{symbol}</span>
      </div>

      {/* 整體趨勢摘要 */}
      {overallTrend && (
        <div className={clsx('p-3 rounded-lg mb-4', trendConfig[overallTrend.trend as TrendType].bg)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {(() => {
                const Icon = trendConfig[overallTrend.trend as TrendType].icon;
                return <Icon className={clsx('w-5 h-5', trendConfig[overallTrend.trend as TrendType].color)} />;
              })()}
              <span className={clsx('font-medium', trendConfig[overallTrend.trend as TrendType].color)}>
                整體趨勢: {trendConfig[overallTrend.trend as TrendType].label}
              </span>
            </div>
            <span className="text-xs text-slate-400">
              信心度: {overallTrend.confidence.toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      {/* 各時間框架詳細分析 */}
      <div className="space-y-2">
        {TIMEFRAMES.map((tf) => {
          const analysis = analyses.find((a) => a.timeframe === tf.value);
          if (!analysis) return null;

          const trend = trendConfig[analysis.trend as TrendType];
          const TrendIcon = trend.icon;
          const rsiStatus = getRsiStatus(analysis.rsi);
          const macdStatus = getMacdStatus(analysis.macd);

          return (
            <div
              key={tf.value}
              className="p-3 bg-slate-900 rounded-lg border border-slate-700/50"
            >
              {/* 時間框架和趨勢 */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white w-12">{tf.label}</span>
                  <div className={clsx('flex items-center gap-1 px-2 py-0.5 rounded', trend.bg)}>
                    <TrendIcon className={clsx('w-3 h-3', trend.color)} />
                    <span className={clsx('text-xs', trend.color)}>{trend.label}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-xs text-slate-400">強度</span>
                  <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full',
                        analysis.trend === 'bullish' ? 'bg-green-500' :
                        analysis.trend === 'bearish' ? 'bg-red-500' : 'bg-slate-500'
                      )}
                      style={{ width: `${analysis.strength}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* 指標狀態 */}
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div>
                  <span className="text-slate-400">RSI</span>
                  <div className={clsx('font-mono', rsiStatus.color)}>
                    {analysis.rsi.toFixed(1)} {rsiStatus.label}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">MACD</span>
                  <div className={clsx('font-mono', macdStatus.color)}>
                    {macdStatus.label}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">支撐</span>
                  <div className="font-mono text-green-400">
                    ${analysis.support.toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400">阻力</span>
                  <div className="font-mono text-red-400">
                    ${analysis.resistance.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* 成交量比較 */}
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-slate-400">成交量:</span>
                <div className={clsx(
                  'text-xs font-mono',
                  analysis.volume.ratio > 1.5 ? 'text-green-400' :
                  analysis.volume.ratio < 0.5 ? 'text-red-400' : 'text-slate-400'
                )}>
                  {(analysis.volume.ratio * 100).toFixed(0)}% 平均
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 趨勢一致性 */}
      <div className="mt-4 pt-3 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">趨勢一致性</span>
          <div className="flex gap-1">
            {analyses.map((a) => (
              <div
                key={a.timeframe}
                className={clsx(
                  'w-4 h-4 rounded flex items-center justify-center',
                  a.trend === 'bullish' ? 'bg-green-500/30' :
                  a.trend === 'bearish' ? 'bg-red-500/30' : 'bg-slate-500/30'
                )}
                title={`${a.timeframe}: ${trendConfig[a.trend].label}`}
              >
                {a.trend === 'bullish' ? (
                  <ChevronRight className="w-3 h-3 text-green-400 rotate-[-90deg]" />
                ) : a.trend === 'bearish' ? (
                  <ChevronRight className="w-3 h-3 text-red-400 rotate-90" />
                ) : (
                  <Minus className="w-3 h-3 text-slate-400" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
