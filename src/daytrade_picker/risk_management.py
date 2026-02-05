"""
風險控管模組 - Risk Management Module
包含停損停利、部位管理、最大回撤控制
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """持倉資訊"""
    symbol: str
    entry_price: float
    quantity: int
    entry_time: datetime
    stop_loss: float
    take_profit: float
    position_size_pct: float  # 佔總資金百分比


@dataclass
class RiskConfig:
    """風控配置"""
    # 單筆交易風險
    max_position_size_pct: float = 10.0  # 單筆最大部位 (%)
    max_risk_per_trade_pct: float = 2.0  # 單筆最大風險 (%)
    
    # 停損停利
    default_stop_loss_pct: float = 3.0   # 預設停損 (%)
    default_take_profit_pct: float = 6.0 # 預設停利 (%)
    trailing_stop_pct: float = 2.0       # 移動停利 (%)
    
    # 整體風控
    max_daily_loss_pct: float = 5.0      # 單日最大虧損 (%)
    max_drawdown_pct: float = 15.0       # 最大回撤 (%)
    max_open_positions: int = 3          # 最大同時持倉數
    
    # 連續虧損控制
    max_consecutive_losses: int = 3      # 最大連續虧損次數
    cooldown_period_minutes: int = 60    # 冷靜期（分鐘）


class RiskManager:
    """風險管理器"""
    
    def __init__(self, config: RiskConfig, initial_capital: float):
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.consecutive_losses = 0
        self.last_loss_time: Optional[datetime] = None
        self.trade_history: List[Dict] = []
        
    def can_open_position(self) -> tuple[bool, str]:
        """
        檢查是否可以開新倉
        Returns: (是否可開倉, 原因)
        """
        # 檢查持倉數量
        if len(self.positions) >= self.config.max_open_positions:
            return False, f"已達最大持倉數 {self.config.max_open_positions}"
        
        # 檢查單日虧損
        daily_loss_pct = (self.daily_pnl / self.initial_capital) * 100
        if daily_loss_pct <= -self.config.max_daily_loss_pct:
            return False, f"觸及單日最大虧損 {self.config.max_daily_loss_pct}%"
        
        # 檢查最大回撤
        drawdown_pct = ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
        if drawdown_pct >= self.config.max_drawdown_pct:
            return False, f"觸及最大回撤 {self.config.max_drawdown_pct}%"
        
        # 檢查連續虧損冷靜期
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            if self.last_loss_time:
                cooldown_end = self.last_loss_time.timestamp() + (self.config.cooldown_period_minutes * 60)
                if datetime.now().timestamp() < cooldown_end:
                    remaining = int((cooldown_end - datetime.now().timestamp()) / 60)
                    return False, f"連續虧損 {self.consecutive_losses} 次，冷靜期剩餘 {remaining} 分鐘"
                else:
                    # 冷靜期結束，重置計數
                    self.consecutive_losses = 0
        
        return True, "可開倉"
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss_pct: Optional[float] = None) -> tuple[int, float]:
        """
        計算建議持倉數量
        Returns: (股數, 停損價)
        """
        if stop_loss_pct is None:
            stop_loss_pct = self.config.default_stop_loss_pct
        
        # 根據風險百分比計算
        risk_amount = self.current_capital * (self.config.max_risk_per_trade_pct / 100)
        price_risk = entry_price * (stop_loss_pct / 100)
        quantity = int(risk_amount / price_risk)
        
        # 檢查是否超過最大部位
        max_position_value = self.current_capital * (self.config.max_position_size_pct / 100)
        max_quantity = int(max_position_value / entry_price)
        
        if quantity > max_quantity:
            quantity = max_quantity
            logger.warning(f"{symbol}: 根據最大部位限制，調整數量從 {quantity} 到 {max_quantity}")
        
        # 確保至少買 1 張（1000 股）
        if quantity < 1000:
            logger.warning(f"{symbol}: 計算數量 {quantity} 小於 1 張，調整為 1000 股")
            quantity = 1000
        else:
            # 調整為 1000 的倍數（整張）
            quantity = (quantity // 1000) * 1000
        
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        
        return quantity, stop_loss_price
    
    def open_position(self, symbol: str, entry_price: float, quantity: int,
                     stop_loss: float, take_profit: Optional[float] = None) -> bool:
        """
        開倉
        """
        if symbol in self.positions:
            logger.warning(f"{symbol} 已有持倉，無法重複開倉")
            return False
        
        can_open, reason = self.can_open_position()
        if not can_open:
            logger.warning(f"無法開倉 {symbol}: {reason}")
            return False
        
        position_value = entry_price * quantity
        position_size_pct = (position_value / self.current_capital) * 100
        
        if take_profit is None:
            take_profit = entry_price * (1 + self.config.default_take_profit_pct / 100)
        
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_pct=position_size_pct
        )
        
        self.positions[symbol] = position
        logger.info(f"開倉 {symbol}: 價格 {entry_price}, 數量 {quantity}, "
                   f"停損 {stop_loss:.2f}, 停利 {take_profit:.2f}")
        return True
    
    def check_exit_signals(self, symbol: str, current_price: float) -> tuple[bool, str]:
        """
        檢查是否需要出場
        Returns: (是否出場, 原因)
        """
        if symbol not in self.positions:
            return False, "無此持倉"
        
        position = self.positions[symbol]
        
        # 檢查停損
        if current_price <= position.stop_loss:
            return True, f"觸及停損 {position.stop_loss:.2f}"
        
        # 檢查停利
        if current_price >= position.take_profit:
            return True, f"觸及停利 {position.take_profit:.2f}"
        
        # 移動停利（當價格上漲超過一定幅度時）
        profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        if profit_pct > self.config.trailing_stop_pct * 2:
            new_stop = position.entry_price * (1 + self.config.trailing_stop_pct / 100)
            if new_stop > position.stop_loss:
                position.stop_loss = new_stop
                logger.info(f"{symbol} 移動停利至 {new_stop:.2f}")
        
        return False, "持有中"
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "") -> Dict:
        """
        平倉
        """
        if symbol not in self.positions:
            logger.warning(f"無法平倉 {symbol}: 無此持倉")
            return {}
        
        position = self.positions[symbol]
        pnl = (exit_price - position.entry_price) * position.quantity
        pnl_pct = ((exit_price - position.entry_price) / position.entry_price) * 100
        
        # 更新資金
        self.current_capital += pnl
        self.daily_pnl += pnl
        
        # 更新峰值
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # 更新連續虧損
        if pnl < 0:
            self.consecutive_losses += 1
            self.last_loss_time = datetime.now()
        else:
            self.consecutive_losses = 0
        
        # 記錄交易
        trade_record = {
            'symbol': symbol,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        }
        self.trade_history.append(trade_record)
        
        logger.info(f"平倉 {symbol}: 進場 {position.entry_price:.2f}, 出場 {exit_price:.2f}, "
                   f"損益 {pnl:+.0f} ({pnl_pct:+.2f}%), 原因: {reason}")
        
        # 移除持倉
        del self.positions[symbol]
        
        return trade_record
    
    def get_status(self) -> Dict:
        """獲取當前狀態"""
        drawdown_pct = ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
        daily_loss_pct = (self.daily_pnl / self.initial_capital) * 100
        
        return {
            'current_capital': self.current_capital,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': daily_loss_pct,
            'total_pnl': self.current_capital - self.initial_capital,
            'total_pnl_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'drawdown_pct': drawdown_pct,
            'open_positions': len(self.positions),
            'consecutive_losses': self.consecutive_losses,
            'total_trades': len(self.trade_history)
        }
    
    def reset_daily_pnl(self):
        """重置單日損益（每天開盤前調用）"""
        self.daily_pnl = 0.0
        logger.info("已重置單日損益")


# 使用範例
if __name__ == "__main__":
    # 初始化風控配置
    config = RiskConfig(
        max_position_size_pct=10.0,
        max_risk_per_trade_pct=2.0,
        max_daily_loss_pct=5.0,
        max_consecutive_losses=3
    )
    
    # 初始化風險管理器（100 萬資金）
    risk_manager = RiskManager(config, initial_capital=1_000_000)
    
    # 計算建議持倉
    symbol = "2330"  # 台積電
    entry_price = 500.0
    quantity, stop_loss = risk_manager.calculate_position_size(symbol, entry_price)
    
    print(f"建議買入 {symbol}: {quantity} 股, 停損價 {stop_loss:.2f}")
    
    # 開倉
    take_profit = entry_price * 1.06  # 6% 停利
    risk_manager.open_position(symbol, entry_price, quantity, stop_loss, take_profit)
    
    # 檢查狀態
    print(risk_manager.get_status())
