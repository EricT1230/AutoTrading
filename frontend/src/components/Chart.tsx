import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';

interface ChartProps {
    data: { time: number; open: number; high: number; low: number; close: number }[];
    colors?: {
        backgroundColor?: string;
        lineColor?: string;
        textColor?: string;
        areaTopColor?: string;
        areaBottomColor?: string;
    };
}

export const Chart: React.FC<ChartProps> = ({ data, colors = {} }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const seriesRef = useRef<any>(null);

    const {
        backgroundColor = '#1e293b',
        textColor = '#d1d5db',
    } = colors;

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            chartRef.current?.applyOptions({ width: chartContainerRef.current!.clientWidth });
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: backgroundColor },
                textColor,
            },
            width: chartContainerRef.current.clientWidth,
            height: 500,
            grid: {
                vertLines: { color: '#334155' },
                horzLines: { color: '#334155' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const newSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        seriesRef.current = newSeries;
        chartRef.current = chart;

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [backgroundColor, textColor]);

    useEffect(() => {
        if (seriesRef.current && data.length > 0) {
            // Lightweight charts expects unique, sorted time.
            // We assume data coming in is correct, but for a real app we might need to dedupe.
            try {
                seriesRef.current.setData(data as any);
            } catch (e) {
                console.error("Error setting chart data", e);
            }
        }
    }, [data]);

    return (
        <div ref={chartContainerRef} className="w-full h-[500px] rounded-lg overflow-hidden shadow-lg border border-slate-700" />
    );
};
