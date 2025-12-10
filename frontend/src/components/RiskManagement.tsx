import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

export interface RiskMetrics {
  // 帳戶狀態
  accountBalance: number;
  availableMargin: number;
  usedMargin: number;
  marginRatio: number; // 保證金率 (%)

  // 風險限制
  maxRiskPerTrade: number; // 單筆最大風險 (%)
  maxDailyLoss: number; // 每日最大虧損 (%)
  maxPositions: number; // 最大持倉數

  // 當日統計
  dailyPnl: number;
  dailyPnlPercent: number;
  dailyTradeCount: number;
  dailyVolume: number;

  // 風險指標
  currentDrawdown: number; // 當前回撤 (%)
  maxDrawdown: number; // 最大回撤 (%)
  sharpeRatio: number;
  winRate: number;

  // 當前狀態
  currentPositions: number;
  openOrders: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

interface RiskManagementProps {
  metrics?: RiskMetrics;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchRiskMetrics(): Promise<RiskMetrics> {
  const response = await fetch(`${API_URL}/api/risk/metrics`);
  if (!response.ok) {
    throw new Error('Failed to fetch risk metrics');
  }
  return response.json();
}

// 進度條組件
function ProgressBar({
  value,
  max,
  color = 'blue',
  showLabel = true,
}: {
  value: number;
  max: number;
  color?: 'blue' | 'green' | 'red' | 'amber';
  showLabel?: boolean;
}) {
  const percent = Math.min((value / max) * 100, 100);
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    amber: 'bg-amber-500',
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-300`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-slate-400 w-12 text-right">{percent.toFixed(0)}%</span>
      )}
    </div>
  );
}

// 風險等級指示器
function RiskLevelBadge({ level }: { level: RiskMetrics['riskLevel'] }) {
  const config = {
    low: { label: '低風險', bgClass: 'bg-green-500/20', textClass: 'text-green-400' },
    medium: { label: '中風險', bgClass: 'bg-amber-500/20', textClass: 'text-amber-400' },
    high: { label: '高風險', bgClass: 'bg-orange-500/20', textClass: 'text-orange-400' },
    critical: { label: '危險', bgClass: 'bg-red-500/20', textClass: 'text-red-400' },
  };

  const { label, bgClass, textClass } = config[level];

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${bgClass} ${textClass}`}>
      {label}
    </span>
  );
}

export function RiskManagement({ metrics: propMetrics }: RiskManagementProps) {
  const { data: queryMetrics, isLoading, error } = useQuery({
    queryKey: ['riskMetrics'],
    queryFn: fetchRiskMetrics,
    enabled: !propMetrics,
    refetchInterval: 5000,
    staleTime: 2000,
  });

  const metrics = propMetrics || queryMetrics;

  // 計算風險使用率
  const riskUsage = useMemo(() => {
    if (!metrics) return null;

    return {
      marginUsage: (metrics.usedMargin / metrics.accountBalance) * 100,
      dailyLossUsage: Math.abs(metrics.dailyPnlPercent) / metrics.maxDailyLoss * 100,
      positionUsage: (metrics.currentPositions / metrics.maxPositions) * 100,
    };
  }, [metrics]);

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">風險管理</h3>
        <div className="animate-pulse space-y-4">
          <div className="h-20 bg-slate-700 rounded" />
          <div className="h-32 bg-slate-700 rounded" />
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-4">風險管理</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4 space-y-6">
      {/* 標題和風險等級 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-300">風險管理</h3>
        <RiskLevelBadge level={metrics.riskLevel} />
      </div>

      {/* 帳戶概覽 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-1">帳戶餘額</div>
          <div className="text-lg font-mono text-white">
            ${metrics.accountBalance.toLocaleString()}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-1">可用保證金</div>
          <div className="text-lg font-mono text-white">
            ${metrics.availableMargin.toLocaleString()}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-1">當日盈虧</div>
          <div
            className={`text-lg font-mono ${
              metrics.dailyPnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {metrics.dailyPnl >= 0 ? '+' : ''}${metrics.dailyPnl.toFixed(2)}
            <span className="text-xs ml-1">
              ({metrics.dailyPnlPercent >= 0 ? '+' : ''}
              {metrics.dailyPnlPercent.toFixed(2)}%)
            </span>
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-1">保證金率</div>
          <div
            className={`text-lg font-mono ${
              metrics.marginRatio > 100
                ? 'text-green-400'
                : metrics.marginRatio > 50
                ? 'text-amber-400'
                : 'text-red-400'
            }`}
          >
            {metrics.marginRatio.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 風險限制使用狀況 */}
      <div className="space-y-4">
        <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          風險限制使用狀況
        </h4>

        {/* 保證金使用率 */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">保證金使用率</span>
            <span className="text-slate-300">
              ${metrics.usedMargin.toLocaleString()} / ${metrics.accountBalance.toLocaleString()}
            </span>
          </div>
          <ProgressBar
            value={riskUsage?.marginUsage || 0}
            max={100}
            color={riskUsage && riskUsage.marginUsage > 80 ? 'red' : 'blue'}
          />
        </div>

        {/* 每日虧損限制 */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">每日虧損限制</span>
            <span className="text-slate-300">
              {Math.abs(metrics.dailyPnlPercent).toFixed(2)}% / {metrics.maxDailyLoss}%
            </span>
          </div>
          <ProgressBar
            value={riskUsage?.dailyLossUsage || 0}
            max={100}
            color={
              riskUsage && riskUsage.dailyLossUsage > 80
                ? 'red'
                : riskUsage && riskUsage.dailyLossUsage > 50
                ? 'amber'
                : 'green'
            }
          />
        </div>

        {/* 持倉數量 */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">持倉數量</span>
            <span className="text-slate-300">
              {metrics.currentPositions} / {metrics.maxPositions}
            </span>
          </div>
          <ProgressBar
            value={riskUsage?.positionUsage || 0}
            max={100}
            color={riskUsage && riskUsage.positionUsage >= 100 ? 'red' : 'blue'}
          />
        </div>
      </div>

      {/* 風險指標 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-700">
        <div>
          <div className="text-xs text-slate-400 mb-1">當前回撤</div>
          <div
            className={`text-sm font-mono ${
              metrics.currentDrawdown > 10 ? 'text-red-400' : 'text-slate-300'
            }`}
          >
            {metrics.currentDrawdown.toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">最大回撤</div>
          <div className="text-sm font-mono text-slate-300">{metrics.maxDrawdown.toFixed(2)}%</div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">夏普比率</div>
          <div
            className={`text-sm font-mono ${
              metrics.sharpeRatio > 1 ? 'text-green-400' : 'text-slate-300'
            }`}
          >
            {metrics.sharpeRatio.toFixed(2)}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">勝率</div>
          <div
            className={`text-sm font-mono ${
              metrics.winRate >= 50 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {metrics.winRate.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 當日統計 */}
      <div className="flex flex-wrap gap-4 pt-4 border-t border-slate-700 text-xs">
        <div>
          <span className="text-slate-400">當日交易: </span>
          <span className="text-slate-300 font-mono">{metrics.dailyTradeCount} 筆</span>
        </div>
        <div>
          <span className="text-slate-400">當日成交量: </span>
          <span className="text-slate-300 font-mono">${metrics.dailyVolume.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-slate-400">掛單數: </span>
          <span className="text-slate-300 font-mono">{metrics.openOrders} 筆</span>
        </div>
        <div>
          <span className="text-slate-400">單筆風險: </span>
          <span className="text-slate-300 font-mono">{metrics.maxRiskPerTrade}%</span>
        </div>
      </div>
    </div>
  );
}
