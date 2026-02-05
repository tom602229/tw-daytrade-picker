"""
資金曲線保護模組

提供資金曲線監控與保護機制，避免連續虧損造成重大損失。
包含動態部位調整、回撤控制、暫停交易等功能。

Author: TW DayTrade Picker
Version: 2.0
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging


class TradingStatus(Enum):
    """交易狀態"""
    ACTIVE = "active"              # 正常交易
    REDUCED = "reduced"            # 減倉交易（部位縮小）
    SUSPENDED = "suspended"        # 暫停交易
    RECOVERY = "recovery"          # 恢復階段（謹慎交易）


class EquityProtection:
    """
    資金曲線保護系統
    
    監控資金變化並自動調整交易策略以保護資本
    """
    
    def __init__(
        self,
        initial_capital: float,
        max_daily_loss_pct: float = 2.0,
        max_drawdown_pct: float = 10.0,
        consecutive_loss_limit: int = 3,
        recovery_period_days: int = 5,
        position_scaling: bool = True,
        auto_suspend: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化資金保護系統
        
        Args:
            initial_capital: 初始資金
            max_daily_loss_pct: 單日最大虧損百分比
            max_drawdown_pct: 最大回撤百分比
            consecutive_loss_limit: 連續虧損次數上限
            recovery_period_days: 恢復期天數
            position_scaling: 是否啟用動態部位調整
            auto_suspend: 是否自動暫停交易
            logger: 日誌記錄器
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.max_daily_loss_pct = max_daily_loss_pct / 100
        self.max_drawdown_pct = max_drawdown_pct / 100
        self.consecutive_loss_limit = consecutive_loss_limit
        self.recovery_period_days = recovery_period_days
        self.position_scaling = position_scaling
        self.auto_suspend = auto_suspend
        
        self.logger = logger or logging.getLogger(__name__)
        
        # 狀態追蹤
        self.trading_status = TradingStatus.ACTIVE
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.daily_pnl = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown_reached = 0.0
        
        # 歷史記錄
        self.equity_curve = [initial_capital]
        self.equity_dates = [datetime.now()]
        self.trade_history = []
        
        # 暫停相關
        self.suspension_start_date = None
        self.suspension_reason = None
        
        self.logger.info(
            f"資金保護系統已初始化: "
            f"初始資金={initial_capital:,.0f}, "
            f"單日虧損上限={max_daily_loss_pct:.1%}, "
            f"最大回撤={max_drawdown_pct:.1%}, "
            f"連續虧損上限={consecutive_loss_limit}"
        )
    
    def update_equity(
        self,
        pnl: float,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        更新資金並檢查保護條件
        
        Args:
            pnl: 本次交易損益
            timestamp: 時間戳記
        
        Returns:
            包含狀態更新的字典
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 更新資金
        self.current_capital += pnl
        self.daily_pnl += pnl
        
        # 記錄到資金曲線
        self.equity_curve.append(self.current_capital)
        self.equity_dates.append(timestamp)
        
        # 更新高峰資金
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # 計算當前回撤
        self.current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        self.max_drawdown_reached = max(self.max_drawdown_reached, self.current_drawdown)
        
        # 更新連續虧損/獲利次數
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        elif pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # 記錄交易
        self.trade_history.append({
            'timestamp': timestamp,
            'pnl': pnl,
            'equity': self.current_capital,
            'drawdown': self.current_drawdown,
            'status': self.trading_status.value
        })
        
        # 檢查保護條件
        protection_triggered = self._check_protection_rules()
        
        # 返回狀態
        return {
            'current_capital': self.current_capital,
            'pnl': pnl,
            'daily_pnl': self.daily_pnl,
            'current_drawdown': self.current_drawdown,
            'trading_status': self.trading_status.value,
            'protection_triggered': protection_triggered,
            'position_size_multiplier': self.get_position_size_multiplier()
        }
    
    def _check_protection_rules(self) -> bool:
        """
        檢查是否觸發保護機制
        
        Returns:
            是否觸發了保護規則
        """
        triggered = False
        
        # 1. 檢查單日虧損限制
        daily_loss_pct = abs(self.daily_pnl / self.initial_capital)
        if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
            self._trigger_suspension(
                f"單日虧損達 {daily_loss_pct:.2%}，超過上限 {self.max_daily_loss_pct:.2%}"
            )
            triggered = True
        
        # 2. 檢查最大回撤
        if self.current_drawdown >= self.max_drawdown_pct:
            self._trigger_suspension(
                f"回撤達 {self.current_drawdown:.2%}，超過上限 {self.max_drawdown_pct:.2%}"
            )
            triggered = True
        
        # 3. 檢查連續虧損
        if self.consecutive_losses >= self.consecutive_loss_limit:
            self._trigger_reduction(
                f"連續虧損 {self.consecutive_losses} 次，達到上限"
            )
            triggered = True
        
        # 4. 檢查是否可以恢復
        if self.trading_status in [TradingStatus.SUSPENDED, TradingStatus.REDUCED]:
            self._check_recovery_conditions()
        
        return triggered
    
    def _trigger_suspension(self, reason: str):
        """觸發暫停交易"""
        if not self.auto_suspend:
            self.logger.warning(f"保護觸發但未啟用自動暫停: {reason}")
            return
        
        self.trading_status = TradingStatus.SUSPENDED
        self.suspension_start_date = datetime.now()
        self.suspension_reason = reason
        
        self.logger.error(f"❌ 交易已暫停: {reason}")
    
    def _trigger_reduction(self, reason: str):
        """觸發減倉交易"""
        if self.trading_status == TradingStatus.ACTIVE:
            self.trading_status = TradingStatus.REDUCED
            self.logger.warning(f"⚠️ 進入減倉模式: {reason}")
    
    def _check_recovery_conditions(self):
        """檢查是否符合恢復條件"""
        if self.trading_status == TradingStatus.SUSPENDED:
            # 暫停後需要等待恢復期
            if self.suspension_start_date:
                days_suspended = (datetime.now() - self.suspension_start_date).days
                if days_suspended >= self.recovery_period_days:
                    self.trading_status = TradingStatus.RECOVERY
                    self.logger.info(
                        f"✅ 暫停期結束，進入恢復階段（謹慎交易）"
                    )
        
        elif self.trading_status == TradingStatus.REDUCED:
            # 減倉後，如果連續獲利則恢復
            if self.consecutive_wins >= 2:
                self.trading_status = TradingStatus.RECOVERY
                self.logger.info(
                    f"✅ 連續獲利 {self.consecutive_wins} 次，進入恢復階段"
                )
        
        elif self.trading_status == TradingStatus.RECOVERY:
            # 恢復階段，如果穩定則恢復正常
            if self.consecutive_wins >= 3 and self.current_drawdown < self.max_drawdown_pct / 2:
                self.trading_status = TradingStatus.ACTIVE
                self.consecutive_losses = 0
                self.logger.info(
                    f"✅ 交易狀態恢復正常"
                )
    
    def get_position_size_multiplier(self) -> float:
        """
        根據當前狀態獲取部位大小乘數
        
        Returns:
            部位大小乘數（0.0 - 1.0）
        """
        if not self.position_scaling:
            return 1.0 if self.trading_status == TradingStatus.ACTIVE else 0.0
        
        # 根據狀態調整部位
        if self.trading_status == TradingStatus.SUSPENDED:
            return 0.0  # 完全停止交易
        
        elif self.trading_status == TradingStatus.REDUCED:
            # 減倉至 50%
            base_multiplier = 0.5
        
        elif self.trading_status == TradingStatus.RECOVERY:
            # 恢復階段 70%
            base_multiplier = 0.7
        
        else:  # ACTIVE
            base_multiplier = 1.0
        
        # 根據回撤進一步調整
        drawdown_factor = 1.0
        if self.current_drawdown > 0:
            # 回撤越大，部位越小
            drawdown_factor = max(0.5, 1.0 - (self.current_drawdown / self.max_drawdown_pct))
        
        # 根據連續虧損調整
        loss_factor = 1.0
        if self.consecutive_losses > 0:
            loss_factor = max(0.5, 1.0 - (self.consecutive_losses * 0.1))
        
        final_multiplier = base_multiplier * drawdown_factor * loss_factor
        
        return max(0.0, min(1.0, final_multiplier))  # 限制在 0-1 之間
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        檢查是否可以交易
        
        Returns:
            (是否可以交易, 原因說明)
        """
        if self.trading_status == TradingStatus.SUSPENDED:
            return False, f"交易已暫停: {self.suspension_reason}"
        
        # 檢查單日虧損
        daily_loss_pct = abs(self.daily_pnl / self.initial_capital)
        if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"達到單日虧損上限 {self.max_daily_loss_pct:.1%}"
        
        # 檢查回撤
        if self.current_drawdown >= self.max_drawdown_pct:
            return False, f"達到最大回撤上限 {self.max_drawdown_pct:.1%}"
        
        return True, "可以交易"
    
    def reset_daily_pnl(self):
        """重置每日損益（在每個交易日開始時調用）"""
        self.daily_pnl = 0.0
        self.logger.info("每日損益已重置")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        獲取資金保護統計
        
        Returns:
            包含統計資訊的字典
        """
        total_pnl = self.current_capital - self.initial_capital
        total_return = (total_pnl / self.initial_capital) * 100
        
        # 計算勝率
        winning_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
        total_trades = len(self.trade_history)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 計算平均獲利/虧損
        profits = [t['pnl'] for t in self.trade_history if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trade_history if t['pnl'] < 0]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = abs(sum(profits) / sum(losses)) if losses and sum(losses) != 0 else 0
        
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'total_pnl': total_pnl,
            'total_return_pct': total_return,
            'current_drawdown_pct': self.current_drawdown * 100,
            'max_drawdown_pct': self.max_drawdown_reached * 100,
            'peak_capital': self.peak_capital,
            'trading_status': self.trading_status.value,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate_pct': win_rate,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'position_size_multiplier': self.get_position_size_multiplier()
        }
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """
        獲取資金曲線 DataFrame
        
        Returns:
            資金曲線資料
        """
        return pd.DataFrame({
            'timestamp': self.equity_dates,
            'equity': self.equity_curve
        })
    
    def plot_equity_curve(self, save_path: Optional[str] = None):
        """
        繪製資金曲線圖（需要 matplotlib）
        
        Args:
            save_path: 儲存路徑，如果為 None 則顯示圖表
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            
            # 資金曲線
            ax1.plot(self.equity_dates, self.equity_curve, 'b-', linewidth=2)
            ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', label='初始資金')
            ax1.set_ylabel('資金 (元)', fontsize=12)
            ax1.set_title('資金曲線', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # 回撤曲線
            drawdowns = [(self.peak_capital - eq) / self.peak_capital * 100 
                        for eq in self.equity_curve]
            ax2.fill_between(self.equity_dates, 0, drawdowns, color='red', alpha=0.3)
            ax2.plot(self.equity_dates, drawdowns, 'r-', linewidth=1)
            ax2.axhline(y=-self.max_drawdown_pct * 100, color='darkred', 
                       linestyle='--', label=f'最大回撤限制 ({self.max_drawdown_pct*100:.0f}%)')
            ax2.set_ylabel('回撤 (%)', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_title('回撤曲線', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # 格式化 x 軸
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"資金曲線圖已儲存至: {save_path}")
            else:
                plt.show()
            
            plt.close()
            
        except ImportError:
            self.logger.warning("無法繪製圖表: matplotlib 未安裝")
    
    def export_report(self, filepath: str):
        """
        匯出詳細報告
        
        Args:
            filepath: 報告儲存路徑
        """
        stats = self.get_statistics()
        
        report = f"""
{'='*80}
資金保護系統報告
{'='*80}

【資金狀況】
  初始資金: {stats['initial_capital']:,.0f} 元
  當前資金: {stats['current_capital']:,.0f} 元
  總損益: {stats['total_pnl']:,.0f} 元 ({stats['total_return_pct']:+.2f}%)
  高峰資金: {stats['peak_capital']:,.0f} 元

【風險指標】
  當前回撤: {stats['current_drawdown_pct']:.2f}%
  最大回撤: {stats['max_drawdown_pct']:.2f}%
  回撤上限: {self.max_drawdown_pct*100:.0f}%

【交易統計】
  總交易次數: {stats['total_trades']}
  獲利次數: {stats['winning_trades']}
  虧損次數: {stats['losing_trades']}
  勝率: {stats['win_rate_pct']:.1f}%
  
【績效指標】
  平均獲利: {stats['avg_profit']:,.0f} 元
  平均虧損: {stats['avg_loss']:,.0f} 元
  獲利因子: {stats['profit_factor']:.2f}
  
【當前狀態】
  交易狀態: {stats['trading_status']}
  連續獲利: {stats['consecutive_wins']} 次
  連續虧損: {stats['consecutive_losses']} 次
  部位乘數: {stats['position_size_multiplier']:.2f}

{'='*80}
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"報告已匯出至: {filepath}")


if __name__ == "__main__":
    # 測試範例
    print("=" * 80)
    print("資金曲線保護系統測試")
    print("=" * 80)
    
    # 創建保護系統
    protection = EquityProtection(
        initial_capital=1000000,
        max_daily_loss_pct=2.0,
        max_drawdown_pct=10.0,
        consecutive_loss_limit=3
    )
    
    # 模擬交易序列
    trades = [
        ('2024-01-01', 5000),   # 獲利
        ('2024-01-02', -3000),  # 虧損
        ('2024-01-03', -4000),  # 虧損
        ('2024-01-04', -5000),  # 虧損（連續3次）
        ('2024-01-05', 2000),   # 獲利
        ('2024-01-06', 3000),   # 獲利
    ]
    
    print("\n模擬交易序列:")
    for date_str, pnl in trades:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        result = protection.update_equity(pnl, date)
        
        print(f"\n{date_str}:")
        print(f"  損益: {pnl:+,.0f} 元")
        print(f"  資金: {result['current_capital']:,.0f} 元")
        print(f"  回撤: {result['current_drawdown']:.2%}")
        print(f"  狀態: {result['trading_status']}")
        print(f"  部位乘數: {result['position_size_multiplier']:.2f}")
        
        can_trade, reason = protection.can_trade()
        print(f"  可交易: {'是' if can_trade else '否'} ({reason})")
    
    # 顯示統計
    print("\n" + "=" * 80)
    print("最終統計")
    print("=" * 80)
    stats = protection.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")
