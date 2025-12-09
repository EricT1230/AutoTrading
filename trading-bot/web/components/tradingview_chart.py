"""
TradingView 圖表整合組件

提供嵌入式 TradingView 圖表功能，支援自定義指標和策略標記
"""

import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict, List, Optional


def tradingview_chart(
    symbol: str = "BTCUSDT",
    exchange: str = "OKX",
    interval: str = "5",
    theme: str = "dark",
    width: int = 800,
    height: int = 600,
    timezone: str = "Etc/UTC",
    locale: str = "en",
    toolbar_bg: str = "#f1f3f6",
    enable_publishing: bool = False,
    withdateranges: bool = True,
    range: str = "1D",
    hide_side_toolbar: bool = False,
    allow_symbol_change: bool = True,
    save_image: bool = False,
    container_id: str = "tradingview_chart",
    studies: List[str] = None,
    **kwargs
) -> None:
    """
    嵌入 TradingView 圖表
    
    Args:
        symbol: 交易對符號
        exchange: 交易所名稱
        interval: 時間間隔 (1, 3, 5, 15, 30, 60, 240, 1D)
        theme: 主題 (light/dark)
        width: 圖表寬度
        height: 圖表高度
        timezone: 時區
        locale: 語言
        studies: 技術指標列表
        **kwargs: 其他參數
    """
    
    # 默認技術指標
    if studies is None:
        studies = [
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies",
            "MACD@tv-basicstudies"
        ]
    
    # TradingView Widget 配置
    config = {
        "width": width,
        "height": height,
        "symbol": f"{exchange.upper()}:{symbol}",
        "interval": interval,
        "timezone": timezone,
        "theme": theme,
        "style": "1",
        "locale": locale,
        "toolbar_bg": toolbar_bg,
        "enable_publishing": enable_publishing,
        "withdateranges": withdateranges,
        "range": range,
        "hide_side_toolbar": hide_side_toolbar,
        "allow_symbol_change": allow_symbol_change,
        "save_image": save_image,
        "studies": studies,
        "container_id": container_id,
        **kwargs
    }
    
    # TradingView HTML - 修正版本
    tradingview_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div id="{container_id}" style="height:calc(100% - 32px);width:100%;"></div>
      <div class="tradingview-widget-copyright" style="text-align: center; margin-top: 5px;">
        <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank" style="color: #999; font-size: 12px;">
          TradingView Charts
        </a>
      </div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js">
      {json.dumps(config)}
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    
    # 嵌入 HTML
    components.html(tradingview_html, height=height + 50, width=width)


def tradingview_ticker_tape(
    symbols: List[Dict] = None,
    show_symbol_logo: bool = True,
    color_theme: str = "dark",
    is_transparent: bool = False,
    width: str = "100%",
    height: int = 60
) -> None:
    """
    TradingView 股票行情跑馬燈
    
    Args:
        symbols: 顯示的符號列表
        show_symbol_logo: 是否顯示符號 logo
        color_theme: 顏色主題
        is_transparent: 是否透明背景
        width: 寬度
        height: 高度
    """
    
    if symbols is None:
        symbols = [
            {"proName": "OKX:BTCUSDT", "title": "Bitcoin"},
            {"proName": "OKX:ETHUSDT", "title": "Ethereum"},
            {"proName": "OKX:ADAUSDT", "title": "Cardano"},
            {"proName": "OKX:SOLUSDT", "title": "Solana"},
            {"proName": "OKX:DOTUSDT", "title": "Polkadot"}
        ]
    
    config = {
        "symbols": symbols,
        "showSymbolLogo": show_symbol_logo,
        "colorTheme": color_theme,
        "isTransparent": is_transparent,
        "width": width,
        "height": height,
        "locale": "en"
    }
    
    ticker_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="width:100%; height:{height}px;">
      <div class="tradingview-widget-container__widget" style="width:100%; height:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js">
      {json.dumps(config)}
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    
    components.html(ticker_html, height=height + 10)


def tradingview_market_overview(
    color_theme: str = "dark",
    width: str = "100%", 
    height: int = 400,
    tabs: List[Dict] = None
) -> None:
    """
    TradingView 市場概覽
    
    Args:
        color_theme: 顏色主題
        width: 寬度
        height: 高度
        tabs: 市場標籤
    """
    
    if tabs is None:
        tabs = [
            {
                "title": "Crypto",
                "symbols": [
                    {"s": "OKX:BTCUSDT", "d": "Bitcoin / Tether"},
                    {"s": "OKX:ETHUSDT", "d": "Ethereum / Tether"},
                    {"s": "OKX:ADAUSDT", "d": "Cardano / Tether"},
                    {"s": "OKX:SOLUSDT", "d": "Solana / Tether"},
                    {"s": "OKX:DOTUSDT", "d": "Polkadot / Tether"}
                ]
            }
        ]
    
    config = {
        "colorTheme": color_theme,
        "dateRange": "12M",
        "showChart": True,
        "locale": "en",
        "width": width,
        "height": height,
        "largeChartUrl": "",
        "isTransparent": False,
        "showSymbolLogo": True,
        "showFloatingTooltip": False,
        "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
        "plotLineColorFalling": "rgba(41, 98, 255, 1)",
        "gridLineColor": "rgba(42, 46, 57, 0)",
        "scaleFontColor": "rgba(134, 137, 147, 1)",
        "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
        "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
        "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
        "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
        "tabs": tabs
    }
    
    overview_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
      {{
        {json.dumps(config, indent=2)}
      }}
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    
    components.html(overview_html, height=height + 50)


def tradingview_economic_calendar(
    color_theme: str = "dark",
    width: str = "100%",
    height: int = 600,
    locale: str = "en"
) -> None:
    """
    TradingView 經濟日曆
    
    Args:
        color_theme: 顏色主題
        width: 寬度
        height: 高度
        locale: 語言
    """
    
    config = {
        "colorTheme": color_theme,
        "isTransparent": False,
        "width": width,
        "height": height,
        "locale": locale,
        "importanceFilter": "-1,0,1",
        "countryFilter": "us,eu,jp,gb,ch,au,ca,nz,cn"
    }
    
    calendar_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-economic-calendar.js" async>
      {{
        {json.dumps(config, indent=2)}
      }}
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    
    components.html(calendar_html, height=height + 50)


def create_custom_indicator(
    name: str,
    script: str,
    inputs: List[Dict] = None,
    plots: List[Dict] = None
) -> str:
    """
    建立自定義 Pine Script 指標
    
    Args:
        name: 指標名稱
        script: Pine Script 程式碼
        inputs: 輸入參數
        plots: 繪製設定
        
    Returns:
        指標 ID
    """
    
    # 這是一個示範，實際使用需要 TradingView 的 Pine Editor
    pine_script_template = f"""
    //@version=5
    indicator("{name}", overlay=true)
    
    // 輸入參數
    {chr(10).join([f"input.{inp['type']}(title='{inp['title']}', defval={inp['default']})" for inp in (inputs or [])]) if inputs else ""}
    
    // 主要邏輯
    {script}
    
    // 繪製
    {chr(10).join([f"plot({plot['series']}, title='{plot['title']}', color={plot.get('color', 'color.blue')})" for plot in (plots or [])]) if plots else ""}
    """
    
    return pine_script_template


# ICT 策略專用指標
def ict_fvg_indicator() -> str:
    """ICT Fair Value Gap 指標"""
    return create_custom_indicator(
        name="ICT Fair Value Gap",
        script="""
        // FVG 偵測邏輯
        bullish_fvg = low[0] > high[2]
        bearish_fvg = high[0] < low[2]
        
        // 繪製 FVG 區域
        var box bullish_box = na
        var box bearish_box = na
        
        if bullish_fvg
            bullish_box := box.new(bar_index[2], high[2], bar_index, low[0], 
                                  bgcolor=color.new(color.green, 80), 
                                  border_color=color.green)
                                  
        if bearish_fvg
            bearish_box := box.new(bar_index[2], low[2], bar_index, high[0],
                                  bgcolor=color.new(color.red, 80),
                                  border_color=color.red)
        """,
        inputs=[
            {"type": "int", "title": "FVG Lookback", "default": 3}
        ],
        plots=[
            {"series": "bullish_fvg ? 1 : 0", "title": "Bullish FVG", "color": "color.green"},
            {"series": "bearish_fvg ? -1 : 0", "title": "Bearish FVG", "color": "color.red"}
        ]
    )


def ict_liquidity_sweep_indicator() -> str:
    """ICT Liquidity Sweep 指標"""
    return create_custom_indicator(
        name="ICT Liquidity Sweep",
        script="""
        // Liquidity Sweep 偵測
        lookback = input.int(5, title="Lookback Period")
        
        recent_high = ta.highest(high, lookback)[1]
        recent_low = ta.lowest(low, lookback)[1]
        
        sweep_high = high > recent_high and close < high
        sweep_low = low < recent_low and close > low
        
        // 標記 Sweep 點
        plotshape(sweep_high, style=shape.triangledown, location=location.abovebar, 
                 color=color.red, size=size.small, title="Sweep High")
        plotshape(sweep_low, style=shape.triangleup, location=location.belowbar,
                 color=color.green, size=size.small, title="Sweep Low")
        """,
        inputs=[
            {"type": "int", "title": "Lookback Period", "default": 5}
        ]
    )


# 使用示例
if __name__ == "__main__":
    # 這個檔案可以獨立測試
    st.title("TradingView 圖表測試")
    
    # 基本圖表
    st.subheader("基本 K 線圖")
    tradingview_chart(
        symbol="BTCUSDT",
        exchange="OKX",
        interval="5",
        theme="dark",
        height=500
    )
    
    # 行情跑馬燈
    st.subheader("行情跑馬燈")
    tradingview_ticker_tape()
    
    # 市場概覽
    st.subheader("市場概覽")
    tradingview_market_overview(height=300)