"""
交易日誌記錄模組 - Trade Logging Module
記錄所有交易細節，用於分析和改進策略
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradeLog:
    """交易日誌記錄"""
    # 基本資訊
    timestamp: str
    symbol: str
    action: str  # 'OPEN', 'CLOSE', 'ALERT'
    
    # 價格資訊
    price: float
    quantity: Optional[int] = None
    
    # 訊號資訊
    signal_type: Optional[str] = None  # 'BUY', 'SELL', 'HOLD'
    signal_score: Optional[float] = None
    
    # 技術指標
    rsi: Optional[float] = None
    williams_r: Optional[float] = None
    obv_signal: Optional[str] = None
    
    # 籌碼資訊
    foreign_net: Optional[float] = None
    trust_net: Optional[float] = None
    dealer_net: Optional[float] = None
    institutional_consensus: Optional[str] = None
    
    # 市場環境
    market_trend: Optional[str] = None
    market_sentiment: Optional[str] = None
    
    # 風控資訊
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: Optional[float] = None
    
    # 結果（平倉時填寫）
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    holding_period: Optional[str] = None
    
    # 備註
    notes: Optional[str] = None


class TradeLogger:
    """交易日誌管理器"""
    
    def __init__(self, log_dir: str = "./logs/trades"):
        """
        初始化交易日誌器
        
        Args:
            log_dir: 日誌儲存目錄
        """
        self.log_dir = log_dir
        self.logs: List[TradeLog] = []
        
        # 建立目錄
        os.makedirs(log_dir, exist_ok=True)
        
        # 當日檔案名稱
        self.today_file = os.path.join(
            log_dir, 
            f"trades_{datetime.now().strftime('%Y%m%d')}.json"
        )
        
        # 載入當日已存在的日誌
        self._load_today_logs()
    
    def _load_today_logs(self):
        """載入當日的日誌"""
        if os.path.exists(self.today_file):
            try:
                with open(self.today_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logs = [TradeLog(**log) for log in data]
                logger.info(f"已載入 {len(self.logs)} 筆當日交易日誌")
            except Exception as e:
                logger.error(f"載入日誌失敗: {e}")
                self.logs = []
    
    def log_signal(self, symbol: str, signal_type: str, price: float,
                   score: float, technical: Dict, chip: Dict, 
                   market: Dict, notes: str = "") -> TradeLog:
        """
        記錄交易訊號
        
        Args:
            symbol: 股票代號
            signal_type: 訊號類型 ('BUY', 'SELL', 'HOLD')
            price: 當前價格
            score: 訊號分數
            technical: 技術指標字典
            chip: 籌碼資料字典
            market: 市場環境字典
            notes: 備註
        """
        log = TradeLog(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            action='ALERT',
            price=price,
            signal_type=signal_type,
            signal_score=score,
            rsi=technical.get('rsi'),
            williams_r=technical.get('williams_r'),
            obv_signal=chip.get('obv_signal'),
            foreign_net=chip.get('institutional', {}).get('foreign_net') if chip.get('institutional') else None,
            institutional_consensus=chip.get('institutional', {}).get('consensus') if chip.get('institutional') else None,
            market_trend=market.get('trend'),
            market_sentiment=market.get('sentiment'),
            notes=notes
        )
        
        self.logs.append(log)
        self._save_log(log)
        
        logger.info(f"記錄訊號: {symbol} {signal_type} @ {price:.2f}, 分數 {score}")
        return log
    
    def log_entry(self, symbol: str, price: float, quantity: int,
                  stop_loss: float, take_profit: float, 
                  position_size_pct: float, technical: Dict, 
                  chip: Dict, market: Dict, notes: str = "") -> TradeLog:
        """
        記錄進場
        """
        log = TradeLog(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            action='OPEN',
            price=price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_pct=position_size_pct,
            rsi=technical.get('rsi'),
            williams_r=technical.get('williams_r'),
            obv_signal=chip.get('obv_signal'),
            foreign_net=chip.get('institutional', {}).get('foreign_net') if chip.get('institutional') else None,
            institutional_consensus=chip.get('institutional', {}).get('consensus') if chip.get('institutional') else None,
            market_trend=market.get('trend'),
            market_sentiment=market.get('sentiment'),
            notes=notes
        )
        
        self.logs.append(log)
        self._save_log(log)
        
        logger.info(f"記錄進場: {symbol} {quantity} 股 @ {price:.2f}")
        return log
    
    def log_exit(self, symbol: str, price: float, quantity: int,
                 pnl: float, pnl_pct: float, exit_reason: str,
                 entry_time: datetime, notes: str = "") -> TradeLog:
        """
        記錄出場
        """
        holding_period = str(datetime.now() - entry_time)
        
        log = TradeLog(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            action='CLOSE',
            price=price,
            quantity=quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            holding_period=holding_period,
            notes=notes
        )
        
        self.logs.append(log)
        self._save_log(log)
        
        logger.info(f"記錄出場: {symbol} @ {price:.2f}, "
                   f"損益 {pnl:+.0f} ({pnl_pct:+.2f}%), 原因: {exit_reason}")
        return log
    
    def _save_log(self, log: TradeLog):
        """儲存單筆日誌到檔案"""
        try:
            # 讀取現有資料
            if os.path.exists(self.today_file):
                with open(self.today_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # 加入新日誌
            data.append(asdict(log))
            
            # 寫入檔案
            with open(self.today_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"儲存日誌失敗: {e}")
    
    def get_today_logs(self, action: Optional[str] = None) -> List[TradeLog]:
        """
        獲取當日日誌
        
        Args:
            action: 過濾條件 ('OPEN', 'CLOSE', 'ALERT')
        """
        if action:
            return [log for log in self.logs if log.action == action]
        return self.logs
    
    def get_trade_summary(self, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Dict:
        """
        生成交易摘要
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        """
        # 取得所有平倉記錄
        closed_trades = [log for log in self.logs if log.action == 'CLOSE' and log.pnl is not None]
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        winning = [log for log in closed_trades if log.pnl > 0]
        losing = [log for log in closed_trades if log.pnl < 0]
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': (len(winning) / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': sum(log.pnl for log in closed_trades),
            'avg_pnl': sum(log.pnl for log in closed_trades) / len(closed_trades),
            'avg_win': sum(log.pnl for log in winning) / len(winning) if winning else 0,
            'avg_loss': sum(log.pnl for log in losing) / len(losing) if losing else 0,
            'best_trade': max(log.pnl for log in closed_trades),
            'worst_trade': min(log.pnl for log in closed_trades)
        }
    
    def generate_daily_report(self) -> str:
        """生成每日報表"""
        summary = self.get_trade_summary()
        
        signals = [log for log in self.logs if log.action == 'ALERT']
        entries = [log for log in self.logs if log.action == 'OPEN']
        exits = [log for log in self.logs if log.action == 'CLOSE']
        
        report = f"""
{'='*70}
每日交易報表 - {datetime.now().strftime('%Y-%m-%d')}
{'='*70}

訊號統計:
  總訊號數: {len(signals)}
  買入訊號: {len([s for s in signals if s.signal_type == 'BUY'])}
  賣出訊號: {len([s for s in signals if s.signal_type == 'SELL'])}

交易統計:
  進場次數: {len(entries)}
  出場次數: {len(exits)}
  
損益統計:
  總交易: {summary['total_trades']} 筆
  獲利: {summary['winning_trades']} 筆
  虧損: {summary['losing_trades']} 筆
  勝率: {summary['win_rate']:.2f}%
  總損益: ${summary['total_pnl']:+,.0f}
  平均損益: ${summary['avg_pnl']:+,.0f}
  平均獲利: ${summary['avg_win']:+,.0f}
  平均虧損: ${summary['avg_loss']:+,.0f}
  最佳交易: ${summary.get('best_trade', 0):+,.0f}
  最差交易: ${summary.get('worst_trade', 0):+,.0f}

{'='*70}
"""
        return report
    
    def export_to_csv(self, filename: Optional[str] = None) -> str:
        """
        匯出日誌為 CSV
        
        Returns:
            CSV 檔案路徑
        """
        if not filename:
            filename = f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
        
        filepath = os.path.join(self.log_dir, filename)
        
        # 轉換為 DataFrame
        df = pd.DataFrame([asdict(log) for log in self.logs])
        
        # 儲存
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"已匯出 {len(self.logs)} 筆日誌至 {filepath}")
        return filepath
    
    def print_report(self):
        """印出每日報表"""
        print(self.generate_daily_report())


# 使用範例
if __name__ == "__main__":
    # 初始化日誌器
    trade_logger = TradeLogger(log_dir="./logs/trades")
    
    # 記錄訊號
    trade_logger.log_signal(
        symbol="2330",
        signal_type="BUY",
        price=500.0,
        score=85.0,
        technical={'rsi': 28.5, 'williams_r': -85.2},
        chip={'obv_signal': 'bullish', 'institutional': {'consensus': '法人一致買超'}},
        market={'trend': '多頭', 'sentiment': '中性'},
        notes="RSI 超賣，法人買超"
    )
    
    # 記錄進場
    trade_logger.log_entry(
        symbol="2330",
        price=501.0,
        quantity=2000,
        stop_loss=485.0,
        take_profit=531.0,
        position_size_pct=10.0,
        technical={'rsi': 29.0, 'williams_r': -84.0},
        chip={'obv_signal': 'bullish'},
        market={'trend': '多頭'},
        notes="依訊號進場"
    )
    
    # 記錄出場
    trade_logger.log_exit(
        symbol="2330",
        price=532.0,
        quantity=2000,
        pnl=62000,
        pnl_pct=6.19,
        exit_reason="TAKE_PROFIT",
        entry_time=datetime.now(),
        notes="觸及停利"
    )
    
    # 印出報表
    trade_logger.print_report()
    
    # 匯出 CSV
    csv_file = trade_logger.export_to_csv()
    print(f"\n已匯出至: {csv_file}")
