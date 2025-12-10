import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Star, StarOff, TrendingUp, TrendingDown } from 'lucide-react';
import clsx from 'clsx';

export interface SymbolInfo {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  price: number;
  priceChange24h: number;
  priceChangePercent24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
}

interface SymbolSelectorProps {
  selectedSymbol: string;
  onSymbolChange: (symbol: string) => void;
  favorites: string[];
  onToggleFavorite: (symbol: string) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 熱門交易對分類
const CATEGORIES = {
  'Layer 1': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'ADA/USDT', 'DOT/USDT', 'NEAR/USDT', 'ATOM/USDT'],
  'Layer 2': ['ARB/USDT', 'OP/USDT', 'MATIC/USDT', 'IMX/USDT'],
  'DeFi': ['UNI/USDT', 'AAVE/USDT', 'LINK/USDT', 'MKR/USDT', 'CRV/USDT', 'SUSHI/USDT'],
  'Meme': ['DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT', 'BONK/USDT'],
  'AI': ['FET/USDT', 'AGIX/USDT', 'RNDR/USDT', 'WLD/USDT'],
  'Gaming': ['AXS/USDT', 'SAND/USDT', 'MANA/USDT', 'GALA/USDT', 'ENJ/USDT'],
};

async function fetchTickers(): Promise<SymbolInfo[]> {
  const response = await fetch(`${API_URL}/api/tickers`);
  if (!response.ok) {
    throw new Error('Failed to fetch tickers');
  }
  return response.json();
}

export function SymbolSelector({
  selectedSymbol,
  onSymbolChange,
  favorites,
  onToggleFavorite,
}: SymbolSelectorProps) {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | 'favorites' | 'all'>('all');

  const { data: tickers = [], isLoading } = useQuery({
    queryKey: ['tickers'],
    queryFn: fetchTickers,
    refetchInterval: 5000,
    staleTime: 2000,
  });

  // 過濾和排序
  const filteredSymbols = useMemo(() => {
    let symbols = tickers;

    // 搜尋過濾
    if (search) {
      const searchLower = search.toLowerCase();
      symbols = symbols.filter(
        (s) =>
          s.symbol.toLowerCase().includes(searchLower) ||
          s.baseAsset.toLowerCase().includes(searchLower)
      );
    }

    // 分類過濾
    if (activeCategory === 'favorites') {
      symbols = symbols.filter((s) => favorites.includes(s.symbol));
    } else if (activeCategory !== 'all' && CATEGORIES[activeCategory as keyof typeof CATEGORIES]) {
      const categorySymbols = CATEGORIES[activeCategory as keyof typeof CATEGORIES];
      symbols = symbols.filter((s) => categorySymbols.includes(s.symbol));
    }

    // 按交易量排序
    return symbols.sort((a, b) => b.volume24h - a.volume24h);
  }, [tickers, search, activeCategory, favorites]);

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toFixed(2);
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* 搜尋欄 */}
      <div className="p-3 border-b border-slate-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜尋幣種..."
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
      </div>

      {/* 分類標籤 */}
      <div className="p-2 border-b border-slate-700 overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          <button
            onClick={() => setActiveCategory('favorites')}
            className={clsx(
              'px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1',
              activeCategory === 'favorites'
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            )}
          >
            <Star className="w-3 h-3" />
            收藏
          </button>
          <button
            onClick={() => setActiveCategory('all')}
            className={clsx(
              'px-3 py-1.5 rounded text-xs font-medium transition-colors',
              activeCategory === 'all'
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            )}
          >
            全部
          </button>
          {Object.keys(CATEGORIES).map((category) => (
            <button
              key={category}
              onClick={() => setActiveCategory(category)}
              className={clsx(
                'px-3 py-1.5 rounded text-xs font-medium transition-colors whitespace-nowrap',
                activeCategory === category
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              )}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* 幣種列表 */}
      <div className="max-h-96 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-slate-500">載入中...</div>
        ) : filteredSymbols.length === 0 ? (
          <div className="p-4 text-center text-slate-500">
            {activeCategory === 'favorites' ? '尚無收藏' : '找不到符合的幣種'}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
              <tr className="text-slate-400 text-xs">
                <th className="py-2 px-3 text-left font-medium">幣種</th>
                <th className="py-2 px-3 text-right font-medium">價格</th>
                <th className="py-2 px-3 text-right font-medium">24h%</th>
                <th className="py-2 px-3 text-right font-medium">24h量</th>
                <th className="py-2 px-3 w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {filteredSymbols.map((ticker) => (
                <tr
                  key={ticker.symbol}
                  onClick={() => onSymbolChange(ticker.symbol)}
                  className={clsx(
                    'cursor-pointer transition-colors',
                    selectedSymbol === ticker.symbol
                      ? 'bg-blue-500/10'
                      : 'hover:bg-slate-700/50'
                  )}
                >
                  <td className="py-2 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{ticker.baseAsset}</span>
                      <span className="text-slate-500 text-xs">/{ticker.quoteAsset}</span>
                    </div>
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-slate-200">
                    ${ticker.price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: ticker.price < 1 ? 6 : 2
                    })}
                  </td>
                  <td className="py-2 px-3 text-right">
                    <div
                      className={clsx(
                        'flex items-center justify-end gap-1 font-mono',
                        ticker.priceChangePercent24h >= 0 ? 'text-green-400' : 'text-red-400'
                      )}
                    >
                      {ticker.priceChangePercent24h >= 0 ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {ticker.priceChangePercent24h >= 0 ? '+' : ''}
                      {ticker.priceChangePercent24h.toFixed(2)}%
                    </div>
                  </td>
                  <td className="py-2 px-3 text-right text-slate-400 font-mono">
                    ${formatVolume(ticker.volume24h)}
                  </td>
                  <td className="py-2 px-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleFavorite(ticker.symbol);
                      }}
                      className="p-1 hover:bg-slate-600 rounded transition-colors"
                    >
                      {favorites.includes(ticker.symbol) ? (
                        <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                      ) : (
                        <StarOff className="w-4 h-4 text-slate-500" />
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
