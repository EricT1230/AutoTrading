# 🚀 AutoTrading Bot 快速啟動指南

> 5分鐘內啟動你的專業加密貨幣自動交易系統！

## 📋 啟動檢查清單

- [x] ✅ Python 3.11+ 已安裝
- [x] ✅ 專案環境已設置
- [x] ✅ 核心模組已完成
- [ ] 🔧 OKX API 金鑰設置
- [ ] 🌐 Web UI 啟動測試

---

## 🎯 三種啟動方式

### 1️⃣ 快速啟動 Web UI（推薦）

```bash
# 進入專案目錄
cd trading-bot

# 啟動 Web 介面
python start.py web

# 或直接使用 Web UI 啟動器
python run_web_ui.py
```

**Web 介面**: http://localhost:8501

### 2️⃣ 命令行工具

```bash
# 環境測試
python start.py test

# 策略演示
python start.py demo

# 查看專案結構
python start.py structure

# 查看開發步驟
python start.py steps
```

### 3️⃣ Jupyter 研究環境

```bash
# 啟動 Jupyter
jupyter notebook notebooks/01_strategy_exploration.ipynb

# 或使用 Jupyter Lab
jupyter lab
```

---

## 🔧 首次設置

### Step 1: API 配置

1. **註冊 OKX 帳戶**
   - 訪問 [OKX.com](https://okx.com) 註冊帳戶
   - 完成 KYC 認證（如需實盤交易）

2. **創建 API 金鑰**
   ```
   登入 OKX → API → 創建 API Key
   ✅ 現貨交易權限
   ✅ 讀取權限  
   ❌ 提幣權限（安全考慮）
   ```

3. **配置環境變數**
   ```bash
   # 複製配置範本
   cp .env.example .env
   
   # 編輯 .env 文件，填入真實 API 資訊
   # BINANCE_API_KEY=你的OKX_API_金鑰
   # BINANCE_SECRET_KEY=你的OKX_密鑰  
   # OKX_PASSPHRASE=你的OKX_密語
   ```

### Step 2: 啟動測試

```bash
# 1. 測試環境
python start.py test

# 2. 啟動 Web UI
python start.py web

# 3. 在瀏覽器中訪問 http://localhost:8501
```

### Step 3: 連接 API

1. 在 Web UI 左側邊欄輸入 API 資訊
2. ✅ 勾選「使用測試網」（建議）
3. 點擊「🔌 連接 OKX」
4. 看到 ✅ 連接成功提示

---

## 📊 功能概覽

### 🎯 交易功能
- **自動策略**: ICT NY FVG 自動交易策略
- **手動交易**: 快速下單和平倉功能
- **風險控制**: 智能倉位管理和止損

### 📈 圖表分析
- **TradingView**: 嵌入式專業圖表
- **技術指標**: RSI, MACD, 移動平均線
- **實時更新**: WebSocket 即時價格

### 💼 投資組合
- **資產總覽**: 總資產、盈虧、保證金
- **持倉管理**: 當前持倉一目了然
- **交易歷史**: 詳細交易記錄

### 📊 績效監控
- **實時監控**: 策略狀態、系統健康
- **風險管理**: 風險使用率、預警通知
- **績效分析**: 收益率、夏普比率、回撤

---

## 💡 使用技巧

### 新手建議

1. **先用測試網**
   - ✅ 使用 OKX 測試網熟悉操作
   - 🔄 測試所有功能
   - 📚 閱讀策略邏輯

2. **小額開始**
   - 💰 初期使用小額資金
   - ⚖️ 設置保守風險參數
   - 📊 觀察策略表現

3. **持續學習**
   - 📖 研讀 ICT/SMC 理論
   - 📈 分析歷史交易
   - 🔧 優化策略參數

### 進階設置

```yaml
# config/config.yaml 策略調整
strategy:
  parameters:
    session_start: "09:30"     # 調整交易時段
    session_end: "11:30"
    min_fvg_size_pips: 15     # 提高 FVG 標準
    risk_reward_ratio: 2.5     # 降低風險收益比

trading:
  risk_per_trade: 0.005      # 降低單筆風險到 0.5%
  max_daily_loss: 0.03       # 降低每日最大虧損到 3%
```

---

## ⚠️ 重要提醒

### 安全須知
- 🔐 **API 安全**: 不要分享 API 金鑰
- 🏠 **IP 限制**: 設置 API IP 白名單
- 💰 **資金安全**: 不要將全部資金用於自動交易

### 風險控制
- 📉 **止損設置**: 始終設置合理止損
- ⚖️ **倉位控制**: 不要超過風險承受能力
- 📊 **策略監控**: 定期檢查策略表現

### 技術支援
- 🐛 **Bug 回報**: GitHub Issues
- 📚 **文檔**: 查看 `WEB_UI_README.md`
- 💬 **討論**: 專案討論區

---

## 🚧 故障排除

### 常見問題

**1. Web UI 無法啟動**
```bash
# 檢查依賴套件
pip install -r requirements.txt

# 重新啟動
python run_web_ui.py
```

**2. API 連接失敗**
```bash
# 檢查 API 資訊格式
# 確認網路連接
# 檢查 OKX 服務狀態
```

**3. 圖表顯示異常**
```bash
# 更新 plotly
pip install --upgrade plotly

# 清除瀏覽器快取
# 重新整理頁面
```

### 聯絡支援

- 📧 Email: support@autotrading.bot
- 💬 GitHub: 提交 Issue
- 📱 Telegram: @AutoTradingSupport

---

## 🎉 恭喜！

如果你已成功啟動 Web UI 並連接到 OKX API，恭喜你！🎊

你現在擁有了一個功能完整的專業加密貨幣自動交易系統！

### 下一步建議：
1. 📚 熟悉 ICT/SMC 交易理論
2. 🔬 在測試網上測試策略
3. 📊 分析歷史交易數據
4. ⚙️ 根據表現調整參數
5. 💰 小額實盤驗證

**祝你交易順利，獲利豐厚！** 🚀💰📈