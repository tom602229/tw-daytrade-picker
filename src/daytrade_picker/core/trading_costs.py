"""
交易成本計算模組

精確計算台股交易的所有成本，包括手續費、證交稅、滑價等。
這是回測系統與實盤交易的關鍵模組。

台股交易成本結構：
- 手續費：0.1425%（可打折，通常 6 折 = 0.0855%）
- 證交稅：當沖 0.15%，一般 0.3%
- 滑價：根據市場流動性估算

Author: TW DayTrade Picker
Version: 2.0
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from datetime import datetime
import logging


class TradingCostCalculator:
    """
    台股交易成本計算器
    
    精確計算各種交易成本，支援不同券商費率和交易模式
    """
    
    # 台股標準費率（單位：%）
    STANDARD_COMMISSION_RATE = 0.1425  # 手續費 0.1425%
    STANDARD_TAX_RATE = 0.3            # 證交稅 0.3%
    DAYTRADE_TAX_RATE = 0.15           # 當沖證交稅 0.15%
    MIN_COMMISSION = 20                # 最低手續費 20 元
    
    def __init__(
        self,
        commission_rate: float = 0.1425,
        commission_discount: float = 0.6,  # 6 折
        tax_rate: float = 0.3,
        daytrade_tax_rate: float = 0.15,
        min_commission: float = 20.0,
        enable_slippage: bool = True,
        slippage_bps: float = 2.0,  # 滑價 2 個基點 (0.02%)
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化交易成本計算器
        
        Args:
            commission_rate: 手續費率（%）
            commission_discount: 手續費折扣（1.0 = 無折扣，0.6 = 六折）
            tax_rate: 一般交易證交稅率（%）
            daytrade_tax_rate: 當沖證交稅率（%）
            min_commission: 最低手續費（元）
            enable_slippage: 是否計算滑價
            slippage_bps: 滑價（基點，1 bps = 0.01%）
            logger: 日誌記錄器
        """
        self.commission_rate = commission_rate / 100  # 轉換為小數
        self.commission_discount = commission_discount
        self.tax_rate = tax_rate / 100
        self.daytrade_tax_rate = daytrade_tax_rate / 100
        self.min_commission = min_commission
        self.enable_slippage = enable_slippage
        self.slippage_bps = slippage_bps / 10000  # 轉換為小數
        
        self.logger = logger or logging.getLogger(__name__)
        
        # 成本追蹤
        self.total_commission = 0.0
        self.total_tax = 0.0
        self.total_slippage = 0.0
        self.trade_count = 0
        
        self.logger.info(
            f"交易成本計算器已初始化: "
            f"手續費={commission_rate}%×{commission_discount}, "
            f"稅率={tax_rate}%, "
            f"當沖稅率={daytrade_tax_rate}%, "
            f"滑價={slippage_bps} bps"
        )
    
    def calculate_commission(
        self,
        price: float,
        quantity: int,
        is_buy: bool = True
    ) -> float:
        """
        計算手續費
        
        Args:
            price: 成交價格
            quantity: 數量（張）
            is_buy: 是否為買入（買賣手續費相同，此參數保留供未來擴展）
        
        Returns:
            手續費金額（元）
        """
        # 計算交易金額（1 張 = 1000 股）
        trade_value = price * quantity * 1000
        
        # 計算手續費
        commission = trade_value * self.commission_rate * self.commission_discount
        
        # 確保不低於最低手續費
        commission = max(commission, self.min_commission)
        
        return round(commission, 0)  # 四捨五入到整數
    
    def calculate_tax(
        self,
        price: float,
        quantity: int,
        is_daytrade: bool = False
    ) -> float:
        """
        計算證交稅（僅賣出時收取）
        
        Args:
            price: 賣出價格
            quantity: 數量（張）
            is_daytrade: 是否為當沖交易
        
        Returns:
            證交稅金額（元）
        """
        # 計算交易金額
        trade_value = price * quantity * 1000
        
        # 選擇稅率
        tax_rate = self.daytrade_tax_rate if is_daytrade else self.tax_rate
        
        # 計算證交稅
        tax = trade_value * tax_rate
        
        return round(tax, 0)  # 四捨五入到整數
    
    def calculate_slippage(
        self,
        price: float,
        quantity: int,
        is_buy: bool = True,
        market_impact_factor: float = 1.0
    ) -> float:
        """
        計算滑價成本
        
        Args:
            price: 目標價格
            quantity: 數量（張）
            is_buy: 是否為買入
            market_impact_factor: 市場衝擊因子（1.0 = 正常，>1.0 = 流動性較差）
        
        Returns:
            滑價成本（元）
        """
        if not self.enable_slippage:
            return 0.0
        
        # 計算交易金額
        trade_value = price * quantity * 1000
        
        # 基礎滑價
        base_slippage = trade_value * self.slippage_bps
        
        # 考慮市場衝擊（大量交易會有更多滑價）
        slippage = base_slippage * market_impact_factor
        
        return round(slippage, 0)
    
    def calculate_round_trip_cost(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        is_daytrade: bool = True
    ) -> Dict[str, float]:
        """
        計算完整往返交易成本（買入 + 賣出）
        
        Args:
            entry_price: 買入價格
            exit_price: 賣出價格
            quantity: 數量（張）
            is_daytrade: 是否為當沖
        
        Returns:
            包含各項成本的字典
        """
        # 買入成本
        buy_commission = self.calculate_commission(entry_price, quantity, is_buy=True)
        buy_slippage = self.calculate_slippage(entry_price, quantity, is_buy=True)
        
        # 賣出成本
        sell_commission = self.calculate_commission(exit_price, quantity, is_buy=False)
        sell_tax = self.calculate_tax(exit_price, quantity, is_daytrade=is_daytrade)
        sell_slippage = self.calculate_slippage(exit_price, quantity, is_buy=False)
        
        # 總成本
        total_commission = buy_commission + sell_commission
        total_tax = sell_tax
        total_slippage = buy_slippage + sell_slippage
        total_cost = total_commission + total_tax + total_slippage
        
        # 更新追蹤
        self.total_commission += total_commission
        self.total_tax += total_tax
        self.total_slippage += total_slippage
        self.trade_count += 1
        
        return {
            'buy_commission': buy_commission,
            'sell_commission': sell_commission,
            'total_commission': total_commission,
            'tax': total_tax,
            'buy_slippage': buy_slippage,
            'sell_slippage': sell_slippage,
            'total_slippage': total_slippage,
            'total_cost': total_cost,
            'cost_rate': self._calculate_cost_rate(entry_price, quantity, total_cost)
        }
    
    def calculate_net_pnl(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        is_daytrade: bool = True
    ) -> Dict[str, float]:
        """
        計算扣除成本後的淨損益
        
        Args:
            entry_price: 買入價格
            exit_price: 賣出價格
            quantity: 數量（張）
            is_daytrade: 是否為當沖
        
        Returns:
            包含損益詳情的字典
        """
        # 計算毛利
        gross_pnl = (exit_price - entry_price) * quantity * 1000
        
        # 計算成本
        costs = self.calculate_round_trip_cost(
            entry_price, exit_price, quantity, is_daytrade
        )
        
        # 計算淨利
        net_pnl = gross_pnl - costs['total_cost']
        
        # 計算報酬率
        investment = entry_price * quantity * 1000
        gross_return = (gross_pnl / investment) * 100 if investment > 0 else 0
        net_return = (net_pnl / investment) * 100 if investment > 0 else 0
        
        return {
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'total_cost': costs['total_cost'],
            'commission': costs['total_commission'],
            'tax': costs['tax'],
            'slippage': costs['total_slippage'],
            'gross_return_pct': gross_return,
            'net_return_pct': net_return,
            'cost_rate_pct': costs['cost_rate']
        }
    
    def _calculate_cost_rate(
        self,
        price: float,
        quantity: int,
        total_cost: float
    ) -> float:
        """
        計算成本率（成本佔投資金額的百分比）
        
        Args:
            price: 價格
            quantity: 數量（張）
            total_cost: 總成本
        
        Returns:
            成本率（%）
        """
        investment = price * quantity * 1000
        if investment <= 0:
            return 0.0
        
        return (total_cost / investment) * 100
    
    def estimate_breakeven_price(
        self,
        entry_price: float,
        quantity: int,
        is_daytrade: bool = True
    ) -> Dict[str, float]:
        """
        估算損益兩平價格
        
        Args:
            entry_price: 買入價格
            quantity: 數量（張）
            is_daytrade: 是否為當沖
        
        Returns:
            包含損益兩平資訊的字典
        """
        # 初始估算（假設賣出價 = 買入價）
        costs = self.calculate_round_trip_cost(
            entry_price, entry_price, quantity, is_daytrade
        )
        
        # 需要彌補的成本
        total_cost = costs['total_cost']
        
        # 計算損益兩平價格（考慮賣出時也需要手續費和稅）
        # 設 x 為損益兩平價格
        # (x - entry_price) * qty * 1000 = buy_comm + sell_comm(x) + tax(x) + slippage
        
        # 簡化計算：使用迭代法
        breakeven_price = entry_price
        max_iterations = 10
        
        for i in range(max_iterations):
            costs = self.calculate_round_trip_cost(
                entry_price, breakeven_price, quantity, is_daytrade
            )
            
            gross_pnl_needed = costs['total_cost']
            breakeven_price = entry_price + (gross_pnl_needed / (quantity * 1000))
            
            # 檢查收斂
            if i > 0 and abs(breakeven_price - entry_price) < 0.01:
                break
        
        # 計算需要的漲幅
        price_increase = breakeven_price - entry_price
        price_increase_pct = (price_increase / entry_price) * 100
        
        return {
            'entry_price': entry_price,
            'breakeven_price': round(breakeven_price, 2),
            'price_increase': round(price_increase, 2),
            'price_increase_pct': round(price_increase_pct, 3),
            'total_cost': round(costs['total_cost'], 0)
        }
    
    def get_cost_summary(self) -> Dict[str, any]:
        """
        獲取成本統計摘要
        
        Returns:
            包含成本統計的字典
        """
        if self.trade_count == 0:
            return {
                'total_trades': 0,
                'total_commission': 0.0,
                'total_tax': 0.0,
                'total_slippage': 0.0,
                'total_cost': 0.0,
                'avg_cost_per_trade': 0.0
            }
        
        total_cost = self.total_commission + self.total_tax + self.total_slippage
        
        return {
            'total_trades': self.trade_count,
            'total_commission': round(self.total_commission, 0),
            'total_tax': round(self.total_tax, 0),
            'total_slippage': round(self.total_slippage, 0),
            'total_cost': round(total_cost, 0),
            'avg_cost_per_trade': round(total_cost / self.trade_count, 0),
            'commission_ratio': self.total_commission / total_cost if total_cost > 0 else 0,
            'tax_ratio': self.total_tax / total_cost if total_cost > 0 else 0,
            'slippage_ratio': self.total_slippage / total_cost if total_cost > 0 else 0
        }
    
    def reset_tracking(self):
        """重置成本追蹤"""
        self.total_commission = 0.0
        self.total_tax = 0.0
        self.total_slippage = 0.0
        self.trade_count = 0
        self.logger.info("成本追蹤已重置")
    
    @staticmethod
    def get_broker_presets() -> Dict[str, Dict[str, float]]:
        """
        獲取常見券商費率預設
        
        Returns:
            券商費率字典
        """
        return {
            'standard': {
                'commission_rate': 0.1425,
                'commission_discount': 1.0,
                'description': '標準費率（無折扣）'
            },
            'discount_6': {
                'commission_rate': 0.1425,
                'commission_discount': 0.6,
                'description': '6 折手續費（常見）'
            },
            'discount_5': {
                'commission_rate': 0.1425,
                'commission_discount': 0.5,
                'description': '5 折手續費（優惠）'
            },
            'discount_28': {
                'commission_rate': 0.1425,
                'commission_discount': 0.28,
                'description': '28 折手續費（電子下單優惠）'
            },
            'ultra_low': {
                'commission_rate': 0.1425,
                'commission_discount': 0.2,
                'description': '2 折手續費（大戶或特殊優惠）'
            }
        }


def calculate_min_profit_target(
    entry_price: float,
    quantity: int = 1,
    commission_discount: float = 0.6,
    is_daytrade: bool = True
) -> Dict[str, float]:
    """
    快速計算最小獲利目標
    
    Args:
        entry_price: 買入價格
        quantity: 數量（張）
        commission_discount: 手續費折扣
        is_daytrade: 是否為當沖
    
    Returns:
        包含最小獲利資訊的字典
    
    Example:
        >>> result = calculate_min_profit_target(100, quantity=1)
        >>> print(f"損益兩平價: {result['breakeven_price']}")
    """
    calculator = TradingCostCalculator(commission_discount=commission_discount)
    return calculator.estimate_breakeven_price(entry_price, quantity, is_daytrade)


if __name__ == "__main__":
    # 測試範例
    print("=" * 80)
    print("台股交易成本計算器測試")
    print("=" * 80)
    
    # 創建計算器（6 折手續費）
    calculator = TradingCostCalculator(commission_discount=0.6)
    
    # 測試案例：買入 100 元，賣出 102 元，交易 2 張，當沖
    entry_price = 100.0
    exit_price = 102.0
    quantity = 2
    
    print(f"\n測試案例:")
    print(f"  買入價: {entry_price} 元")
    print(f"  賣出價: {exit_price} 元")
    print(f"  數量: {quantity} 張")
    print(f"  交易類型: 當沖")
    
    # 計算淨損益
    result = calculator.calculate_net_pnl(entry_price, exit_price, quantity, is_daytrade=True)
    
    print(f"\n損益分析:")
    print(f"  毛利: {result['gross_pnl']:,.0f} 元")
    print(f"  手續費: {result['commission']:,.0f} 元")
    print(f"  證交稅: {result['tax']:,.0f} 元")
    print(f"  滑價: {result['slippage']:,.0f} 元")
    print(f"  總成本: {result['total_cost']:,.0f} 元")
    print(f"  淨利: {result['net_pnl']:,.0f} 元")
    print(f"  毛報酬率: {result['gross_return_pct']:.2f}%")
    print(f"  淨報酬率: {result['net_return_pct']:.2f}%")
    print(f"  成本率: {result['cost_rate_pct']:.3f}%")
    
    # 計算損益兩平價
    breakeven = calculator.estimate_breakeven_price(entry_price, quantity, is_daytrade=True)
    
    print(f"\n損益兩平分析:")
    print(f"  買入價: {breakeven['entry_price']} 元")
    print(f"  損益兩平價: {breakeven['breakeven_price']} 元")
    print(f"  需要漲幅: {breakeven['price_increase']} 元 ({breakeven['price_increase_pct']:.3f}%)")
    print(f"  總成本: {breakeven['total_cost']:,.0f} 元")
    
    # 顯示券商費率預設
    print(f"\n常見券商費率:")
    presets = TradingCostCalculator.get_broker_presets()
    for name, config in presets.items():
        print(f"  {config['description']}: 折扣 {config['commission_discount']*100:.0f}%")
    
    print("\n" + "=" * 80)
