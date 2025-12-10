import { useEffect, useRef, useMemo } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type LineData, type Time, ColorType, LineSeries, HistogramSeries } from 'lightweight-charts';

interface KlineData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface TechnicalIndicatorsProps {
  data: KlineData[];
  height?: number;
}

// RSI 計算
function calculateRSI(data: KlineData[], period: number = 14): LineData<Time>[] {
  if (data.length < period + 1) return [];

  const rsi: LineData<Time>[] = [];
  let gains = 0;
  let losses = 0;

  // 計算初始平均漲跌幅
  for (let i = 1; i <= period; i++) {
    const change = data[i].close - data[i - 1].close;
    if (change > 0) gains += change;
    else losses -= change;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  // 計算第一個 RSI
  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  rsi.push({
    time: data[period].time as Time,
    value: 100 - (100 / (1 + rs))
  });

  // 平滑計算後續 RSI
  for (let i = period + 1; i < data.length; i++) {
    const change = data[i].close - data[i - 1].close;
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? -change : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    const rsValue = avgLoss === 0 ? 100 : avgGain / avgLoss;
    rsi.push({
      time: data[i].time as Time,
      value: 100 - (100 / (1 + rsValue))
    });
  }

  return rsi;
}

// MACD 計算
function calculateMACD(
  data: KlineData[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): { macd: LineData<Time>[]; signal: LineData<Time>[]; histogram: LineData<Time>[] } {
  if (data.length < slowPeriod) {
    return { macd: [], signal: [], histogram: [] };
  }

  // 計算 EMA
  const calculateEMA = (prices: number[], period: number): number[] => {
    const ema: number[] = [];
    const multiplier = 2 / (period + 1);

    // 第一個值用 SMA
    let sum = 0;
    for (let i = 0; i < period; i++) {
      sum += prices[i];
    }
    ema[period - 1] = sum / period;

    // 後續用 EMA
    for (let i = period; i < prices.length; i++) {
      ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1];
    }

    return ema;
  };

  const closes = data.map(d => d.close);
  const fastEMA = calculateEMA(closes, fastPeriod);
  const slowEMA = calculateEMA(closes, slowPeriod);

  // 計算 MACD 線
  const macdLine: number[] = [];
  for (let i = slowPeriod - 1; i < data.length; i++) {
    macdLine.push(fastEMA[i] - slowEMA[i]);
  }

  // 計算信號線
  const signalLine = calculateEMA(macdLine, signalPeriod);

  // 組裝結果
  const macd: LineData<Time>[] = [];
  const signal: LineData<Time>[] = [];
  const histogram: LineData<Time>[] = [];

  for (let i = signalPeriod - 1; i < macdLine.length; i++) {
    const dataIdx = slowPeriod - 1 + i;
    const time = data[dataIdx].time as Time;

    macd.push({ time, value: macdLine[i] });
    signal.push({ time, value: signalLine[i] });
    histogram.push({ time, value: macdLine[i] - signalLine[i] });
  }

  return { macd, signal, histogram };
}

export function TechnicalIndicators({ data, height = 150 }: TechnicalIndicatorsProps) {
  const rsiContainerRef = useRef<HTMLDivElement>(null);
  const macdContainerRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const signalLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const histogramRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  // 計算指標數據
  const rsiData = useMemo(() => calculateRSI(data, 14), [data]);
  const macdData = useMemo(() => calculateMACD(data, 12, 26, 9), [data]);

  // RSI 圖表
  useEffect(() => {
    if (!rsiContainerRef.current) return;

    if (!rsiChartRef.current) {
      rsiChartRef.current = createChart(rsiContainerRef.current, {
        width: rsiContainerRef.current.clientWidth,
        height,
        layout: {
          background: { type: ColorType.Solid, color: '#1e293b' },
          textColor: '#94a3b8',
        },
        grid: {
          vertLines: { color: '#334155' },
          horzLines: { color: '#334155' },
        },
        rightPriceScale: {
          borderColor: '#334155',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: '#334155',
          timeVisible: true,
        },
      });

      // RSI 線
      rsiSeriesRef.current = rsiChartRef.current.addSeries(LineSeries, {
        color: '#8b5cf6',
        lineWidth: 2,
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
      });

      // 添加超買線 (70)
      const overboughtLine = rsiChartRef.current.addSeries(LineSeries, {
        color: '#ef4444',
        lineWidth: 1,
        lineStyle: 2,
        priceFormat: { type: 'price', precision: 0, minMove: 1 },
      });
      if (rsiData.length > 0) {
        overboughtLine.setData([
          { time: rsiData[0].time, value: 70 },
          { time: rsiData[rsiData.length - 1]?.time || rsiData[0].time, value: 70 }
        ]);
      }

      // 添加超賣線 (30)
      const oversoldLine = rsiChartRef.current.addSeries(LineSeries, {
        color: '#22c55e',
        lineWidth: 1,
        lineStyle: 2,
        priceFormat: { type: 'price', precision: 0, minMove: 1 },
      });
      if (rsiData.length > 0) {
        oversoldLine.setData([
          { time: rsiData[0].time, value: 30 },
          { time: rsiData[rsiData.length - 1]?.time || rsiData[0].time, value: 30 }
        ]);
      }
    }

    if (rsiSeriesRef.current && rsiData.length > 0) {
      rsiSeriesRef.current.setData(rsiData);
      rsiChartRef.current?.timeScale().fitContent();
    }

    const handleResize = () => {
      if (rsiContainerRef.current && rsiChartRef.current) {
        rsiChartRef.current.applyOptions({
          width: rsiContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [rsiData, height]);

  // MACD 圖表
  useEffect(() => {
    if (!macdContainerRef.current) return;

    if (!macdChartRef.current) {
      macdChartRef.current = createChart(macdContainerRef.current, {
        width: macdContainerRef.current.clientWidth,
        height,
        layout: {
          background: { type: ColorType.Solid, color: '#1e293b' },
          textColor: '#94a3b8',
        },
        grid: {
          vertLines: { color: '#334155' },
          horzLines: { color: '#334155' },
        },
        rightPriceScale: {
          borderColor: '#334155',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: '#334155',
          timeVisible: true,
        },
      });

      macdLineRef.current = macdChartRef.current.addSeries(LineSeries, {
        color: '#3b82f6',
        lineWidth: 2,
        priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      });

      signalLineRef.current = macdChartRef.current.addSeries(LineSeries, {
        color: '#f59e0b',
        lineWidth: 2,
        priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      });

      histogramRef.current = macdChartRef.current.addSeries(HistogramSeries, {
        color: '#22c55e',
        priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      });
    }

    if (macdData.macd.length > 0) {
      macdLineRef.current?.setData(macdData.macd);
      signalLineRef.current?.setData(macdData.signal);

      // 柱狀圖顏色根據正負值
      const coloredHistogram = macdData.histogram.map(h => ({
        ...h,
        color: h.value >= 0 ? '#22c55e' : '#ef4444'
      }));
      histogramRef.current?.setData(coloredHistogram);

      macdChartRef.current?.timeScale().fitContent();
    }

    const handleResize = () => {
      if (macdContainerRef.current && macdChartRef.current) {
        macdChartRef.current.applyOptions({
          width: macdContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [macdData, height]);

  // 清理
  useEffect(() => {
    return () => {
      rsiChartRef.current?.remove();
      macdChartRef.current?.remove();
      rsiChartRef.current = null;
      macdChartRef.current = null;
    };
  }, []);

  // 計算當前 RSI 狀態
  const currentRSI = rsiData[rsiData.length - 1]?.value;
  const rsiStatus = currentRSI
    ? currentRSI > 70 ? 'overbought' : currentRSI < 30 ? 'oversold' : 'neutral'
    : null;

  return (
    <div className="space-y-4">
      {/* RSI */}
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-slate-300">RSI (14)</h3>
          {currentRSI && (
            <span className={`text-sm font-mono ${
              rsiStatus === 'overbought' ? 'text-red-400' :
              rsiStatus === 'oversold' ? 'text-green-400' :
              'text-slate-400'
            }`}>
              {currentRSI.toFixed(2)}
              {rsiStatus === 'overbought' && ' 超買'}
              {rsiStatus === 'oversold' && ' 超賣'}
            </span>
          )}
        </div>
        <div ref={rsiContainerRef} />
      </div>

      {/* MACD */}
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-slate-300">MACD (12, 26, 9)</h3>
          <div className="flex gap-4 text-xs">
            <span className="text-blue-400">MACD</span>
            <span className="text-amber-400">Signal</span>
            <span className="text-slate-400">Histogram</span>
          </div>
        </div>
        <div ref={macdContainerRef} />
      </div>
    </div>
  );
}
