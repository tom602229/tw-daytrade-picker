"""
回測系統框架 - Backtesting Framework
用歷史資料驗證策略有效性
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易記錄"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    commission: float
    exit_reason: str  # 'STOP_LOSS', 'TAKE_PROFIT', 'SIGNAL', 'TIMEOUT'


@dataclass
class BacktestConfig:
    """回測配置"""
    initial_capital: float = 1_000_000  # 初始資金
    commission_rate: float = 0.001425   # 手續費率 0.1425%
    tax_rate: float = 0.003             # 證交稅 0.3% (賣出時)
    slippage: float = 0.001             # 滑價 0.1%
    
    # 風控參數
    max_position_size_pct: float = 10.0  # 單筆最大部位 %
    max_risk_per_trade_pct: float = 2.0  # 單筆最大風險 %
    max_open_positions: int = 3          # 最大同時持倉數
    
    # 停損停利
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 6.0


class BacktestResult:
    """回測結果"""
    
    def __init__(self, trades: List[Trade], config: BacktestConfig):
        self.trades = trades
        self.config = config
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """計算績效指標"""
        if not self.trades:
            self.total_trades = 0
            self.winning_trades = 0
            self.losing_trades = 0
            self.win_rate = 0
            self.total_pnl = 0
            self.total_return_pct = 0
            self.avg_win = 0
            self.avg_loss = 0
            self.profit_factor = 0
            self.max_drawdown = 0
            self.sharpe_ratio = 0
            self.max_consecutive_wins = 0
            self.max_consecutive_losses = 0
            return
        
        # 基本統計
        self.total_trades = len(self.trades)
        self.winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        self.losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # 損益
        self.total_pnl = sum(t.pnl for t in self.trades)
        self.total_return_pct = (self.total_pnl / self.config.initial_capital) * 100
        
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        self.avg_win = np.mean(wins) if wins else 0
        self.avg_loss = np.mean(losses) if losses else 0
        
        total_win = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 0
        self.profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        # 計算資金曲線和最大回撤
        capital_curve = [self.config.initial_capital]
        for trade in self.trades:
            capital_curve.append(capital_curve[-1] + trade.pnl)
        
        peak = capital_curve[0]
        max_dd = 0
        for capital in capital_curve:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        self.max_drawdown = max_dd
        self.capital_curve = capital_curve
        
        # Sharpe Ratio (簡化版，假設無風險利率為 0)
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            self.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            self.sharpe_ratio = 0
        
        # 連續勝負
        consecutive_wins = 0
        consecutive_losses = 0
        max_cons_wins = 0
        max_cons_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_cons_wins = max(max_cons_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_cons_losses = max(max_cons_losses, consecutive_losses)
        
        self.max_consecutive_wins = max_cons_wins
        self.max_consecutive_losses = max_cons_losses
    
    def print_summary(self):
        """印出回測摘要"""
        print("=" * 70)
        print("回測結果摘要")
        print("=" * 70)
        print(f"初始資金: ${self.config.initial_capital:,.0f}")
        print(f"最終資金: ${self.config.initial_capital + self.total_pnl:,.0f}")
        print(f"總損益: ${self.total_pnl:+,.0f} ({self.total_return_pct:+.2f}%)")
        print(f"\n交易統計:")
        print(f"  總交易次數: {self.total_trades}")
        print(f"  獲利次數: {self.winning_trades}")
        print(f"  虧損次數: {self.losing_trades}")
        print(f"  勝率: {self.win_rate:.2f}%")
        print(f"\n損益分析:")
        print(f"  平均獲利: ${self.avg_win:+,.0f}")
        print(f"  平均虧損: ${self.avg_loss:+,.0f}")
        print(f"  獲利因子: {self.profit_factor:.2f}")
        print(f"\n風險指標:")
        print(f"  最大回撤: {self.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print(f"  最大連勝: {self.max_consecutive_wins} 次")
        print(f"  最大連敗: {self.max_consecutive_losses} 次")
        print("=" * 70)
    
    def get_trade_details(self) -> pd.DataFrame:
        """獲取交易明細"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame([
            {
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'quantity': t.quantity,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'exit_reason': t.exit_reason
            }
            for t in self.trades
        ])


class Backtester:
    """回測引擎"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.trades: List[Trade] = []
        self.current_capital = config.initial_capital
        self.positions: Dict[str, Dict] = {}  # 當前持倉
    
    def calculate_commission(self, price: float, quantity: int, is_sell: bool = False) -> float:
        """計算手續費和稅"""
        value = price * quantity
        commission = value * self.config.commission_rate
        
        # 賣出時加上證交稅
        if is_sell:
            tax = value * self.config.tax_rate
            commission += tax
        
        return commission
    
    def can_open_position(self) -> bool:
        """檢查是否可以開新倉"""
        return len(self.positions) < self.config.max_open_positions
    
    def calculate_position_size(self, price: float) -> int:
        """計算建議持倉數量"""
        # 根據風險百分比計算
        risk_amount = self.current_capital * (self.config.max_risk_per_trade_pct / 100)
        price_risk = price * (self.config.stop_loss_pct / 100)
        quantity = int(risk_amount / price_risk)
        
        # 檢查最大部位限制
        max_position_value = self.current_capital * (self.config.max_position_size_pct / 100)
        max_quantity = int(max_position_value / price)
        
        if quantity > max_quantity:
            quantity = max_quantity
        
        # 調整為 1000 的倍數（整張）
        if quantity >= 1000:
            quantity = (quantity // 1000) * 1000
        else:
            quantity = 1000  # 至少 1 張
        
        return quantity
    
    def open_position(self, symbol: str, price: float, timestamp: datetime, 
                     signal_data: Optional[Dict] = None) -> bool:
        """開倉"""
        if not self.can_open_position():
            logger.warning(f"{timestamp}: 無法開倉 {symbol}，已達最大持倉數")
            return False
        
        quantity = self.calculate_position_size(price)
        
        # 考慮滑價
        actual_price = price * (1 + self.config.slippage)
        
        # 計算手續費
        commission = self.calculate_commission(actual_price, quantity, is_sell=False)
        
        # 檢查資金是否足夠
        required_capital = actual_price * quantity + commission
        if required_capital > self.current_capital:
            logger.warning(f"{timestamp}: 資金不足，無法開倉 {symbol}")
            return False
        
        # 計算停損停利價
        stop_loss = actual_price * (1 - self.config.stop_loss_pct / 100)
        take_profit = actual_price * (1 + self.config.take_profit_pct / 100)
        
        # 記錄持倉
        self.positions[symbol] = {
            'entry_time': timestamp,
            'entry_price': actual_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_paid': commission,
            'signal_data': signal_data
        }
        
        # 扣除資金
        self.current_capital -= required_capital
        
        logger.info(f"{timestamp}: 開倉 {symbol} @ {actual_price:.2f}, 數量 {quantity}")
        return True
    
    def close_position(self, symbol: str, price: float, timestamp: datetime, 
                      reason: str = 'SIGNAL') -> Optional[Trade]:
        """平倉"""
        if symbol not in self.positions:
            logger.warning(f"{timestamp}: 無此持倉 {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # 考慮滑價
        actual_price = price * (1 - self.config.slippage)
        
        # 計算手續費和稅
        commission = self.calculate_commission(actual_price, position['quantity'], is_sell=True)
        total_commission = position['commission_paid'] + commission
        
        # 計算損益
        pnl = (actual_price - position['entry_price']) * position['quantity'] - total_commission
        pnl_pct = ((actual_price - position['entry_price']) / position['entry_price']) * 100
        
        # 回收資金
        proceeds = actual_price * position['quantity'] - commission
        self.current_capital += proceeds
        
        # 記錄交易
        trade = Trade(
            entry_time=position['entry_time'],
            exit_time=timestamp,
            symbol=symbol,
            direction='LONG',
            entry_price=position['entry_price'],
            exit_price=actual_price,
            quantity=position['quantity'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=total_commission,
            exit_reason=reason
        )
        
        self.trades.append(trade)
        
        # 移除持倉
        del self.positions[symbol]
        
        logger.info(f"{timestamp}: 平倉 {symbol} @ {actual_price:.2f}, "
                   f"損益 {pnl:+.0f} ({pnl_pct:+.2f}%), 原因: {reason}")
        
        return trade
    
    def check_exit_conditions(self, symbol: str, current_price: float, 
                             timestamp: datetime) -> Optional[str]:
        """檢查出場條件"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # 檢查停損
        if current_price <= position['stop_loss']:
            return 'STOP_LOSS'
        
        # 檢查停利
        if current_price >= position['take_profit']:
            return 'TAKE_PROFIT'
        
        return None
    
    def run(self, data: pd.DataFrame, strategy_func: Callable) -> BacktestResult:
        """
        執行回測
        
        Args:
            data: 股票資料，需包含 Date, Open, High, Low, Close, Volume
            strategy_func: 策略函數，簽名為 func(df, index) -> {'signal': 'BUY'|'SELL'|'HOLD', ...}
        
        Returns:
            BacktestResult
        """
        logger.info(f"開始回測，資料期間: {data['Date'].iloc[0]} 到 {data['Date'].iloc[-1]}")
        
        for i in range(60, len(data)):  # 從第 60 天開始（需要足夠歷史資料）
            current_date = data['Date'].iloc[i]
            current_price = data['Close'].iloc[i]
            high_price = data['High'].iloc[i]
            low_price = data['Low'].iloc[i]
            
            # 檢查現有持倉的停損停利
            symbols_to_close = []
            for symbol in list(self.positions.keys()):
                # 先檢查最低價是否觸發停損
                if low_price <= self.positions[symbol]['stop_loss']:
                    symbols_to_close.append((symbol, self.positions[symbol]['stop_loss'], 'STOP_LOSS'))
                # 再檢查最高價是否觸發停利
                elif high_price >= self.positions[symbol]['take_profit']:
                    symbols_to_close.append((symbol, self.positions[symbol]['take_profit'], 'TAKE_PROFIT'))
            
            # 平倉
            for symbol, exit_price, reason in symbols_to_close:
                self.close_position(symbol, exit_price, current_date, reason)
            
            # 獲取策略訊號（使用截至當前的歷史資料）
            historical_data = data.iloc[:i+1].copy()
            signal = strategy_func(historical_data, i)
            
            # 執行交易
            if signal['signal'] == 'BUY' and self.can_open_position():
                # 假設股票代號
                symbol = data.get('Symbol', ['STOCK'])[0] if 'Symbol' in data.columns else 'STOCK'
                self.open_position(symbol, current_price, current_date, signal)
            
            elif signal['signal'] == 'SELL':
                # 平掉所有持倉
                for symbol in list(self.positions.keys()):
                    self.close_position(symbol, current_price, current_date, 'SIGNAL')
        
        # 回測結束，平掉所有剩餘持倉
        final_date = data['Date'].iloc[-1]
        final_price = data['Close'].iloc[-1]
        for symbol in list(self.positions.keys()):
            self.close_position(symbol, final_price, final_date, 'END_OF_BACKTEST')
        
        logger.info(f"回測完成，共 {len(self.trades)} 筆交易")
        
        return BacktestResult(self.trades, self.config)


# 使用範例
if __name__ == "__main__":
    # 生成模擬資料
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 2)
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices * (1 + np.random.randn(len(dates)) * 0.01),
        'High': prices * (1 + abs(np.random.randn(len(dates))) * 0.02),
        'Low': prices * (1 - abs(np.random.randn(len(dates))) * 0.02),
        'Close': prices,
        'Volume': np.random.randint(100_000, 300_000, len(dates))
    })
    
    # 定義簡單的策略（RSI 超賣買入）
    def simple_rsi_strategy(data: pd.DataFrame, index: int) -> Dict:
        # 計算 RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[index]
        
        if current_rsi < 30:
            return {'signal': 'BUY'}
        elif current_rsi > 70:
            return {'signal': 'SELL'}
        else:
            return {'signal': 'HOLD'}
    
    # 初始化回測
    config = BacktestConfig(
        initial_capital=1_000_000,
        stop_loss_pct=3.0,
        take_profit_pct=6.0
    )
    
    backtester = Backtester(config)
    
    # 執行回測
    result = backtester.run(df, simple_rsi_strategy)
    
    # 印出結果
    result.print_summary()
    
    # 獲取交易明細
    trade_df = result.get_trade_details()
    print(f"\n前 5 筆交易:")
    print(trade_df.head())
