import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell,
  BellOff,
  Plus,
  Trash2,
  X,
  TrendingUp,
  TrendingDown,
  Activity,
  Volume2,
} from 'lucide-react';
import clsx from 'clsx';

export type AlertType = 'price_above' | 'price_below' | 'price_cross' | 'rsi' | 'macd_cross' | 'volume_spike';

export interface PriceAlert {
  id: string;
  symbol: string;
  type: AlertType;
  condition: {
    value: number;
    comparison?: 'above' | 'below' | 'cross';
    indicator?: string;
  };
  message: string;
  enabled: boolean;
  triggered: boolean;
  triggeredAt?: number;
  createdAt: number;
  repeatInterval?: number; // 重複觸發間隔 (ms)，0 = 只觸發一次
}

interface AlertManagerProps {
  defaultSymbol?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 警報類型配置
const alertTypeConfig: Record<AlertType, { label: string; icon: React.ComponentType<{ className?: string }>; description: string }> = {
  price_above: { label: '價格高於', icon: TrendingUp, description: '當價格突破指定價位時觸發' },
  price_below: { label: '價格低於', icon: TrendingDown, description: '當價格跌破指定價位時觸發' },
  price_cross: { label: '價格穿越', icon: Activity, description: '當價格穿越指定價位時觸發' },
  rsi: { label: 'RSI 警報', icon: Activity, description: '當 RSI 達到指定數值時觸發' },
  macd_cross: { label: 'MACD 交叉', icon: Activity, description: '當 MACD 發生金叉或死叉時觸發' },
  volume_spike: { label: '成交量異常', icon: Volume2, description: '當成交量超過平均值指定倍數時觸發' },
};

async function fetchAlerts(): Promise<PriceAlert[]> {
  const response = await fetch(`${API_URL}/api/alerts`);
  if (!response.ok) throw new Error('Failed to fetch alerts');
  return response.json();
}

async function createAlert(alert: Omit<PriceAlert, 'id' | 'createdAt' | 'triggered'>): Promise<PriceAlert> {
  const response = await fetch(`${API_URL}/api/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(alert),
  });
  if (!response.ok) throw new Error('Failed to create alert');
  return response.json();
}

async function updateAlert(id: string, updates: Partial<PriceAlert>): Promise<PriceAlert> {
  const response = await fetch(`${API_URL}/api/alerts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update alert');
  return response.json();
}

async function deleteAlert(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/alerts/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete alert');
}

export function AlertManager({ defaultSymbol = 'BTC/USDT' }: AlertManagerProps) {
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);
  const [newAlert, setNewAlert] = useState<{
    symbol: string;
    type: AlertType;
    value: number;
    message: string;
  }>({
    symbol: defaultSymbol,
    type: 'price_above',
    value: 0,
    message: '',
  });

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
    refetchInterval: 5000,
  });

  const createMutation = useMutation({
    mutationFn: createAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setIsCreating(false);
      setNewAlert({ symbol: defaultSymbol, type: 'price_above', value: 0, message: '' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<PriceAlert> }) =>
      updateAlert(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  // 分類警報
  const { activeAlerts, triggeredAlerts } = useMemo(() => {
    const active = alerts.filter((a) => !a.triggered && a.enabled);
    const triggered = alerts.filter((a) => a.triggered);
    return { activeAlerts: active, triggeredAlerts: triggered };
  }, [alerts]);

  const handleCreateAlert = () => {
    if (!newAlert.value || !newAlert.message) return;
    createMutation.mutate({
      symbol: newAlert.symbol,
      type: newAlert.type,
      condition: { value: newAlert.value },
      message: newAlert.message,
      enabled: true,
    });
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">價格警報</h3>
        <div className="animate-pulse space-y-2">
          {Array(3).fill(0).map((_, i) => (
            <div key={i} className="h-16 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
      {/* 標題和新增按鈕 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-medium text-slate-300">價格警報</h3>
          <span className="text-xs text-slate-500">({activeAlerts.length} 啟用中)</span>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className={clsx(
            'p-1.5 rounded transition-colors',
            isCreating ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
          )}
        >
          {isCreating ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
        </button>
      </div>

      {/* 新增警報表單 */}
      {isCreating && (
        <div className="mb-4 p-3 bg-slate-900 rounded-lg border border-slate-700">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">幣種</label>
              <input
                type="text"
                value={newAlert.symbol}
                onChange={(e) => setNewAlert({ ...newAlert, symbol: e.target.value.toUpperCase() })}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white"
                placeholder="BTC/USDT"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">類型</label>
              <select
                value={newAlert.type}
                onChange={(e) => setNewAlert({ ...newAlert, type: e.target.value as AlertType })}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white"
              >
                {Object.entries(alertTypeConfig).map(([key, config]) => (
                  <option key={key} value={key}>{config.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                {newAlert.type === 'rsi' ? 'RSI 數值' :
                 newAlert.type === 'volume_spike' ? '倍數' : '價格'}
              </label>
              <input
                type="number"
                value={newAlert.value || ''}
                onChange={(e) => setNewAlert({ ...newAlert, value: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white"
                placeholder={newAlert.type === 'rsi' ? '70' : newAlert.type === 'volume_spike' ? '2' : '50000'}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">提示訊息</label>
              <input
                type="text"
                value={newAlert.message}
                onChange={(e) => setNewAlert({ ...newAlert, message: e.target.value })}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white"
                placeholder="價格突破關鍵位"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setIsCreating(false)}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200"
            >
              取消
            </button>
            <button
              onClick={handleCreateAlert}
              disabled={!newAlert.value || !newAlert.message}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-sm rounded transition-colors"
            >
              建立警報
            </button>
          </div>
        </div>
      )}

      {/* 啟用中的警報 */}
      {activeAlerts.length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-slate-400 mb-2">啟用中</div>
          <div className="space-y-2">
            {activeAlerts.map((alert) => {
              const config = alertTypeConfig[alert.type];
              const Icon = config.icon;
              return (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700"
                >
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      'p-1.5 rounded',
                      alert.type.includes('above') || alert.type === 'macd_cross' ? 'bg-green-500/20' :
                      alert.type.includes('below') ? 'bg-red-500/20' : 'bg-blue-500/20'
                    )}>
                      <Icon className={clsx(
                        'w-4 h-4',
                        alert.type.includes('above') || alert.type === 'macd_cross' ? 'text-green-400' :
                        alert.type.includes('below') ? 'text-red-400' : 'text-blue-400'
                      )} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{alert.symbol}</span>
                        <span className="text-xs text-slate-400">{config.label}</span>
                        <span className="text-sm font-mono text-amber-400">
                          {alert.type === 'rsi' ? alert.condition.value :
                           alert.type === 'volume_spike' ? `${alert.condition.value}x` :
                           `$${alert.condition.value.toLocaleString()}`}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">{alert.message}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateMutation.mutate({
                        id: alert.id,
                        updates: { enabled: !alert.enabled }
                      })}
                      className={clsx(
                        'p-1.5 rounded transition-colors',
                        alert.enabled ? 'text-green-400 hover:bg-green-500/20' : 'text-slate-500 hover:bg-slate-700'
                      )}
                    >
                      {alert.enabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(alert.id)}
                      className="p-1.5 text-red-400 hover:bg-red-500/20 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 已觸發的警報 */}
      {triggeredAlerts.length > 0 && (
        <div>
          <div className="text-xs text-slate-400 mb-2">已觸發</div>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {triggeredAlerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-2 bg-amber-500/10 rounded border border-amber-500/30"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white">{alert.symbol}</span>
                    <span className="text-xs text-amber-400">{alert.message}</span>
                  </div>
                  <div className="text-xs text-slate-500">
                    {alert.triggeredAt && formatTime(alert.triggeredAt)}
                  </div>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(alert.id)}
                  className="p-1 text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 空狀態 */}
      {alerts.length === 0 && !isCreating && (
        <div className="text-center py-8 text-slate-500 text-sm">
          尚無警報，點擊 + 建立新警報
        </div>
      )}
    </div>
  );
}
