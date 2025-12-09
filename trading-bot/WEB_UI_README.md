# AutoTrading Bot Web UI 使用指南

> 專業的加密貨幣自動交易 Web 介面，整合 TradingView 圖表、OKX API 和實時數據監控

## 🚀 快速啟動

### 1. 安裝依賴套件

```bash
# 確保在 trading-bot 目錄下
cd trading-bot

# 安裝 Web UI 相關套件
pip install streamlit plotly dash flask flask-socketio websocket-client

# 或安裝完整依賴
pip install -r requirements.txt
```

### 2. 啟動 Web UI

```bash
# 方法 1: 使用啟動腳本（推薦）
python run_web_ui.py

# 方法 2: 直接使用 streamlit
streamlit run web/main_app.py --server.port 8501
```

### 3. 訪問應用

- 🌐 **Web 介面**: http://localhost:8501
- 📱 **手機訪問**: http://你的電腦IP:8501

---

## ✨ 功能特色

### 📈 專業交易圖表
- **TradingView 整合**: 嵌入式 TradingView 專業圖表
- **自定義 K 線**: 基於 Plotly 的互動式圖表
- **技術指標**: RSI、MACD、移動平均線、布林帶
- **多時間框架**: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d

### 🔌 OKX API 整合
- **實時行情**: WebSocket 即時價格更新
- **訂單管理**: 市價單、限價單下單功能
- **帳戶監控**: 餘額、持倉、交易歷史查詢
- **風險控制**: 自動風險管理和倉位控制

### 🤖 ICT 策略系統
- **Smart Money Concepts**: 基於 ICT 理論的自動交易
- **Fair Value Gap**: FVG 區域自動識別
- **Liquidity Sweep**: 流動性掃蕩偵測
- **NY Session**: 紐約交易時段專用策略

### 📊 交易儀表板
- **投資組合概覽**: 總資產、未實現盈虧、保證金比例
- **持倉管理**: 即時持倉狀況、一鍵平倉功能
- **績效分析**: 收益曲線、回撤分析、風險指標
- **交易歷史**: 詳細交易記錄和統計分析

### 📡 實時監控
- **即時數據流**: WebSocket 實時價格和訂單簿
- **系統監控**: API 延遲、策略狀態、錯誤追蹤
- **智能通知**: 交易訊號、風險警告、系統狀態

---

## 🎛️ 使用說明

### 第一次使用

1. **API 配置**
   - 在左側邊欄「API 設定」中輸入 OKX API 資訊
   - 建議先使用測試網進行練習
   - 點擊「連接 OKX」建立 API 連接

2. **交易設定**
   - 選擇監控的交易對（BTC/USDT, ETH/USDT 等）
   - 設定 K 線時間框架
   - 調整風險參數（單筆風險、最大持倉）

3. **策略啟動**
   - 確認 API 連接成功
   - 點擊「啟動交易」開始自動策略
   - 在「實時監控」頁面查看策略狀態

### 主要功能頁面

#### 📈 交易視圖
- **TradingView 圖表**: 專業圖表分析
- **技術指標開關**: 自定義顯示的指標
- **快速交易**: 手動下單功能

#### 💼 投資組合
- **帳戶總覽**: 資金狀況和盈虧統計
- **持倉管理**: 當前持倉和快速平倉
- **交易歷史**: 過往交易記錄

#### 📊 績效分析
- **收益統計**: 總收益率、年化收益、夏普比率
- **風險指標**: 最大回撤、波動率分析
- **對比分析**: 與基準指標對比

#### ⚖️ 風險管理
- **風險參數**: 動態調整風險控制參數
- **使用情況**: 實時風險使用率監控
- **預警系統**: 風險超標自動警告

#### 📡 實時監控
- **即時行情**: 最新價格和成交數據
- **系統狀態**: API 狀態、策略運行時間
- **通知中心**: 交易通知和系統訊息

---

## ⚙️ 高級配置

### 自定義設定

編輯 `config/config.yaml` 來調整策略參數：

```yaml
# 策略參數
strategy:
  name: "ICT_NY_FVG"
  parameters:
    session_start: "09:30"  # NY 開盤時間
    session_end: "11:30"    # NY 結束時間
    min_fvg_size_pips: 10   # 最小 FVG 大小
    risk_reward_ratio: 3.0   # 風險收益比 1:3

# 風險控制
trading:
  risk_per_trade: 0.01    # 1% 每筆風險
  max_daily_loss: 0.05    # 5% 日最大虧損
  max_positions: 3        # 最大持倉數
```

### 環境變數設定

複製 `.env.example` 為 `.env` 並填入真實資訊：

```bash
# OKX API 設定
BINANCE_API_KEY=your_okx_api_key
BINANCE_SECRET_KEY=your_okx_secret_key  
OKX_PASSPHRASE=your_okx_passphrase
BINANCE_TESTNET=True

# 通知設定
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 🔧 開發與自定義

### 添加新的技術指標

在 `web/components/` 目錄下創建自定義組件：

```python
# web/components/custom_indicators.py
def custom_rsi_component(df, period=14):
    """自定義 RSI 指標組件"""
    # 計算 RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # 繪製圖表
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=rsi, name='RSI'))
    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    
    return fig
```

### 新增交易所支援

參考 `core/exchange_okx.py` 實作新的交易所：

```python
# core/exchange_binance.py
class BinanceExchange(ExchangeBase):
    def __init__(self, config: Dict):
        super().__init__(config)
        # Binance 特定實作
```

### 自定義交易策略

繼承 `StrategyBase` 創建新策略：

```python
# core/strategy_custom.py
class CustomStrategy(StrategyBase):
    def on_bar(self, bar: BarData, history: pd.DataFrame):
        # 自定義策略邏輯
        return trading_signal
```

---

## 🐛 故障排除

### 常見問題

**1. 無法連接 OKX API**
```bash
# 檢查 API 金鑰格式
# 確認 API 權限設定（現貨交易、讀取權限）
# 檢查 IP 白名單設定
```

**2. 圖表無法顯示**
```bash
# 重新安裝 plotly
pip uninstall plotly
pip install plotly>=5.17.0

# 清除瀏覽器快取
# 重新啟動 Streamlit
```

**3. 實時數據更新慢**
```bash
# 檢查網路連接
# 確認 WebSocket 連接狀態
# 重啟應用程式
```

### 日誌查看

```bash
# 查看應用日誌
tail -f logs/trading_bot.log

# 查看錯誤日誌  
tail -f logs/error.log
```

### 效能優化

```python
# 在 streamlit 配置中調整
# .streamlit/config.toml
[server]
maxUploadSize = 1000
maxMessageSize = 1000

[browser]
gatherUsageStats = false
```

---

## 📞 技術支援

### 文檔資源
- 📚 **用戶手冊**: 本文檔
- 🔗 **API 文檔**: [OKX API](https://www.okx.com/docs-v5/en/)
- 📊 **TradingView**: [TradingView Widgets](https://www.tradingview.com/widget/)

### 社群支援
- 💬 **討論區**: GitHub Issues
- 📧 **技術支援**: support@autotrading.bot
- 📱 **Telegram**: @AutoTradingBotSupport

---

## ⚠️ 風險聲明

1. **投資風險**: 加密貨幣交易具有極高風險，可能導致全部資金損失
2. **策略風險**: 任何交易策略都不能保證盈利，過往表現不代表未來結果
3. **技術風險**: 軟體可能存在 bug 或故障，請充分測試後再使用實盤
4. **法律風險**: 請確保在您的司法管轄區內合法使用自動交易軟體

**建議**:
- 先在測試網環境熟悉操作
- 使用小額資金進行實盤測試
- 設定合理的風險控制參數
- 定期監控交易狀況
- 不要投入超過可承受損失的資金

---

## 🎯 路線圖

### v1.1 (規劃中)
- [ ] 多交易所支援 (Binance, Bybit)
- [ ] 更多技術指標
- [ ] 移動端響應式設計
- [ ] 策略回測功能

### v1.2 (未來)
- [ ] 機器學習策略優化
- [ ] 社交交易功能
- [ ] 多語言支援
- [ ] 雲端部署選項

---

**祝您交易順利！** 🚀📈💰