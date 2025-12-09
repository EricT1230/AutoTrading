"""
交易指標儀表板組件

提供交易相關的各種指標、圖表和監控面板
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time


class TradingDashboard:
    """交易儀表板類別"""
    
    def __init__(self):
        self.metrics_history = []
        self.trades_data = []
        self.performance_data = {}
        
    def render_account_overview(self, account_data: Dict):
        """渲染帳戶總覽"""
        st.subheader("💰 帳戶總覽")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            balance = account_data.get('total_balance', 0)
            balance_change = account_data.get('balance_change_24h', 0)
            st.metric(
                "帳戶餘額",
                f"${balance:,.2f}",
                f"{balance_change:+.2f}",
                delta_color="normal"
            )
            
        with col2:
            equity = account_data.get('equity', 0)
            equity_change = account_data.get('equity_change_24h', 0)
            st.metric(
                "淨資產",
                f"${equity:,.2f}",
                f"{equity_change:+.2f}%",
                delta_color="normal"
            )
            
        with col3:
            pnl = account_data.get('unrealized_pnl', 0)
            pnl_pct = account_data.get('unrealized_pnl_pct', 0)
            st.metric(
                "未實現盈虧",
                f"${pnl:+,.2f}",
                f"{pnl_pct:+.2f}%",
                delta_color="normal"
            )
            
        with col4:
            margin_ratio = account_data.get('margin_ratio', 0)
            st.metric(
                "保證金比例",
                f"{margin_ratio:.1f}%",
                help="已用保證金 / 可用保證金"
            )
    
    def render_positions_table(self, positions: List[Dict]):
        """渲染持倉表格"""
        st.subheader("📋 當前持倉")
        
        if not positions:
            st.info("目前沒有持倉")
            return
            
        # 準備表格數據
        df_data = []
        for pos in positions:
            df_data.append({
                '交易對': pos.get('symbol', 'N/A'),
                '方向': '多頭' if pos.get('side') == 'long' else '空頭',
                '數量': f"{pos.get('size', 0):,.4f}",
                '進場價': f"${pos.get('entry_price', 0):,.2f}",
                '標記價': f"${pos.get('mark_price', 0):,.2f}",
                '未實現盈虧': f"${pos.get('unrealized_pnl', 0):+,.2f}",
                '盈虧率': f"{pos.get('unrealized_pnl_pct', 0):+.2f}%",
                '保證金': f"${pos.get('margin', 0):,.2f}",
                '操作': '平倉'
            })
        
        df = pd.DataFrame(df_data)
        
        # 顯示數據框（移除按鈕功能以避免版本問題）
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # 添加平倉操作按鈕
        if len(positions) > 0:
            st.subheader("快速操作")
            for i, pos in enumerate(positions):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{pos.get('symbol', 'N/A')}** - {pos.get('side', 'Unknown')}")
                with col2:
                    if st.button(f"平倉", key=f"close_{i}"):
                        st.info(f"平倉功能開發中 - {pos.get('symbol', 'N/A')}")
        
        # 總計行
        if positions:
            total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            total_margin = sum(pos.get('margin', 0) for pos in positions)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("總未實現盈虧", f"${total_pnl:+,.2f}")
            with col2:
                st.metric("總保證金", f"${total_margin:,.2f}")
            with col3:
                st.metric("持倉數量", len(positions))
    
    def render_trading_history(self, trades: List[Dict], limit: int = 50):
        """渲染交易歷史"""
        st.subheader("📈 交易歷史")
        
        # 篩選選項
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol_filter = st.selectbox(
                "交易對篩選",
                ["全部"] + list(set(trade.get('symbol', 'N/A') for trade in trades)),
                key="history_symbol_filter"
            )
        with col2:
            side_filter = st.selectbox(
                "方向篩選", 
                ["全部", "多頭", "空頭"],
                key="history_side_filter"
            )
        with col3:
            date_range = st.date_input(
                "日期範圍",
                value=(datetime.now() - timedelta(days=7), datetime.now()),
                key="history_date_range"
            )
        
        # 應用篩選
        filtered_trades = trades
        if symbol_filter != "全部":
            filtered_trades = [t for t in filtered_trades if t.get('symbol') == symbol_filter]
        if side_filter != "全部":
            side_value = 'long' if side_filter == '多頭' else 'short'
            filtered_trades = [t for t in filtered_trades if t.get('side') == side_value]
            
        # 準備表格數據
        df_data = []
        for trade in filtered_trades[:limit]:
            df_data.append({
                '時間': trade.get('close_time', 'N/A'),
                '交易對': trade.get('symbol', 'N/A'),
                '方向': '多頭' if trade.get('side') == 'long' else '空頭',
                '數量': f"{trade.get('quantity', 0):,.4f}",
                '進場價': f"${trade.get('entry_price', 0):,.2f}",
                '出場價': f"${trade.get('exit_price', 0):,.2f}",
                '已實現盈虧': f"${trade.get('realized_pnl', 0):+,.2f}",
                '手續費': f"${trade.get('commission', 0):,.2f}",
                '持倉時間': trade.get('duration', 'N/A')
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 分頁
            if len(filtered_trades) > limit:
                st.info(f"顯示最近 {limit} 筆交易，總共 {len(filtered_trades)} 筆")
        else:
            st.info("沒有符合條件的交易記錄")
    
    def render_performance_metrics(self, performance: Dict):
        """渲染績效指標"""
        st.subheader("📊 績效分析")
        
        # 主要指標
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pnl = performance.get('total_pnl', 0)
            st.metric("總盈虧", f"${total_pnl:+,.2f}")
            
        with col2:
            win_rate = performance.get('win_rate', 0)
            st.metric("勝率", f"{win_rate:.1f}%")
            
        with col3:
            profit_factor = performance.get('profit_factor', 0)
            st.metric("獲利因子", f"{profit_factor:.2f}")
            
        with col4:
            max_drawdown = performance.get('max_drawdown', 0)
            st.metric("最大回撤", f"{max_drawdown:.2f}%")
        
        # 詳細指標
        st.subheader("詳細績效指標")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**交易統計**")
            metrics_1 = {
                "總交易筆數": performance.get('total_trades', 0),
                "獲利交易": performance.get('winning_trades', 0),
                "虧損交易": performance.get('losing_trades', 0),
                "平均獲利": f"${performance.get('avg_win', 0):,.2f}",
                "平均虧損": f"${performance.get('avg_loss', 0):,.2f}",
                "最大單筆獲利": f"${performance.get('largest_win', 0):,.2f}",
                "最大單筆虧損": f"${performance.get('largest_loss', 0):,.2f}"
            }
            for key, value in metrics_1.items():
                st.write(f"- **{key}**: {value}")
        
        with col2:
            st.write("**風險指標**")
            metrics_2 = {
                "夏普比率": f"{performance.get('sharpe_ratio', 0):.2f}",
                "索提諾比率": f"{performance.get('sortino_ratio', 0):.2f}",
                "卡爾瑪比率": f"{performance.get('calmar_ratio', 0):.2f}",
                "波動率": f"{performance.get('volatility', 0):.2f}%",
                "平均持倉時間": performance.get('avg_hold_time', 'N/A'),
                "最長連勝": f"{performance.get('max_consecutive_wins', 0)} 筆",
                "最長連敗": f"{performance.get('max_consecutive_losses', 0)} 筆"
            }
            for key, value in metrics_2.items():
                st.write(f"- **{key}**: {value}")
    
    def render_equity_curve(self, equity_data: List[Dict]):
        """渲染資金曲線圖"""
        st.subheader("📈 資金曲線")
        
        if not equity_data:
            st.info("沒有資金曲線數據")
            return
            
        # 準備數據
        df = pd.DataFrame(equity_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 建立圖表
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('資金曲線', '回撤'),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )
        
        # 資金曲線
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['equity'],
                mode='lines',
                name='淨資產',
                line=dict(color='#2E86AB', width=2)
            ),
            row=1, col=1
        )
        
        # 回撤
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['drawdown'],
                mode='lines',
                name='回撤',
                line=dict(color='#E63946', width=2),
                fill='tonexty'
            ),
            row=2, col=1
        )
        
        # 更新布局
        fig.update_layout(
            height=500,
            showlegend=False,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        fig.update_xaxes(title_text="時間", row=2, col=1)
        fig.update_yaxes(title_text="金額 ($)", row=1, col=1)
        fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_pnl_distribution(self, trades: List[Dict]):
        """渲染盈虧分佈圖"""
        st.subheader("📊 盈虧分佈")
        
        if not trades:
            st.info("沒有交易數據")
            return
        
        # 提取盈虧數據
        pnl_data = [trade.get('realized_pnl', 0) for trade in trades]
        
        # 建立直方圖
        fig = px.histogram(
            x=pnl_data,
            nbins=30,
            title="盈虧分佈直方圖",
            labels={'x': '盈虧 ($)', 'y': '交易次數'},
            color_discrete_sequence=['#2E86AB']
        )
        
        # 添加統計線
        mean_pnl = np.mean(pnl_data)
        fig.add_vline(
            x=mean_pnl, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"平均: ${mean_pnl:.2f}"
        )
        fig.add_vline(
            x=0, 
            line_dash="solid", 
            line_color="gray",
            annotation_text="損益平衡"
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 統計摘要
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("獲利交易", len([p for p in pnl_data if p > 0]))
        with col2:
            st.metric("虧損交易", len([p for p in pnl_data if p < 0]))
        with col3:
            st.metric("平手交易", len([p for p in pnl_data if p == 0]))
    
    def render_monthly_returns(self, returns_data: Dict):
        """渲染月度收益熱力圖"""
        st.subheader("🗓️ 月度收益")
        
        if not returns_data:
            st.info("沒有月度收益數據")
            return
        
        # 準備數據矩陣
        months = ['1月', '2月', '3月', '4月', '5月', '6月',
                 '7月', '8月', '9月', '10月', '11月', '12月']
        years = sorted(returns_data.keys())
        
        # 建立矩陣
        matrix = []
        for year in years:
            row = []
            for month in range(1, 13):
                value = returns_data.get(year, {}).get(month, None)
                row.append(value if value is not None else np.nan)
            matrix.append(row)
        
        # 建立熱力圖
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=months,
            y=years,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f'{val:.1f}%' if not np.isnan(val) else 'N/A' 
                  for val in row] for row in matrix],
            texttemplate='%{text}',
            textfont={'size': 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title='月度收益率 (%)',
            height=300,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_risk_metrics(self, risk_data: Dict):
        """渲染風險指標"""
        st.subheader("⚖️ 風險監控")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**當日風險使用情況**")
            
            # 風險使用率進度條
            risk_used = risk_data.get('daily_risk_used', 0)
            risk_limit = risk_data.get('daily_risk_limit', 5.0)
            risk_pct = (risk_used / risk_limit) * 100
            
            # 顏色根據使用率調整
            if risk_pct < 50:
                color = "green"
            elif risk_pct < 80:
                color = "orange"
            else:
                color = "red"
            
            st.metric("已用風險", f"{risk_used:.2f}%", f"/ {risk_limit:.1f}%")
            st.progress(min(risk_pct / 100, 1.0))
            
            # 其他風險指標
            st.write(f"**剩餘可用風險**: {max(0, risk_limit - risk_used):.2f}%")
            st.write(f"**當日交易次數**: {risk_data.get('daily_trades', 0)}")
            st.write(f"**最大持倉數**: {risk_data.get('max_positions', 0)}")
        
        with col2:
            st.write("**風險分散情況**")
            
            # 持倉分散度
            positions_by_symbol = risk_data.get('positions_by_symbol', {})
            if positions_by_symbol:
                symbols = list(positions_by_symbol.keys())
                sizes = list(positions_by_symbol.values())
                
                fig = px.pie(
                    values=sizes,
                    names=symbols,
                    title="持倉分散度"
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=50, b=0),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("目前沒有持倉")
        
        # 風險警告
        warnings = []
        if risk_pct > 80:
            warnings.append("⚠️ 當日風險使用率過高")
        if risk_data.get('current_positions', 0) >= risk_data.get('max_positions', 3):
            warnings.append("⚠️ 已達最大持倉數限制")
        if risk_data.get('margin_ratio', 0) > 80:
            warnings.append("⚠️ 保證金比例偏高")
            
        if warnings:
            st.warning("\n".join(warnings))


# 全域儀表板實例
dashboard = TradingDashboard()


def render_complete_dashboard():
    """渲染完整儀表板"""
    
    # 模擬數據
    account_data = {
        'total_balance': 10500.50,
        'balance_change_24h': 150.25,
        'equity': 10750.30,
        'equity_change_24h': 2.4,
        'unrealized_pnl': 249.80,
        'unrealized_pnl_pct': 2.4,
        'margin_ratio': 25.3
    }
    
    positions = [
        {
            'symbol': 'BTC/USDT',
            'side': 'long',
            'size': 0.1,
            'entry_price': 45200,
            'mark_price': 45350,
            'unrealized_pnl': 15.0,
            'unrealized_pnl_pct': 0.33,
            'margin': 1500
        }
    ]
    
    trades = [
        {
            'close_time': '2024-01-01 10:30:00',
            'symbol': 'BTC/USDT',
            'side': 'long',
            'quantity': 0.1,
            'entry_price': 44800,
            'exit_price': 45100,
            'realized_pnl': 30.0,
            'commission': 0.9,
            'duration': '2h 15m'
        }
    ]
    
    performance = {
        'total_pnl': 485.50,
        'win_rate': 65.2,
        'profit_factor': 1.8,
        'max_drawdown': 3.2,
        'total_trades': 45,
        'winning_trades': 29,
        'losing_trades': 16,
        'avg_win': 45.20,
        'avg_loss': -25.80,
        'sharpe_ratio': 1.65,
        'sortino_ratio': 2.1,
        'volatility': 15.2
    }
    
    risk_data = {
        'daily_risk_used': 2.1,
        'daily_risk_limit': 5.0,
        'daily_trades': 3,
        'max_positions': 3,
        'current_positions': 1,
        'margin_ratio': 25.3,
        'positions_by_symbol': {'BTC/USDT': 60, 'ETH/USDT': 40}
    }
    
    # 渲染各個組件
    dashboard.render_account_overview(account_data)
    st.divider()
    
    dashboard.render_positions_table(positions)
    st.divider()
    
    dashboard.render_performance_metrics(performance)
    st.divider()
    
    dashboard.render_risk_metrics(risk_data)


if __name__ == "__main__":
    st.title("交易儀表板測試")
    render_complete_dashboard()