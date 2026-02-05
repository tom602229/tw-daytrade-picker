# 🔧 TW DayTrade Picker - 完整改進實作指南

> **版本:** 2.0  
> **日期:** 2026-02-05  
> **狀態:** Production-Ready Upgrade

---

## 📋 目錄

1. [已完成的基礎模組](#已完成的基礎模組)
2. [核心改進清單](#核心改進清單)
3. [改進實作步驟](#改進實作步驟)
4. [程式碼範本](#程式碼範本)
5. [測試指南](#測試指南)
6. [部署檢查清單](#部署檢查清單)

---

## ✅ 已完成的基礎模組

### 1. error_handler.py - 錯誤處理基礎模組
**位置:** `code/src/daytrade_picker/core/error_handler.py`

**功能:**
- ✅ 統一錯誤處理裝飾器 `@safe_execute`
- ✅ 資料驗證輔助函數
- ✅ 安全除法、NaN 清理
- ✅ 價格和數量驗證
- ✅ 錯誤日誌追蹤

**使用範例:**
```python
from core.error_handler import ErrorHandler, safe_calculate

error_handler = ErrorHandler()

@error_handler.safe_execute(default_return=0.0)
def calculate_rsi(data):
    # 你的計算邏輯
    return rsi_value
```

---

### 2. data_validator.py - 資料驗證模組
**位置:** `code/src/daytrade_picker/core/data_validator.py`

**功能:**
- ✅ OHLCV 資料驗證
- ✅ 資料清理（NaN、異常值）
- ✅ 異常值偵測（IQR、Z-score）
- ✅ 交易時間驗證
- ✅ 技術指標驗證

**使用範例:**
```python
from core.data_validator import DataValidator, quick_validate_ohlcv

# 快速驗證並清理
clean_data = quick_validate_ohlcv(raw_data, strict=False)

# 詳細驗證
validator = DataValidator()
is_valid, errors = validator.validate_ohlcv_data(data)
```

---

### 3. trading_costs.py - 交易成本計算模組
**位置:** `code/src/daytrade_picker/core/trading_costs.py`

**功能:**
- ✅ 精確計算手續費（含折扣）
- ✅ 證交稅計算（一般 0.3%、當沖 0.15%）
- ✅ 滑價估算
- ✅ 損益兩平價計算
- ✅ 淨損益計算

**使用範例:**
```python
from core.trading_costs import TradingCostCalculator

calculator = TradingCostCalculator(commission_discount=0.6)

# 計算淨損益
result = calculator.calculate_net_pnl(
    entry_price=100,
    exit_price=102,
    quantity=2,
    is_daytrade=True
)

print(f"淨利: {result['net_pnl']}")
print(f"淨報酬率: {result['net_return_pct']:.2f}%")
```

---

### 4. equity_protection.py - 資金曲線保護模組
**位置:** `code/src/daytrade_picker/core/equity_protection.py`

**功能:**
- ✅ 資金曲線監控
- ✅ 回撤控制
- ✅ 動態部位調整
- ✅ 自動暫停交易
- ✅ 連續虧損保護

**使用範例:**
```python
from core.equity_protection import EquityProtection

protection = EquityProtection(
    initial_capital=1000000,
    max_daily_loss_pct=2.0,
    max_drawdown_pct=10.0
)

# 每次交易後更新
result = protection.update_equity(pnl=5000)

# 檢查是否可交易
can_trade, reason = protection.can_trade()
if can_trade:
    # 獲取建議部位大小
    position_multiplier = protection.get_position_size_multiplier()
```

---

## 🎯 核心改進清單

### 必須立即改進（Critical）

| 模組 | 問題 | 改進方案 | 優先級 |
|------|------|---------|--------|
| enhanced_strategy.py | 缺少錯誤處理 | 加入 @safe_execute 裝飾器 | 🔴 P0 |
| enhanced_strategy.py | NaN 未處理 | 使用 data_validator 清理 | 🔴 P0 |
| risk_management.py | 固定停損 | 實作 ATR-based 動態停損 | 🔴 P0 |
| risk_management.py | 無交易成本 | 整合 trading_costs | 🔴 P0 |
| backtesting.py | 前視偏差風險 | 嚴格時間序列處理 | 🔴 P0 |
| backtesting.py | 無交易成本 | 整合 trading_costs | 🔴 P0 |

### 重要改進（High Priority）

| 模組 | 問題 | 改進方案 | 優先級 |
|------|------|---------|--------|
| market_environment.py | 缺震盪市識別 | 加入 ADX、布林帶寬度 | 🟡 P1 |
| market_environment.py | 無錯誤處理 | 加入 @safe_execute | 🟡 P1 |
| multi_timeframe.py | 無資料驗證 | 使用 data_validator | 🟡 P1 |
| main_strategy.py | 日誌不完整 | 建立結構化日誌系統 | 🟡 P1 |

---

## 🔨 改進實作步驟

### 步驟 1: 更新 enhanced_strategy.py

**改進要點:**
1. ✅ 匯入新的核心模組
2. ✅ 在所有技術指標計算加入錯誤處理
3. ✅ 在 generate_signals 加入資料驗證
4. ✅ 處理 NaN 值

**核心程式碼範本:**

```python
"""
Strategy C - Enhanced Version 2.0
加入完整錯誤處理與資料驗證
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple

# 匯入核心模組
from ..core.error_handler import ErrorHandler, safe_calculate
from ..core.data_validator import DataValidator, quick_validate_ohlcv

class EnhancedStrategyC:
    """策略 C - 增強版 2.0"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # 初始化核心模組
        self.error_handler = ErrorHandler(logger=self.logger)
        self.validator = DataValidator(logger=self.logger)
        
        self.logger.info("Strategy C Enhanced v2.0 已初始化")
    
    @safe_calculate(default_return=pd.Series())
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        計算 RSI - 加入錯誤處理
        """
        # 驗證輸入
        self.error_handler.validate_dataframe(
            data,
            required_columns=['close'],
            min_rows=period + 1
        )
        
        # 計算 RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 安全除法避免除以零
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # 清理 NaN
        rsi = self.error_handler.clean_nan(rsi, default=50.0, strategy='forward_fill')
        
        # 驗證 RSI 範圍
        rsi = rsi.clip(0, 100)
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信號 - 完整版
        """
        try:
            # 1. 資料驗證與清理
            self.logger.info("開始資料驗證...")
            data_clean = quick_validate_ohlcv(data, strict=False)
            
            if len(data_clean) < len(data):
                self.logger.warning(
                    f"資料清理: {len(data)} -> {len(data_clean)} 筆"
                )
            
            # 2. 計算技術指標（所有函數都有 @safe_calculate）
            self.logger.info("計算技術指標...")
            data_clean['rsi'] = self.calculate_rsi(data_clean)
            data_clean['macd'] = self.calculate_macd(data_clean)
            data_clean['bb_upper'], data_clean['bb_lower'] = self.calculate_bollinger(data_clean)
            
            # 3. 驗證指標
            is_valid, errors = self.validator.validate_indicator(
                data_clean['rsi'],
                name='RSI',
                valid_range=(0, 100),
                allow_nan=False
            )
            
            if not is_valid:
                self.logger.error(f"RSI 驗證失敗: {errors}")
                raise ValueError("技術指標驗證失敗")
            
            # 4. 生成信號
            self.logger.info("生成交易信號...")
            signals = self._generate_signal_logic(data_clean)
            
            # 5. 驗證信號
            is_valid, errors = self.validator.validate_signal(signals)
            if not is_valid:
                self.logger.warning(f"信號驗證警告: {errors}")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"信號生成失敗: {e}", exc_info=True)
            # 返回空信號而不是崩潰
            return pd.Series(0, index=data.index)
```

---

### 步驟 2: 更新 risk_management.py

**改進要點:**
1. ✅ ATR-based 動態停損
2. ✅ 整合 trading_costs
3. ✅ 整合 equity_protection
4. ✅ 錯誤處理

**核心程式碼範本:**

```python
"""
Risk Management - Enhanced Version 2.0
動態停損 + 交易成本整合
"""

from ..core.trading_costs import TradingCostCalculator
from ..core.equity_protection import EquityProtection
from ..core.error_handler import ErrorHandler

class RiskManager:
    """風險管理系統 2.0"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 初始化交易成本計算器
        self.cost_calculator = TradingCostCalculator(
            commission_discount=config.get('commission_discount', 0.6),
            enable_slippage=True
        )
        
        # 初始化資金保護
        self.equity_protection = EquityProtection(
            initial_capital=config.get('initial_capital', 1000000),
            max_daily_loss_pct=config.get('max_daily_loss_pct', 2.0),
            max_drawdown_pct=config.get('max_drawdown_pct', 10.0)
        )
        
        self.error_handler = ErrorHandler()
    
    def calculate_dynamic_stop_loss(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.0
    ) -> float:
        """
        計算 ATR-based 動態停損
        
        Args:
            entry_price: 進場價格
            atr: 當前 ATR 值
            atr_multiplier: ATR 倍數（預設 2.0）
        
        Returns:
            停損價格
        """
        try:
            # 驗證輸入
            self.error_handler.validate_price(entry_price)
            
            if atr <= 0 or np.isnan(atr):
                self.logger.warning(f"ATR 無效 ({atr})，使用固定停損")
                atr = entry_price * 0.02  # 回退到 2% 固定停損
            
            # 計算停損
            stop_loss = entry_price - (atr * atr_multiplier)
            
            # 確保停損不會太緊或太鬆
            min_stop_pct = 0.01  # 最小 1%
            max_stop_pct = 0.05  # 最大 5%
            
            min_stop = entry_price * (1 - max_stop_pct)
            max_stop = entry_price * (1 - min_stop_pct)
            
            stop_loss = max(min_stop, min(max_stop, stop_loss))
            
            return round(stop_loss, 2)
            
        except Exception as e:
            self.logger.error(f"動態停損計算失敗: {e}")
            # 回退到固定停損
            return entry_price * 0.98
    
    def calculate_position_size(
        self,
        price: float,
        risk_per_trade_pct: float = 1.0,
        stop_loss_price: float = None
    ) -> int:
        """
        計算部位大小（考慮資金保護乘數）
        
        Returns:
            建議張數
        """
        try:
            # 1. 基礎部位計算
            current_capital = self.equity_protection.current_capital
            risk_amount = current_capital * (risk_per_trade_pct / 100)
            
            if stop_loss_price:
                risk_per_share = abs(price - stop_loss_price)
                base_quantity = int(risk_amount / (risk_per_share * 1000))
            else:
                # 預設最大投資 20% 資金
                max_investment = current_capital * 0.2
                base_quantity = int(max_investment / (price * 1000))
            
            # 2. 應用資金保護乘數
            protection_multiplier = self.equity_protection.get_position_size_multiplier()
            final_quantity = int(base_quantity * protection_multiplier)
            
            # 3. 限制範圍
            final_quantity = max(0, min(final_quantity, 10))  # 最多 10 張
            
            self.logger.info(
                f"部位計算: 基礎={base_quantity}, "
                f"保護乘數={protection_multiplier:.2f}, "
                f"最終={final_quantity} 張"
            )
            
            return final_quantity
            
        except Exception as e:
            self.logger.error(f"部位計算失敗: {e}")
            return 0
    
    def evaluate_trade(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int
    ) -> Dict:
        """
        評估交易（含成本）
        """
        # 計算淨損益
        result = self.cost_calculator.calculate_net_pnl(
            entry_price, exit_price, quantity, is_daytrade=True
        )
        
        # 更新資金保護
        protection_result = self.equity_protection.update_equity(result['net_pnl'])
        
        return {
            **result,
            'trading_status': protection_result['trading_status'],
            'can_trade': protection_result['protection_triggered'] == False
        }
```

---

### 步驟 3: 更新 market_environment.py

**改進要點:**
1. ✅ 加入震盪市識別（ADX、布林帶寬度）
2. ✅ 錯誤處理
3. ✅ 資料驗證

**核心程式碼範本:**

```python
"""
Market Environment Detector - Enhanced Version 2.0
加入震盪市識別與完整錯誤處理
"""

from ..core.error_handler import safe_calculate, ErrorHandler

class MarketEnvironmentDetector:
    """市場環境偵測器 2.0"""
    
    @safe_calculate(default_return=pd.Series(50.0))
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        計算 ADX - 用於判斷趨勢強度
        ADX > 25: 趨勢市場
        ADX < 20: 震盪市場
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # TR (True Range)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(window=period).mean()
        
        # +DI 和 -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # ADX
        adx = dx.rolling(window=period).mean()
        
        return adx.fillna(50.0)
    
    @safe_calculate(default_return=pd.Series(0.02))
    def calculate_bollinger_bandwidth(
        self,
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> pd.Series:
        """
        計算布林帶寬度 - 用於判斷波動性
        寬度 < 0.02: 極度收縮（可能突破）
        寬度 > 0.05: 高波動（謹慎交易）
        """
        close = data['close']
        
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        # 寬度 = (upper - lower) / sma
        bandwidth = (upper - lower) / sma
        
        return bandwidth.fillna(0.02)
    
    def detect_environment(self, data: pd.DataFrame) -> Dict:
        """
        綜合判斷市場環境
        
        Returns:
            {
                'type': 'trending' | 'ranging' | 'volatile',
                'strength': float (0-100),
                'recommendations': List[str]
            }
        """
        adx = self.calculate_adx(data)
        bb_width = self.calculate_bollinger_bandwidth(data)
        
        current_adx = adx.iloc[-1]
        current_width = bb_width.iloc[-1]
        
        # 判斷市場類型
        if current_adx > 25:
            market_type = 'trending'
            recommendations = [
                "適合趨勢追蹤策略",
                "可以使用較寬的停損",
                "注意趨勢反轉信號"
            ]
        elif current_adx < 20 and current_width < 0.03:
            market_type = 'ranging'
            recommendations = [
                "適合震盪交易策略",
                "使用較緊的停損",
                "注意支撐壓力位"
            ]
        else:
            market_type = 'volatile'
            recommendations = [
                "市場波動較大",
                "減小部位規模",
                "謹慎交易"
            ]
        
        return {
            'type': market_type,
            'adx': current_adx,
            'bb_width': current_width,
            'strength': current_adx,
            'recommendations': recommendations
        }
```

---

### 步驟 4: 更新 backtesting.py

**改進要點:**
1. ✅ 嚴格避免前視偏差
2. ✅ 整合交易成本
3. ✅ 時間序列驗證

**關鍵程式碼:**

```python
"""
Backtesting Engine - Enhanced Version 2.0
修正前視偏差 + 交易成本整合
"""

from ..core.trading_costs import TradingCostCalculator

class BacktestEngine:
    """回測引擎 2.0"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.cost_calculator = TradingCostCalculator(
            commission_discount=config.get('commission_discount', 0.6)
        )
    
    def run_backtest(self, data: pd.DataFrame, strategy) -> Dict:
        """
        執行回測 - 嚴格時間序列處理
        """
        results = []
        
        # 確保資料按時間排序
        data = data.sort_index()
        
        for i in range(len(data)):
            # ⚠️ 關鍵: 只使用當前時點之前的資料
            historical_data = data.iloc[:i+1]  # 包含當前但不包含未來
            
            # 生成信號（使用歷史資料）
            signal = strategy.generate_signal(historical_data)
            
            # 如果有信號，執行交易
            if signal != 0:
                entry_price = data['close'].iloc[i]
                
                # 下一根K棒才能成交（避免前視偏差）
                if i + 1 < len(data):
                    exit_price = data['close'].iloc[i+1]
                    
                    # 計算含成本的損益
                    trade_result = self.cost_calculator.calculate_net_pnl(
                        entry_price,
                        exit_price,
                        quantity=1,
                        is_daytrade=True
                    )
                    
                    results.append({
                        'entry_time': data.index[i],
                        'exit_time': data.index[i+1],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'gross_pnl': trade_result['gross_pnl'],
                        'net_pnl': trade_result['net_pnl'],
                        'cost': trade_result['total_cost']
                    })
        
        return self._calculate_statistics(results)
```

---

## 🧪 測試指南

### 建立測試框架

創建 `tests/test_core_modules.py`:

```python
"""
核心模組測試
"""

import pytest
import pandas as pd
import numpy as np
from src.daytrade_picker.core import (
    ErrorHandler,
    DataValidator,
    TradingCostCalculator,
    EquityProtection
)

class TestErrorHandler:
    def test_safe_division(self):
        handler = ErrorHandler()
        
        # 正常除法
        assert handler.safe_division(10, 2) == 5.0
        
        # 除以零
        assert handler.safe_division(10, 0, default=0.0) == 0.0
        
        # NaN 處理
        assert handler.safe_division(10, np.nan, default=0.0) == 0.0

class TestDataValidator:
    def test_ohlcv_validation(self):
        validator = DataValidator()
        
        # 正常資料
        good_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        is_valid, errors = validator.validate_ohlcv_data(good_data)
        assert is_valid == True
        assert len(errors) == 0
        
        # 異常資料 (High < Low)
        bad_data = pd.DataFrame({
            'open': [100],
            'high': [99],  # 錯誤: High < Low
            'low': [100],
            'close': [100],
            'volume': [1000]
        })
        
        is_valid, errors = validator.validate_ohlcv_data(bad_data, strict=False)
        assert is_valid == False
        assert len(errors) > 0

class TestTradingCosts:
    def test_cost_calculation(self):
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        # 測試案例: 買100賣102，2張，當沖
        result = calculator.calculate_net_pnl(
            entry_price=100,
            exit_price=102,
            quantity=2,
            is_daytrade=True
        )
        
        # 毛利應該是 4000 元
        assert result['gross_pnl'] == 4000
        
        # 淨利應該小於毛利（扣除成本）
        assert result['net_pnl'] < result['gross_pnl']
        
        # 成本應該 > 0
        assert result['total_cost'] > 0

class TestEquityProtection:
    def test_drawdown_protection(self):
        protection = EquityProtection(
            initial_capital=1000000,
            max_drawdown_pct=10.0
        )
        
        # 模擬大幅虧損
        protection.update_equity(-100000)  # 虧損 10%
        
        # 應該觸發保護
        can_trade, reason = protection.can_trade()
        assert can_trade == False

# 執行測試
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**執行測試:**
```bash
cd tw-daytrade-picker
python -m pytest tests/ -v
```

---

## ✅ 部署檢查清單

### 上線前必須完成

- [ ] **所有核心模組已整合錯誤處理**
- [ ] **資料驗證已加入所有輸入點**
- [ ] **交易成本已整合到回測和實盤**
- [ ] **資金保護系統已啟用**
- [ ] **單元測試全部通過**
- [ ] **回測驗證（最近 3 個月資料）**
- [ ] **紙上交易測試（至少 2 週）**
- [ ] **設定監控告警**

### 設定檢查

- [ ] **config_enhanced.yml 已更新**
  - commission_discount: 0.6
  - max_daily_loss_pct: 2.0
  - max_drawdown_pct: 10.0
  - enable_slippage: true
  
- [ ] **日誌系統已設定**
  - 等級: INFO
  - 檔案輸出: logs/trading_{date}.log
  - 保留天數: 30

### 監控指標

監控以下指標：
1. 每日損益
2. 當前回撤
3. 勝率
4. 平均獲利/虧損
5. 最大連續虧損
6. 交易成本佔比

---

## 📚 相關文件

- [程式碼審查報告](./程式碼審查報告.md)
- [API 文件](./api_documentation.md)
- [常見問題](./FAQ.md)

---

## 🆘 需要幫助？

如果在實作過程中遇到問題：

1. **檢查日誌** - 所有錯誤都會記錄
2. **執行測試** - `pytest tests/ -v`
3. **查看範例** - 每個模組都有 `if __name__ == "__main__"` 範例

---

**最後更新:** 2026-02-05
**版本:** 2.0.0
**狀態:** ✅ Ready for Implementation
