import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';

interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
}

interface OrderBookData {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  spread: number;
  spreadPercent: number;
  lastUpdateTime: number;
}

interface OrderBookProps {
  symbol: string;
  depth?: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchOrderBook(symbol: string, depth: number): Promise<OrderBookData> {
  const response = await fetch(`${API_URL}/api/orderbook?symbol=${encodeURIComponent(symbol)}&depth=${depth}`);
  if (!response.ok) {
    throw new Error('Failed to fetch order book');
  }
  return response.json();
}

export function OrderBook({ symbol, depth = 15 }: OrderBookProps) {
  const { data: orderBook, isLoading, error } = useQuery({
    queryKey: ['orderbook', symbol, depth],
    queryFn: () => fetchOrderBook(symbol, depth),
    refetchInterval: 500, // 高頻更新
    staleTime: 200,
  });

  // 計算最大交易量（用於進度條寬度）
  const maxTotal = useMemo(() => {
    if (!orderBook) return 0;
    const maxBid = Math.max(...orderBook.bids.map((b) => b.total));
    const maxAsk = Math.max(...orderBook.asks.map((a) => a.total));
    return Math.max(maxBid, maxAsk);
  }, [orderBook]);

  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(6);
  };

  const formatSize = (size: number) => {
    if (size >= 1000) return `${(size / 1000).toFixed(2)}K`;
    return size.toFixed(4);
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">訂單簿</h3>
        <div className="animate-pulse space-y-1">
          {Array(10).fill(0).map((_, i) => (
            <div key={i} className="h-5 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !orderBook) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-4">訂單簿</h3>
        <div className="text-red-400 text-sm">載入失敗</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-slate-300">訂單簿</h3>
        <div className="text-xs text-slate-400">
          價差: <span className="text-white font-mono">{orderBook.spread.toFixed(2)}</span>
          <span className="ml-1 text-slate-500">({orderBook.spreadPercent.toFixed(3)}%)</span>
        </div>
      </div>

      {/* 表頭 */}
      <div className="grid grid-cols-3 text-xs text-slate-400 mb-1 px-1">
        <span>價格</span>
        <span className="text-right">數量</span>
        <span className="text-right">累計</span>
      </div>

      {/* 賣單 (倒序顯示) */}
      <div className="space-y-0.5 mb-2">
        {[...orderBook.asks].reverse().map((ask, i) => (
          <div key={`ask-${i}`} className="relative">
            {/* 背景進度條 */}
            <div
              className="absolute right-0 top-0 h-full bg-red-500/10"
              style={{ width: `${(ask.total / maxTotal) * 100}%` }}
            />
            {/* 數據 */}
            <div className="relative grid grid-cols-3 text-xs py-0.5 px-1">
              <span className="text-red-400 font-mono">{formatPrice(ask.price)}</span>
              <span className="text-right text-slate-300 font-mono">{formatSize(ask.size)}</span>
              <span className="text-right text-slate-500 font-mono">{formatSize(ask.total)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 中間價格 */}
      <div className="py-2 border-y border-slate-700 text-center">
        <span
          className={clsx(
            'text-lg font-bold font-mono',
            orderBook.bids[0]?.price > orderBook.asks[0]?.price ? 'text-green-400' : 'text-red-400'
          )}
        >
          {formatPrice((orderBook.bids[0]?.price + orderBook.asks[0]?.price) / 2)}
        </span>
      </div>

      {/* 買單 */}
      <div className="space-y-0.5 mt-2">
        {orderBook.bids.map((bid, i) => (
          <div key={`bid-${i}`} className="relative">
            {/* 背景進度條 */}
            <div
              className="absolute right-0 top-0 h-full bg-green-500/10"
              style={{ width: `${(bid.total / maxTotal) * 100}%` }}
            />
            {/* 數據 */}
            <div className="relative grid grid-cols-3 text-xs py-0.5 px-1">
              <span className="text-green-400 font-mono">{formatPrice(bid.price)}</span>
              <span className="text-right text-slate-300 font-mono">{formatSize(bid.size)}</span>
              <span className="text-right text-slate-500 font-mono">{formatSize(bid.total)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 買賣比例 */}
      <div className="mt-3 pt-3 border-t border-slate-700">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-green-400">買方</span>
          <span className="text-red-400">賣方</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden flex">
          {(() => {
            const totalBids = orderBook.bids.reduce((sum, b) => sum + b.total, 0);
            const totalAsks = orderBook.asks.reduce((sum, a) => sum + a.total, 0);
            const bidPercent = (totalBids / (totalBids + totalAsks)) * 100;
            return (
              <>
                <div
                  className="h-full bg-green-500 transition-all duration-300"
                  style={{ width: `${bidPercent}%` }}
                />
                <div
                  className="h-full bg-red-500 transition-all duration-300"
                  style={{ width: `${100 - bidPercent}%` }}
                />
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
