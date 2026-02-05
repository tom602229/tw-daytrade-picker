"""
快速驗證腳本 - 測試核心模組是否正常運作

執行方式:
    python scripts/quick_test.py
"""
import sys
import os

# 加入專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 80)
print("🧪 TW DayTrade Picker - 核心模組快速測試")
print("=" * 80)

# ============================================================================
# 1. 測試錯誤處理模組
# ============================================================================
print("\n📦 1. 測試錯誤處理模組 (error_handler.py)")
print("-" * 80)

try:
    from daytrade_picker.core.error_handler import ErrorHandler, safe_calculate
    
    eh = ErrorHandler()
    
    # 測試 safe_execute 裝飾器
    @eh.safe_execute(default_return=0)
    def divide_by_zero():
        return 1 / 0
    
    result = divide_by_zero()
    test1_pass = (result == 0)
    print(f"   ✓ safe_execute 裝飾器: {'✅ 通過' if test1_pass else '❌ 失敗'}")
    
    # 測試 safe_calculate
    result2 = safe_calculate(lambda: 10 / 0, default=99)
    test2_pass = (result2 == 99)
    print(f"   ✓ safe_calculate 函數: {'✅ 通過' if test2_pass else '❌ 失敗'}")
    
    module1_pass = test1_pass and test2_pass
    print(f"\n   {'✅ 錯誤處理模組測試通過' if module1_pass else '❌ 錯誤處理模組測試失敗'}")
    
except Exception as e:
    print(f"   ❌ 錯誤處理模組載入失敗: {str(e)}")
    module1_pass = False

# ============================================================================
# 2. 測試資料驗證模組
# ============================================================================
print("\n📦 2. 測試資料驗證模組 (data_validator.py)")
print("-" * 80)

try:
    from daytrade_picker.core.data_validator import DataValidator
    
    dv = DataValidator()
    
    # 建立測試資料
    test_data = pd.DataFrame({
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [105.0, 106.0, 107.0, 108.0, 109.0],
        'low': [98.0, 99.0, 100.0, 101.0, 102.0],
        'close': [103.0, 104.0, 105.0, 106.0, 107.0],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    # 測試 OHLCV 驗證
    is_valid, message = dv.validate_ohlcv(test_data)
    print(f"   ✓ OHLCV 驗證: {'✅ 通過' if is_valid else '❌ 失敗'}")
    
    # 測試 NaN 檢測
    test_data_nan = test_data.copy()
    test_data_nan.loc[2, 'close'] = np.nan
    has_nan = dv.check_nan(test_data_nan)
    print(f"   ✓ NaN 檢測: {'✅ 通過' if has_nan else '❌ 失敗'}")
    
    # 測試資料清理
    cleaned = dv.clean_data(test_data_nan)
    no_nan_after_clean = not dv.check_nan(cleaned)
    print(f"   ✓ 資料清理: {'✅ 通過' if no_nan_after_clean else '❌ 失敗'}")
    
    module2_pass = is_valid and has_nan and no_nan_after_clean
    print(f"\n   {'✅ 資料驗證模組測試通過' if module2_pass else '❌ 資料驗證模組測試失敗'}")
    
except Exception as e:
    print(f"   ❌ 資料驗證模組載入失敗: {str(e)}")
    module2_pass = False

# ============================================================================
# 3. 測試交易成本計算模組
# ============================================================================
print("\n📦 3. 測試交易成本計算模組 (trading_costs.py)")
print("-" * 80)

try:
    from daytrade_picker.core.trading_costs import TradingCostCalculator
    
    # 使用一般券商費率（6 折手續費）
    calc = TradingCostCalculator(
        commission_discount=0.6,
        is_daytrade=True
    )
    
    # 測試案例：買入 100 元，賣出 103 元，交易 1000 股（1 張）
    entry_price = 100.0
    exit_price = 103.0
    shares = 1000
    
    cost = calc.calculate_total_cost(
        entry_price=entry_price,
        exit_price=exit_price,
        shares=shares,
        is_daytrade=True
    )
    
    print(f"   測試案例: 買 {entry_price} 賣 {exit_price}，交易 {shares} 股")
    print(f"   ✓ 買入手續費: {cost['buy_commission']:.2f} 元")
    print(f"   ✓ 賣出手續費: {cost['sell_commission']:.2f} 元")
    print(f"   ✓ 證交稅: {cost['tax']:.2f} 元")
    print(f"   ✓ 總成本: {cost['total_cost']:.2f} 元")
    
    # 驗證成本合理性（當沖約 0.35-0.40%）
    total_value = (entry_price + exit_price) / 2 * shares
    cost_pct = (cost['total_cost'] / total_value) * 100
    cost_reasonable = 0.30 <= cost_pct <= 0.50
    
    print(f"   ✓ 成本比例: {cost_pct:.3f}%")
    print(f"   ✓ 成本合理性: {'✅ 通過 (0.30-0.50%)' if cost_reasonable else '❌ 失敗'}")
    
    # 測試損益兩平價
    breakeven = calc.calculate_breakeven_price(entry_price, shares, is_daytrade=True)
    print(f"   ✓ 損益兩平價: {breakeven:.2f} 元 (需漲 {((breakeven/entry_price-1)*100):.2f}%)")
    
    module3_pass = cost_reasonable and (breakeven > entry_price)
    print(f"\n   {'✅ 交易成本模組測試通過' if module3_pass else '❌ 交易成本模組測試失敗'}")
    
except Exception as e:
    print(f"   ❌ 交易成本模組載入失敗: {str(e)}")
    module3_pass = False

# ============================================================================
# 4. 測試資金曲線保護模組
# ============================================================================
print("\n📦 4. 測試資金曲線保護模組 (equity_protection.py)")
print("-" * 80)

try:
    from daytrade_picker.core.equity_protection import EquityProtection, TradingStatus
    
    initial_capital = 1000000
    ep = EquityProtection(
        initial_capital=initial_capital,
        max_drawdown_pct=10.0
    )
    
    # 測試正常狀態
    ep.update_equity(1050000)  # 獲利 5%
    status1 = ep.get_trading_status()
    test1 = (status1 == TradingStatus.ACTIVE)
    print(f"   ✓ 獲利狀態: {status1.name} {'✅' if test1 else '❌'}")
    
    # 測試警告狀態（回撤 5%）
    ep.update_equity(950000)
    status2 = ep.get_trading_status()
    multiplier2 = ep.get_position_multiplier()
    test2 = (multiplier2 < 1.0)  # 應該減倉
    print(f"   ✓ 回撤 5% 狀態: {status2.name}，部位倍數 {multiplier2:.2f} {'✅' if test2 else '❌'}")
    
    # 測試暫停狀態（回撤 10%）
    ep.update_equity(900000)
    status3 = ep.get_trading_status()
    multiplier3 = ep.get_position_multiplier()
    test3 = (status3 == TradingStatus.SUSPENDED and multiplier3 == 0.0)
    print(f"   ✓ 回撤 10% 狀態: {status3.name}，部位倍數 {multiplier3:.2f} {'✅' if test3 else '❌'}")
    
    # 測試連續虧損保護
    ep_loss = EquityProtection(initial_capital=initial_capital)
    ep_loss.record_trade_result(-5000)  # 虧損
    ep_loss.record_trade_result(-3000)  # 虧損
    ep_loss.record_trade_result(-2000)  # 虧損（第3次）
    
    consecutive_losses = ep_loss.performance_tracker['consecutive_losses']
    test4 = (consecutive_losses == 3)
    print(f"   ✓ 連續虧損追蹤: {consecutive_losses} 次 {'✅' if test4 else '❌'}")
    
    module4_pass = test1 and test2 and test3 and test4
    print(f"\n   {'✅ 資金保護模組測試通過' if module4_pass else '❌ 資金保護模組測試失敗'}")
    
except Exception as e:
    print(f"   ❌ 資金保護模組載入失敗: {str(e)}")
    module4_pass = False

# ============================================================================
# 總結
# ============================================================================
print("\n" + "=" * 80)
print("📊 測試總結")
print("=" * 80)

results = {
    '錯誤處理模組': module1_pass,
    '資料驗證模組': module2_pass,
    '交易成本模組': module3_pass,
    '資金保護模組': module4_pass,
}

for module_name, passed in results.items():
    status = "✅ 通過" if passed else "❌ 失敗"
    print(f"   {module_name}: {status}")

all_pass = all(results.values())
pass_count = sum(results.values())
total_count = len(results)

print("\n" + "=" * 80)
if all_pass:
    print("🎉 恭喜！所有核心模組測試通過！")
    print("✅ 系統已準備好進行下一階段整合")
else:
    print(f"⚠️  {pass_count}/{total_count} 個模組通過測試")
    print("請檢查失敗的模組並修復問題")
print("=" * 80)

# 返回狀態碼
sys.exit(0 if all_pass else 1)
