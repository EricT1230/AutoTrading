# 自動化交易策略機器人

> 基於 ICT/SMC 策略的加密貨幣自動交易系統

## 專案特色

- 🎯 **模組化設計**：策略、交易所、回測引擎完全解耦
- 📊 **完整回測**：支援歷史數據回測與策略驗證
- 🔄 **多階段開發**：從原型 → 回測 → 模擬 → 實盤
- 🛡️ **風控優先**：內建風險管理與資金控制
- 📱 **智能通知**：Telegram/Discord 即時通知
- ☁️ **雲端部署**：支援 VPS 24/7 運行

## 快速開始

```bash
# 1. 進入專案目錄
cd trading-bot

# 2. 啟動虛擬環境
.\trading_env\Scripts\activate  # Windows
# source trading_env/bin/activate  # Linux/Mac

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 API 金鑰

# 5. 運行回測
python backtest/backtest_runner.py

# 6. 啟動模擬交易
python live/paper_runner.py

# 7. 實盤交易（謹慎使用）
python live/bot_runner.py
```

## 策略說明

### ICT NY FVG 策略
- **時間框架**：5分鐘
- **交易時段**：紐約開盤時間 (09:30-11:30)
- **核心邏輯**：Liquidity Sweep + Fair Value Gap
- **風險收益比**：1:3

## 專案結構

```
trading-bot/
├── README.md                 # 專案說明
├── requirements.txt          # Python 套件清單
├── .env.example             # 環境變數範本
├── config/                  # 配置文件
├── data/                    # 歷史數據
├── notebooks/               # Jupyter 研究筆記
├── core/                    # 核心邏輯模組
├── backtest/                # 回測引擎
├── live/                    # 實時交易
├── scripts/                 # 工具腳本
└── tests/                   # 測試文件
```

## 風險警告

⚠️ **投資有風險，交易需謹慎**
- 本系統僅供學習研究使用
- 實盤交易前請充分測試
- 建議先用少量資金驗證
- 過往績效不代表未來收益

## 開發狀態

- [x] ✅ 專案架構設計
- [ ] 🔄 策略核心邏輯
- [ ] 📊 回測引擎開發
- [ ] 🎮 模擬交易系統
- [ ] 🔌 交易所 API 整合
- [ ] 🚀 VPS 部署配置

## 聯絡方式

如有問題或建議，歡迎提出 Issue 或 Pull Request。