"""
核心模組測試套件

測試所有新建立的核心模組，確保功能正常運作。

執行方式:
    python -m pytest tests/test_core_modules.py -v
    或
    python tests/test_core_modules.py
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 加入專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 匯入要測試的模組
from src.daytrade_picker.core.error_handler import (
    ErrorHandler,
    DataValidationError,
    safe_calculate
)
from src.daytrade_picker.core.data_validator import (
    DataValidator,
    quick_validate_ohlcv
)
from src.daytrade_picker.core.trading_costs import (
    TradingCostCalculator,
    calculate_min_profit_target
)
from src.daytrade_picker.core.equity_protection import (
    EquityProtection,
    TradingStatus
)


class TestErrorHandler:
    """測試錯誤處理模組"""
    
    def test_safe_division_normal(self):
        """測試正常除法"""
        handler = ErrorHandler()
        result = handler.safe_division(10, 2)
        assert result == 5.0
    
    def test_safe_division_by_zero(self):
        """測試除以零"""
        handler = ErrorHandler()
        result = handler.safe_division(10, 0, default=0.0)
        assert result == 0.0
    
    def test_safe_division_nan(self):
        """測試 NaN 處理"""
        handler = ErrorHandler()
        result = handler.safe_division(10, np.nan, default=0.0)
        assert result == 0.0
    
    def test_safe_division_infinity(self):
        """測試無限值處理"""
        handler = ErrorHandler()
        result = handler.safe_division(10, np.inf, default=0.0)
        assert result == 0.0
    
    def test_clean_nan_single_value(self):
        """測試單一值 NaN 清理"""
        handler = ErrorHandler()
        
        # NaN 值
        result = handler.clean_nan(np.nan, default=0.0)
        assert result == 0.0
        
        # 正常值
        result = handler.clean_nan(10.5, default=0.0)
        assert result == 10.5
    
    def test_clean_nan_series(self):
        """測試 Series NaN 清理"""
        handler = ErrorHandler()
        
        data = pd.Series([1, 2, np.nan, 4, 5])
        result = handler.clean_nan(data, default=0.0)
        
        assert not result.isna().any()
        assert result.iloc[2] == 0.0
    
    def test_validate_price_valid(self):
        """測試有效價格驗證"""
        handler = ErrorHandler()
        
        assert handler.validate_price(100.0) == True
        assert handler.validate_price(0.01) == True
    
    def test_validate_price_invalid(self):
        """測試無效價格驗證"""
        handler = ErrorHandler()
        
        with pytest.raises(DataValidationError):
            handler.validate_price(0)
        
        with pytest.raises(DataValidationError):
            handler.validate_price(-10)
        
        with pytest.raises(DataValidationError):
            handler.validate_price(np.nan)
    
    def test_safe_execute_decorator(self):
        """測試安全執行裝飾器"""
        handler = ErrorHandler()
        
        @handler.safe_execute(default_return=0.0)
        def risky_function(a, b):
            return a / b
        
        # 正常情況
        assert risky_function(10, 2) == 5.0
        
        # 錯誤情況（除以零）
        assert risky_function(10, 0) == 0.0


class TestDataValidator:
    """測試資料驗證模組"""
    
    def test_validate_ohlcv_valid_data(self):
        """測試有效 OHLCV 資料"""
        validator = DataValidator()
        
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        is_valid, errors = validator.validate_ohlcv_data(data, strict=False)
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_ohlcv_missing_columns(self):
        """測試缺少欄位"""
        validator = DataValidator()
        
        data = pd.DataFrame({
            'open': [100, 101],
            'close': [101, 102]
            # 缺少 high, low, volume
        })
        
        is_valid, errors = validator.validate_ohlcv_data(data, strict=False)
        assert is_valid == False
        assert len(errors) > 0
    
    def test_validate_ohlcv_price_relationship(self):
        """測試價格關係異常"""
        validator = DataValidator()
        
        data = pd.DataFrame({
            'open': [100],
            'high': [99],  # 錯誤: High < Open
            'low': [100],
            'close': [100],
            'volume': [1000]
        })
        
        is_valid, errors = validator.validate_ohlcv_data(data, strict=False)
        assert is_valid == False
        assert any('High' in str(e) for e in errors)
    
    def test_validate_ohlcv_nan_values(self):
        """測試 NaN 值檢測"""
        validator = DataValidator()
        
        data = pd.DataFrame({
            'open': [100, np.nan, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        is_valid, errors = validator.validate_ohlcv_data(data, strict=False)
        assert is_valid == False
        assert any('NaN' in str(e) for e in errors)
    
    def test_clean_ohlcv_data(self):
        """測試資料清理"""
        validator = DataValidator()
        
        data = pd.DataFrame({
            'open': [100, np.nan, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, -100, 1200]  # 包含異常值
        })
        
        clean_data = validator.clean_ohlcv_data(data, method='fill')
        
        # 應該沒有 NaN
        assert not clean_data.isna().any().any()
        
        # 應該沒有負數成交量
        assert (clean_data['volume'] >= 0).all()
    
    def test_detect_outliers_iqr(self):
        """測試異常值偵測 (IQR)"""
        data = pd.Series([1, 2, 3, 4, 5, 100])  # 100 是異常值
        
        outliers = DataValidator.detect_outliers(data, method='iqr', threshold=1.5)
        
        assert outliers.iloc[-1] == True  # 最後一個是異常值
        assert outliers.iloc[0] == False  # 第一個不是異常值
    
    def test_validate_indicator(self):
        """測試技術指標驗證"""
        validator = DataValidator()
        
        # 有效的 RSI
        rsi = pd.Series([30, 40, 50, 60, 70])
        is_valid, errors = validator.validate_indicator(
            rsi,
            name='RSI',
            valid_range=(0, 100)
        )
        assert is_valid == True
        
        # 無效的 RSI (超出範圍)
        invalid_rsi = pd.Series([30, 40, 150, 60, 70])
        is_valid, errors = validator.validate_indicator(
            invalid_rsi,
            name='RSI',
            valid_range=(0, 100)
        )
        assert is_valid == False


class TestTradingCosts:
    """測試交易成本計算模組"""
    
    def test_calculate_commission(self):
        """測試手續費計算"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        commission = calculator.calculate_commission(
            price=100,
            quantity=1,
            is_buy=True
        )
        
        # 手續費應該 > 0
        assert commission > 0
        
        # 應該 >= 最低手續費 20 元
        assert commission >= 20
    
    def test_calculate_tax(self):
        """測試證交稅計算"""
        calculator = TradingCostCalculator()
        
        # 當沖稅率 0.15%
        tax_daytrade = calculator.calculate_tax(
            price=100,
            quantity=1,
            is_daytrade=True
        )
        
        # 一般稅率 0.3%
        tax_normal = calculator.calculate_tax(
            price=100,
            quantity=1,
            is_daytrade=False
        )
        
        # 當沖稅應該是一般稅的一半
        assert tax_daytrade < tax_normal
        assert abs(tax_daytrade * 2 - tax_normal) < 1  # 允許小誤差
    
    def test_calculate_round_trip_cost(self):
        """測試往返交易成本"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        costs = calculator.calculate_round_trip_cost(
            entry_price=100,
            exit_price=100,  # 同價買賣
            quantity=1,
            is_daytrade=True
        )
        
        # 應該包含所有成本項目
        assert 'total_commission' in costs
        assert 'tax' in costs
        assert 'total_cost' in costs
        
        # 總成本應該 > 0
        assert costs['total_cost'] > 0
        
        # 成本率應該合理 (通常 0.2% - 0.6%)
        assert 0.001 < costs['cost_rate'] < 1.0
    
    def test_calculate_net_pnl_profit(self):
        """測試淨損益計算（獲利情況）"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        result = calculator.calculate_net_pnl(
            entry_price=100,
            exit_price=102,  # 獲利 2%
            quantity=1,
            is_daytrade=True
        )
        
        # 毛利應該是 2000 元 (2 * 1000)
        assert result['gross_pnl'] == 2000
        
        # 淨利應該小於毛利（扣除成本）
        assert result['net_pnl'] < result['gross_pnl']
        
        # 淨利應該仍然是正數
        assert result['net_pnl'] > 0
    
    def test_calculate_net_pnl_loss(self):
        """測試淨損益計算（虧損情況）"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        result = calculator.calculate_net_pnl(
            entry_price=100,
            exit_price=98,  # 虧損 2%
            quantity=1,
            is_daytrade=True
        )
        
        # 毛損應該是 -2000 元
        assert result['gross_pnl'] == -2000
        
        # 淨損應該更大（加上成本）
        assert result['net_pnl'] < result['gross_pnl']
    
    def test_estimate_breakeven_price(self):
        """測試損益兩平價計算"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        breakeven = calculator.estimate_breakeven_price(
            entry_price=100,
            quantity=1,
            is_daytrade=True
        )
        
        # 損益兩平價應該高於買入價
        assert breakeven['breakeven_price'] > breakeven['entry_price']
        
        # 需要漲幅應該合理 (通常 0.3% - 0.8%)
        assert 0.2 < breakeven['price_increase_pct'] < 1.0
    
    def test_get_cost_summary(self):
        """測試成本統計摘要"""
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        # 執行幾筆交易
        calculator.calculate_round_trip_cost(100, 102, 1, True)
        calculator.calculate_round_trip_cost(100, 101, 1, True)
        
        summary = calculator.get_cost_summary()
        
        assert summary['total_trades'] == 2
        assert summary['total_cost'] > 0
        assert summary['avg_cost_per_trade'] > 0


class TestEquityProtection:
    """測試資金曲線保護模組"""
    
    def test_initialization(self):
        """測試初始化"""
        protection = EquityProtection(
            initial_capital=1000000,
            max_daily_loss_pct=2.0,
            max_drawdown_pct=10.0
        )
        
        assert protection.current_capital == 1000000
        assert protection.trading_status == TradingStatus.ACTIVE
    
    def test_update_equity_profit(self):
        """測試更新資金（獲利）"""
        protection = EquityProtection(initial_capital=1000000)
        
        result = protection.update_equity(pnl=10000)
        
        assert result['current_capital'] == 1010000
        assert result['pnl'] == 10000
        assert protection.consecutive_wins == 1
        assert protection.consecutive_losses == 0
    
    def test_update_equity_loss(self):
        """測試更新資金（虧損）"""
        protection = EquityProtection(initial_capital=1000000)
        
        result = protection.update_equity(pnl=-10000)
        
        assert result['current_capital'] == 990000
        assert protection.consecutive_losses == 1
        assert protection.consecutive_wins == 0
    
    def test_drawdown_calculation(self):
        """測試回撤計算"""
        protection = EquityProtection(
            initial_capital=1000000,
            max_drawdown_pct=10.0
        )
        
        # 先獲利到高峰
        protection.update_equity(100000)  # 1,100,000
        
        # 然後虧損
        protection.update_equity(-50000)  # 1,050,000
        
        # 回撤應該是 (1,100,000 - 1,050,000) / 1,100,000 ≈ 4.5%
        assert abs(protection.current_drawdown - 0.0455) < 0.01
    
    def test_max_daily_loss_protection(self):
        """測試單日虧損保護"""
        protection = EquityProtection(
            initial_capital=1000000,
            max_daily_loss_pct=2.0,
            auto_suspend=True
        )
        
        # 虧損 2% (達到上限)
        protection.update_equity(-20000)
        
        # 應該被暫停
        assert protection.trading_status == TradingStatus.SUSPENDED
        
        can_trade, reason = protection.can_trade()
        assert can_trade == False
    
    def test_max_drawdown_protection(self):
        """測試最大回撤保護"""
        protection = EquityProtection(
            initial_capital=1000000,
            max_drawdown_pct=10.0,
            auto_suspend=True
        )
        
        # 虧損 10% (達到回撤上限)
        protection.update_equity(-100000)
        
        # 應該被暫停
        assert protection.trading_status == TradingStatus.SUSPENDED
        
        can_trade, reason = protection.can_trade()
        assert can_trade == False
    
    def test_consecutive_loss_reduction(self):
        """測試連續虧損減倉"""
        protection = EquityProtection(
            initial_capital=1000000,
            consecutive_loss_limit=3
        )
        
        # 連續虧損 3 次
        protection.update_equity(-5000)
        protection.update_equity(-5000)
        protection.update_equity(-5000)
        
        # 應該進入減倉模式
        assert protection.trading_status == TradingStatus.REDUCED
    
    def test_position_size_multiplier(self):
        """測試部位大小乘數"""
        protection = EquityProtection(
            initial_capital=1000000,
            position_scaling=True
        )
        
        # 正常狀態應該是 1.0
        assert protection.get_position_size_multiplier() == 1.0
        
        # 連續虧損後應該減少
        protection.update_equity(-5000)
        protection.update_equity(-5000)
        protection.update_equity(-5000)
        
        multiplier = protection.get_position_size_multiplier()
        assert multiplier < 1.0
    
    def test_reset_daily_pnl(self):
        """測試重置每日損益"""
        protection = EquityProtection(initial_capital=1000000)
        
        protection.update_equity(-10000)
        assert protection.daily_pnl == -10000
        
        protection.reset_daily_pnl()
        assert protection.daily_pnl == 0.0
    
    def test_get_statistics(self):
        """測試統計資訊"""
        protection = EquityProtection(initial_capital=1000000)
        
        # 執行一些交易
        protection.update_equity(5000)
        protection.update_equity(-3000)
        protection.update_equity(4000)
        
        stats = protection.get_statistics()
        
        assert stats['total_trades'] == 3
        assert stats['winning_trades'] == 2
        assert stats['losing_trades'] == 1
        assert stats['total_pnl'] == 6000
        assert stats['win_rate_pct'] > 0


# 整合測試
class TestIntegration:
    """整合測試 - 測試模組之間的協作"""
    
    def test_full_trade_workflow(self):
        """測試完整交易流程"""
        # 1. 初始化
        protection = EquityProtection(initial_capital=1000000)
        calculator = TradingCostCalculator(commission_discount=0.6)
        
        # 2. 執行交易
        entry_price = 100.0
        exit_price = 102.0
        quantity = 2
        
        # 3. 計算淨損益
        trade_result = calculator.calculate_net_pnl(
            entry_price, exit_price, quantity, is_daytrade=True
        )
        
        # 4. 更新資金保護
        protection_result = protection.update_equity(trade_result['net_pnl'])
        
        # 5. 驗證結果
        assert trade_result['net_pnl'] > 0  # 應該有獲利
        assert protection_result['current_capital'] > 1000000
        assert protection.can_trade()[0] == True


def run_all_tests():
    """執行所有測試"""
    print("=" * 80)
    print("🧪 執行核心模組測試套件")
    print("=" * 80)
    
    # 使用 pytest 執行
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ 所有測試通過！")
    else:
        print("❌ 部分測試失敗，請檢查錯誤訊息")
    print("=" * 80)
    
    return exit_code


if __name__ == "__main__":
    run_all_tests()
