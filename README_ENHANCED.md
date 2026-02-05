# 增強版台股當沖選股系統
## Enhanced Taiwan Stock Day Trading System v2.0

完整整合技術面、籌碼面、多時間框架分析的專業當沖交易系統

---

## 目錄

1. [系統特色](#系統特色)
2. [模組說明](#模組說明)
3. [快速開始](#快速開始)
4. [詳細使用指南](#詳細使用指南)
5. [配置說明](#配置說明)
6. [重要提醒](#重要提醒)

---

## 系統特色

### 相比原版 tw-daytrade-picker 的重大改進

| 功能 | 原版 | 增強版 v2.0 | 改進說明 |
|------|------|-------------|----------|
| **風險控管** | ❌ 無 | ✅ 完整 | 停損停利、部位管理、最大回撤控制 |
| **市場環境判斷** | ❌ 無 | ✅ 完整 | 大盤趨勢、VIX 恐慌指標、外資動向 |
| **籌碼面分析** | ❌ 無 | ✅ 完整 | OBV 能量潮、三大法人買賣超 |
| **多時間框架** | ❌ 單一時間 | ✅ 多時間確認 | 避免單一週期誤判 |
| **回測系統** | ❌ 無 | ✅ 完整 | 驗證策略有效性 |
| **交易日誌** | ❌ 無 | ✅ 完整 | 記錄所有交易細節 |
| **技術指標** | ✅ RSI, Williams %R | ✅ 同左 + OBV | 增加籌碼指標 |

### 核心優勢

✅ **保命第一**: 完整風控機制，單筆最大風險 2%，單日最大虧損 5%  
✅ **市場環境過濾**: 大盤空頭時自動停止做多，避免逆勢操作  
✅ **籌碼主力追蹤**: OBV 判斷資金流向，三大法人一致性分析  
✅ **多重時間確認**: 日線看趨勢、15 分線找進場點，降低誤判  
✅ **完整回測驗證**: 用歷史資料驗證策略，避免紙上談兵  
✅ **交易日誌分析**: 記錄每筆交易細節，持續優化策略  

---

## 模組說明

### 1. risk_management.py - 風險控管模組

**功能:**
- 停損停利自動計算
- 部位大小控制（單筆不超過資金 10%）
- 單日虧損上限（觸及 5% 停止交易）
- 最大回撤控制（超過 15% 警告）
- 連續虧損冷靜機制（3 次虧損後冷靜 60 分鐘）

**使用範例:**
```python
from risk_management import RiskManager, RiskConfig

# 初始化（100 萬資金）
config = RiskConfig(max_daily_loss_pct=5.0)
risk_manager = RiskManager(config, initial_capital=1_000_000)

# 檢查是否可以開倉
can_open, reason = risk_manager.can_open_position()

# 計算建議持倉
quantity, stop_loss = risk_manager.calculate_position_size("2330", 500.0)

# 開倉
risk_manager.open_position("2330", 500.0, quantity, stop_loss, take_profit=530.0)

# 檢查是否需要出場
should_exit, reason = risk_manager.check_exit_signals("2330", current_price=485.0)
```

---

### 2. market_environment.py - 市場環境判斷模組

**功能:**
- 大盤趨勢分析（強勢多頭/多頭/盤整/空頭/強勢空頭）
- 市場情緒判斷（恐慌/中性/貪婪）
- VIX 恐慌指標監控
- 外資買賣超分析
- 自動決定是否適合做多/做空

**使用範例:**
```python
from market_environment import MarketAnalyzer

analyzer = MarketAnalyzer()

# 分析市場環境
env = analyzer.get_market_environment(
    index_df=大盤資料,
    vix_value=18.5,
    foreign_net_buy=3_000_000_000  # 外資買超 30 億
)

# 檢查是否適合做多
if env.can_long:
    print("市場環境適合做多")
else:
    print("市場環境不適合，建議觀望")

# 印出詳細分析
analyzer.print_environment(env)
```

---

### 3. enhanced_strategy.py - 增強版策略模組

**功能:**
- 技術面分析: RSI, Williams %R, 布林通道, 成交量
- 籌碼面分析: OBV 能量潮, 三大法人買賣超
- 綜合評分系統（0-100 分）
- 自動生成買賣訊號

**使用範例:**
```python
from enhanced_strategy import EnhancedStrategyC

strategy = EnhancedStrategyC()

# 準備法人資料
institutional = {
    'foreign': 5000,          # 外資買超 5000 張
    'investment_trust': 2000, # 投信買超 2000 張
    'dealer': -1000          # 自營賣超 1000 張
}

# 分析個股
analysis = strategy.analyze_stock(股票資料, institutional)

print(f"訊號: {analysis['signal']}")  # BUY/SELL/HOLD
print(f"分數: {analysis['score']}/100")
print(f"理由: {analysis['reasons']}")

# 印出詳細分析
strategy.print_analysis('2330', analysis)
```

---

### 4. multi_timeframe.py - 多時間框架分析模組

**功能:**
- 同時分析日線、小時線、15 分線
- 判斷時間框架一致性
- 長週期看趨勢、短週期找進場點
- 支撐壓力分析

**使用範例:**
```python
from multi_timeframe import MultiTimeFrameAnalyzer, TimeFrame

analyzer = MultiTimeFrameAnalyzer()

# 準備多時間資料
data_dict = {
    TimeFrame.DAILY: 日線資料,
    TimeFrame.HOUR_1: 小時線資料,
    TimeFrame.MINUTE_15: 15分線資料
}

# 綜合分析
result = analyzer.multi_timeframe_check(data_dict)

print(f"一致性: {result['alignment']}")  # bullish/bearish/mixed
print(f"信心指數: {result['confidence']}%")

# 獲取進場訊號
entry = analyzer.get_entry_signal(
    long_term_df=日線資料,
    short_term_df=分線資料,
    trend_alignment=result['alignment']
)
```

---

### 5. backtesting.py - 回測系統模組

**功能:**
- 使用歷史資料驗證策略
- 計算勝率、獲利因子、Sharpe Ratio
- 最大回撤分析
- 考慮手續費、稅金、滑價

**使用範例:**
```python
from backtesting import Backtester, BacktestConfig

# 配置
config = BacktestConfig(
    initial_capital=1_000_000,
    stop_loss_pct=3.0,
    take_profit_pct=6.0
)

# 定義策略
def my_strategy(df, index):
    # 你的策略邏輯
    if df['RSI'].iloc[index] < 30:
        return {'signal': 'BUY'}
    return {'signal': 'HOLD'}

# 執行回測
backtester = Backtester(config)
result = backtester.run(歷史資料, my_strategy)

# 查看結果
result.print_summary()
```

---

### 6. trade_logger.py - 交易日誌模組

**功能:**
- 記錄所有交易訊號、進場、出場
- 自動生成每日報表
- 匯出 CSV 供進一步分析
- 統計勝率、平均獲利

**使用範例:**
```python
from trade_logger import TradeLogger

logger = TradeLogger(log_dir="./logs/trades")

# 記錄訊號
logger.log_signal(
    symbol="2330",
    signal_type="BUY",
    price=500.0,
    score=85.0,
    technical={'rsi': 28.5},
    chip={'obv_signal': 'bullish'},
    market={'trend': '多頭'}
)

# 記錄進場
logger.log_entry(
    symbol="2330",
    price=501.0,
    quantity=2000,
    stop_loss=485.0,
    take_profit=531.0,
    ...
)

# 生成報表
logger.print_report()

# 匯出 CSV
logger.export_to_csv()
```

---

## 快速開始

### 安裝依賴

```bash
pip install pandas numpy pyyaml
```

### 基本使用流程

```python
from main_strategy import EnhancedDayTradingSystem

# 1. 初始化系統
system = EnhancedDayTradingSystem("config_enhanced.yml")

# 2. 分析市場環境
market_env = system.analyze_market_environment(
    index_df=大盤資料,
    vix_value=18.5,
    foreign_net_buy=3_000_000_000
)

# 3. 掃描股票
candidates = system.scan_and_filter_stocks(
    stocks_data={'2330': 台積電資料, '2454': 聯發科資料},
    institutional_data={'2330': 法人資料},
    market_env=market_env
)

# 4. 執行交易（如果有符合條件的股票）
for stock in candidates:
    system.execute_trade(
        symbol=stock['symbol'],
        analysis=stock,
        market_env=market_env
    )

# 5. 查看系統狀態
system.print_status()
```

---

## 詳細使用指南

### 完整交易流程

#### Step 1: 盤前準備

```python
# 1.1 分析大盤環境
market_env = system.analyze_market_environment(
    index_df=加權指數資料,
    vix_value=台灣VIX,
    foreign_net_buy=外資買賣超金額
)

# 1.2 檢查是否適合交易
if not market_env.can_long:
    print("市場環境不佳，今日休息")
    exit()

# 1.3 印出市場分析
system.market_analyzer.print_environment(market_env)
```

#### Step 2: 選股

```python
# 2.1 準備股票池（例如台灣 50 成分股）
stock_pool = ['2330', '2454', '2317', '2412', ...]

# 2.2 下載股票資料和法人資料
stocks_data = {}
institutional_data = {}

for symbol in stock_pool:
    stocks_data[symbol] = 下載股票資料(symbol)
    institutional_data[symbol] = 下載法人資料(symbol)

# 2.3 掃描並篩選
candidates = system.scan_and_filter_stocks(
    stocks_data=stocks_data,
    institutional_data=institutional_data,
    market_env=market_env
)

# 2.4 顯示候選股票（依分數排序）
for i, stock in enumerate(candidates[:10], 1):
    print(f"{i}. {stock['symbol']} - 分數: {stock['score']}")
    print(f"   {', '.join(stock['reasons'][:3])}")
```

#### Step 3: 進場

```python
# 對每檔候選股票
for stock in candidates:
    # 3.1 檢查風控
    can_open, reason = system.risk_manager.can_open_position()
    if not can_open:
        print(f"風控限制: {reason}")
        continue
    
    # 3.2 執行交易
    success = system.execute_trade(
        symbol=stock['symbol'],
        analysis=stock,
        market_env=market_env
    )
    
    if success:
        print(f"已進場: {stock['symbol']}")
```

#### Step 4: 盤中監控

```python
import time

while 交易時段:
    # 4.1 更新價格
    for symbol in system.risk_manager.positions.keys():
        current_price = 取得即時價格(symbol)
        
        # 4.2 檢查出場條件
        should_exit, reason = system.risk_manager.check_exit_signals(
            symbol, current_price
        )
        
        if should_exit:
            # 4.3 執行出場
            trade = system.risk_manager.close_position(
                symbol, current_price, datetime.now(), reason
            )
            
            # 4.4 記錄日誌
            system.trade_logger.log_exit(
                symbol=symbol,
                price=current_price,
                quantity=trade.quantity,
                pnl=trade.pnl,
                pnl_pct=trade.pnl_pct,
                exit_reason=reason,
                entry_time=trade.entry_time
            )
    
    time.sleep(30)  # 每 30 秒檢查一次
```

#### Step 5: 盤後檢討

```python
# 5.1 生成交易報表
system.trade_logger.print_report()

# 5.2 匯出 CSV
csv_file = system.trade_logger.export_to_csv()

# 5.3 查看系統狀態
system.print_status()

# 5.4 重置單日損益（隔天開盤前）
system.risk_manager.reset_daily_pnl()
```

---

## 配置說明

### config_enhanced.yml 重要參數

#### 風險控管

```yaml
risk_management:
  max_position_size_pct: 10.0      # 單筆最大部位 10%
  max_risk_per_trade_pct: 2.0      # 單筆最大風險 2%
  max_open_positions: 3            # 最多同時 3 檔
  default_stop_loss_pct: 3.0       # 停損 3%
  default_take_profit_pct: 6.0     # 停利 6%
  max_daily_loss_pct: 5.0          # 單日最大虧損 5%
  max_consecutive_losses: 3        # 連續虧損 3 次後冷靜
```

**調整建議:**
- 保守型: `max_position_size_pct: 5.0`, `max_risk_per_trade_pct: 1.0`
- 積極型: `max_position_size_pct: 15.0`, `max_risk_per_trade_pct: 3.0`
- **新手務必使用保守設定！**

#### 市場環境過濾

```yaml
market_environment:
  enabled: true                    # 是否啟用
  index_filter:
    require_above_ma20: true       # 大盤必須站上月線
  vix_filter:
    max_vix_for_long: 30           # VIX 超過 30 不做多
```

**調整建議:**
- 空頭市場: 設定 `require_above_ma20: true` 避免逆勢
- 多頭市場: 可設為 `false` 增加交易機會

#### 評分門檻

```yaml
scoring:
  min_score_for_entry: 70          # 最低進場分數 70
  min_score_for_strong_entry: 85   # 強力進場分數 85
```

**調整建議:**
- 提高門檻 (80+): 減少交易次數但提高品質
- 降低門檻 (60+): 增加交易機會但可能降低勝率

---

## 重要提醒

### ⚠️ 風險警告

1. **這不是聖杯**: 任何策略都無法保證獲利，過去績效不代表未來
2. **必須回測**: 使用前務必用至少 2 年歷史資料回測驗證
3. **小額測試**: 實盤前先用小額資金測試至少 1 個月
4. **嚴守紀律**: 程式只是工具，成敗在於執行紀律
5. **持續優化**: 市場會改變，策略需要定期檢視調整

### 📊 建議的學習步驟

**第 1 週: 學習系統**
- 閱讀所有模組文件
- 理解每個參數的意義
- 用模擬資料測試

**第 2-4 週: 回測驗證**
- 下載 2 年歷史資料
- 執行回測並記錄結果
- 調整參數優化策略

**第 5-8 週: 紙上交易**
- 每天選股但不實際下單
- 記錄假設進出場
- 統計模擬績效

**第 9 週起: 小額實戰**
- 用最小資金實戰（如 10 萬）
- 嚴格執行風控
- 持續記錄與檢討

### 🎯 成功的關鍵

1. **風險第一**: 先求不敗，再求勝
2. **嚴格停損**: 絕不違反停損規則
3. **部位控管**: 永不重壓單一股票
4. **市場環境**: 空頭時寧可休息
5. **持續學習**: 定期檢討交易日誌

### 📞 支援

如有問題或建議，歡迎提出討論！

---

**免責聲明**: 本系統僅供教育和研究用途，不構成投資建議。投資有風險，請謹慎評估自身風險承受能力。
