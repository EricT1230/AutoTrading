# 🚀 實時K線系統 - 每秒更新

## 📊 系統特色

### ⚡ 真正的實時性能
- **每秒更新**: 基於WebSocket的實時K線數據
- **毫秒級延遲**: 直連OKX WebSocket API
- **動態K線**: 當前K線隨價格變動實時更新
- **多時間週期**: 支援1m、3m、5m、15m、30m、1h等

### 🎯 專業交易功能
- **多交易對監控**: 同時追蹤BTC、ETH、SOL、ADA等
- **技術指標**: MA、MACD、RSI、布林帶實時計算
- **價格警報**: 突破、支撐阻力位提醒
- **量能分析**: 實時成交量變化追蹤

### 🔧 性能優化
- **智能快取**: 減少API調用，提升響應速度
- **內存管理**: 自動清理過期數據，防止內存洩漏
- **批量更新**: 高效處理多個圖表同時更新
- **背景任務**: 獨立線程處理WebSocket連接

## 🚀 快速開始

### 1. 環境準備
```bash
# 克隆專案
git clone <your-repo>
cd AutoTrading/trading-bot

# 安裝依賴
pip install -r requirements.txt
```

### 2. API設置
創建 `.env` 文件：
```env
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key  
OKX_PASSPHRASE=your_passphrase
OKX_TESTNET=true
```

### 3. 啟動系統
```bash
# 方法1: 使用專用啟動腳本
python run_realtime_kline.py

# 方法2: 直接運行Streamlit
streamlit run web/main_app.py

# 方法3: 使用現有啟動腳本
python run_web_ui.py
```

### 4. 訪問Web界面
瀏覽器打開: http://localhost:8501

點擊 **"⚡ 實時K線"** 標籤體驗每秒更新的K線圖！

## 📈 使用指南

### 實時K線功能
1. **選擇交易對**: 從下拉菜單選擇BTC/USDT、ETH/USDT等
2. **設置時間週期**: 選擇1m、5m、15m等不同週期
3. **調整圖表高度**: 使用滑桿調整適合的顯示高度
4. **啟用自動刷新**: 勾選自動刷新獲得實時更新

### 多交易對監控
- 同時監控4個熱門交易對
- 實時價格變動和漲跌幅
- 迷你圖表顯示價格趨勢
- 快速切換和對比分析

### 性能監控
- 查看快取使用情況
- 監控內存和CPU使用率
- 手動觸發性能優化
- 背景任務狀態檢查

## 🔧 技術架構

### WebSocket數據流
```
OKX WebSocket → RealtimeKlineEngine → DataFrame → Plotly圖表 → Streamlit顯示
```

### 關鍵組件
1. **RealtimeKlineEngine**: 核心實時數據引擎
2. **PerformanceOptimizer**: 性能優化系統
3. **StreamlitKlineComponent**: UI渲染組件
4. **MarketDataProvider**: 市場數據提供者

### 數據處理流程
1. 訂閱OKX WebSocket K線頻道
2. 實時接收並解析K線數據
3. 更新pandas DataFrame
4. 生成Plotly互動圖表
5. 在Streamlit中自動刷新顯示

## ⚡ 性能優化特性

### 智能快取機制
- 數據快取TTL: 5秒（可配置）
- 自動清理過期數據
- 批量更新減少重繪

### 內存管理
- 定期垃圾回收
- 限制DataFrame大小
- 清理無用的session state

### WebSocket優化
- 連接池管理
- 自動重連機制
- 數據壓縮傳輸

## 🛠️ 配置選項

### 更新頻率設定
```python
UPDATE_INTERVALS = {
    'ticker': 1,     # 行情數據：1秒更新
    'kline': 5,      # K線數據：5秒更新  
    'multiple': 2    # 多交易對：2秒更新
}
```

### 性能配置
```python
optimization_config = {
    'enable_compression': True,
    'cache_limit': 1000,
    'update_batch_size': 10,
    'memory_cleanup_interval': 30,
    'websocket_buffer_size': 1000
}
```

## 🐛 常見問題

### Q: K線圖不更新怎麼辦？
A: 
1. 檢查網路連接
2. 確認API密鑰正確
3. 查看性能監控面板
4. 手動點擊強制刷新

### Q: 內存使用過高？
A: 
1. 啟用自動清理功能
2. 減少監控的交易對數量
3. 降低圖表數據點數量
4. 定期重啟應用

### Q: WebSocket連接失敗？
A: 
1. 檢查防火牆設置
2. 確認OKX服務狀態
3. 嘗試切換網路環境
4. 查看日誌錯誤信息

## 📝 更新日誌

### v2.0 - 實時K線系統
- ✅ 新增WebSocket實時K線引擎
- ✅ 實現每秒更新的動態圖表
- ✅ 多交易對同時監控
- ✅ 性能優化系統
- ✅ 智能快取機制

### v1.0 - 基礎交易系統
- ✅ OKX API整合
- ✅ 基礎K線圖表
- ✅ 技術指標計算
- ✅ 風險管理系統

## 🤝 貢獻指南

歡迎提交Issue和Pull Request！

### 開發環境
```bash
# 安裝開發依賴
pip install -r requirements.txt
pip install pytest black flake8

# 運行測試
python -m pytest tests/

# 代碼格式化
black .
flake8 .
```

## 📄 授權協議

MIT License - 詳見 LICENSE 文件

## 📞 技術支持

如有問題請提交Issue或聯繫開發團隊

---

🚀 **立即體驗真正的實時K線交易系統！**