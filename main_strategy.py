"""
主程式 - 整合所有優化模組
Enhanced Day Trading Strategy - Main Program
"""
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging

# 導入自定義模組
from risk_management import RiskManager, RiskConfig
from market_environment import MarketAnalyzer, MarketEnvironment
from enhanced_strategy import EnhancedStrategyC, ChipAnalyzer
from multi_timeframe import MultiTimeFrameAnalyzer, TimeFrame
from backtesting import Backtester, BacktestConfig
from trade_logger import TradeLogger

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedDayTradingSystem:
    """增強版當沖交易系統"""
    
    def __init__(self, config_path: str = "config_enhanced.yml"):
        """
        初始化交易系統
        
        Args:
            config_path: 配置檔路徑
        """
        # 載入配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        logger.info(f"載入配置: {self.config['strategy']['name']} v{self.config['strategy']['version']}")
        
        # 初始化各模組
        self._init_modules()
    
    def _init_modules(self):
        """初始化所有模組"""
        # 1. 風險管理器
        risk_cfg = RiskConfig(
            max_position_size_pct=self.config['risk_management']['max_position_size_pct'],
            max_risk_per_trade_pct=self.config['risk_management']['max_risk_per_trade_pct'],
            default_stop_loss_pct=self.config['risk_management']['default_stop_loss_pct'],
            default_take_profit_pct=self.config['risk_management']['default_take_profit_pct'],
            trailing_stop_pct=self.config['risk_management']['trailing_stop_pct'],
            max_daily_loss_pct=self.config['risk_management']['max_daily_loss_pct'],
            max_drawdown_pct=self.config['risk_management']['max_drawdown_pct'],
            max_open_positions=self.config['risk_management']['max_open_positions'],
            max_consecutive_losses=self.config['risk_management']['max_consecutive_losses'],
            cooldown_period_minutes=self.config['risk_management']['cooldown_period_minutes']
        )
        self.risk_manager = RiskManager(risk_cfg, self.config['capital']['initial_capital'])
        
        # 2. 市場分析器
        self.market_analyzer = MarketAnalyzer()
        
        # 3. 增強策略
        strategy_cfg = {
            'rsi_period': self.config['technical_indicators']['rsi']['period'],
            'rsi_oversold': self.config['technical_indicators']['rsi']['oversold'],
            'rsi_overbought': self.config['technical_indicators']['rsi']['overbought'],
            'williams_period': self.config['technical_indicators']['williams']['period'],
            'williams_oversold': self.config['technical_indicators']['williams']['oversold'],
            'williams_overbought': self.config['technical_indicators']['williams']['overbought'],
            'obv_ma_period': self.config['chip_analysis']['obv']['ma_period'],
            'volume_ma_period': self.config['technical_indicators']['volume']['ma_period'],
            'volume_threshold': self.config['technical_indicators']['volume']['min_volume_ratio'],
            'institutional_threshold': self.config['chip_analysis']['institutional']['threshold_lots']
        }
        self.strategy = EnhancedStrategyC(strategy_cfg)
        
        # 4. 多時間框架分析器
        self.mtf_analyzer = MultiTimeFrameAnalyzer()
        
        # 5. 交易日誌
        self.trade_logger = TradeLogger(
            log_dir=self.config['logging']['save_path']
        )
        
        logger.info("所有模組初始化完成")
    
    def analyze_market_environment(self, index_df: pd.DataFrame, 
                                   vix_value: Optional[float] = None,
                                   foreign_net_buy: Optional[float] = None) -> MarketEnvironment:
        """
        分析市場環境
        
        Args:
            index_df: 大盤資料
            vix_value: VIX 恐慌指標
            foreign_net_buy: 外資買賣超金額
        
        Returns:
            MarketEnvironment 物件
        """
        env = self.market_analyzer.get_market_environment(
            index_df=index_df,
            vix_value=vix_value,
            foreign_net_buy=foreign_net_buy
        )
        
        # 檢查是否啟用市場過濾
        if self.config['market_environment']['enabled']:
            # 大盤過濾
            if self.config['market_environment']['index_filter']['require_above_ma20']:
                if not env.index_ma_status.get('above_ma20', False):
                    env.can_long = False
                    env.signals.append("✗ 大盤未站上月線，停止做多")
            
            # VIX 過濾
            if self.config['market_environment']['vix_filter']['enabled'] and vix_value:
                max_vix = self.config['market_environment']['vix_filter']['max_vix_for_long']
                if vix_value > max_vix:
                    env.can_long = False
                    env.signals.append(f"✗ VIX {vix_value} 超過 {max_vix}，市場恐慌")
        
        return env
    
    def scan_and_filter_stocks(self, stocks_data: Dict[str, pd.DataFrame],
                               institutional_data: Optional[Dict[str, Dict]] = None,
                               market_env: Optional[MarketEnvironment] = None) -> List[Dict]:
        """
        掃描並過濾股票
        
        Args:
            stocks_data: {股票代號: DataFrame}
            institutional_data: {股票代號: 法人資料}
            market_env: 市場環境
        
        Returns:
            符合條件的股票列表
        """
        # 市場環境過濾
        if market_env and not market_env.can_long:
            logger.warning("市場環境不適合做多，跳過選股")
            return []
        
        # 使用策略掃描
        results = self.strategy.scan_stocks(stocks_data, institutional_data)
        
        # 應用評分過濾
        min_score = self.config['scoring']['min_score_for_entry']
        filtered = [r for r in results if r['score'] >= min_score]
        
        logger.info(f"掃描 {len(stocks_data)} 檔股票，{len(filtered)} 檔符合條件（分數 >= {min_score}）")
        
        return filtered
    
    def execute_trade(self, symbol: str, analysis: Dict, 
                     market_env: MarketEnvironment) -> bool:
        """
        執行交易
        
        Args:
            symbol: 股票代號
            analysis: 分析結果
            market_env: 市場環境
        
        Returns:
            是否成功開倉
        """
        # 檢查是否可以開倉
        can_open, reason = self.risk_manager.can_open_position()
        if not can_open:
            logger.warning(f"無法開倉 {symbol}: {reason}")
            return False
        
        # 記錄訊號
        current_price = 100.0  # 實際應從市場取得
        self.trade_logger.log_signal(
            symbol=symbol,
            signal_type=analysis['signal'],
            price=current_price,
            score=analysis['score'],
            technical=analysis['technical'],
            chip=analysis['chip'],
            market={
                'trend': market_env.trend.value,
                'sentiment': market_env.sentiment.value
            },
            notes=', '.join(analysis['reasons'])
        )
        
        # 如果是買入訊號
        if analysis['signal'] == 'BUY':
            # 計算持倉數量和停損價
            quantity, stop_loss = self.risk_manager.calculate_position_size(
                symbol, current_price
            )
            
            # 計算停利價
            take_profit = current_price * (1 + self.risk_manager.config.default_take_profit_pct / 100)
            
            # 開倉
            success = self.risk_manager.open_position(
                symbol=symbol,
                entry_price=current_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if success:
                # 記錄進場
                position = self.risk_manager.positions[symbol]
                self.trade_logger.log_entry(
                    symbol=symbol,
                    price=current_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size_pct=position.position_size_pct,
                    technical=analysis['technical'],
                    chip=analysis['chip'],
                    market={
                        'trend': market_env.trend.value,
                        'sentiment': market_env.sentiment.value
                    },
                    notes=f"分數: {analysis['score']}"
                )
            
            return success
        
        return False
    
    def run_backtest(self, data: pd.DataFrame) -> None:
        """
        執行回測
        
        Args:
            data: 歷史資料
        """
        logger.info("開始回測...")
        
        # 建立回測配置
        bt_config = BacktestConfig(
            initial_capital=self.config['capital']['initial_capital'],
            commission_rate=self.config['costs']['commission_rate'],
            tax_rate=self.config['costs']['tax_rate'],
            slippage=self.config['costs']['slippage'],
            max_position_size_pct=self.config['risk_management']['max_position_size_pct'],
            max_risk_per_trade_pct=self.config['risk_management']['max_risk_per_trade_pct'],
            max_open_positions=self.config['risk_management']['max_open_positions'],
            stop_loss_pct=self.config['risk_management']['default_stop_loss_pct'],
            take_profit_pct=self.config['risk_management']['default_take_profit_pct']
        )
        
        # 定義策略函數
        def strategy_func(df: pd.DataFrame, index: int) -> Dict:
            analysis = self.strategy.analyze_stock(df)
            return {'signal': analysis['signal']}
        
        # 執行回測
        backtester = Backtester(bt_config)
        result = backtester.run(data, strategy_func)
        
        # 印出結果
        result.print_summary()
        
        # 檢查是否達到目標
        logger.info("\n目標達成檢查:")
        target_win_rate = self.config['backtest']['target_win_rate']
        target_pf = self.config['backtest']['target_profit_factor']
        target_sharpe = self.config['backtest']['target_sharpe_ratio']
        
        checks = {
            f"勝率 >= {target_win_rate}%": result.win_rate >= target_win_rate,
            f"獲利因子 >= {target_pf}": result.profit_factor >= target_pf,
            f"Sharpe Ratio >= {target_sharpe}": result.sharpe_ratio >= target_sharpe
        }
        
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {check}")
        
        return result
    
    def print_status(self):
        """印出系統狀態"""
        status = self.risk_manager.get_status()
        
        print("=" * 70)
        print("交易系統狀態")
        print("=" * 70)
        print(f"當前資金: ${status['current_capital']:,.0f}")
        print(f"總損益: ${status['total_pnl']:+,.0f} ({status['total_pnl_pct']:+.2f}%)")
        print(f"今日損益: ${status['daily_pnl']:+,.0f} ({status['daily_pnl_pct']:+.2f}%)")
        print(f"最大回撤: {status['drawdown_pct']:.2f}%")
        print(f"持倉數: {status['open_positions']}/{self.risk_manager.config.max_open_positions}")
        print(f"連續虧損: {status['consecutive_losses']}/{self.risk_manager.config.max_consecutive_losses}")
        print(f"總交易數: {status['total_trades']}")
        print("=" * 70)


# 使用範例
if __name__ == "__main__":
    # 初始化系統
    system = EnhancedDayTradingSystem("config_enhanced.yml")
    
    # === 1. 分析市場環境 ===
    print("\n" + "="*70)
    print("步驟 1: 分析市場環境")
    print("="*70)
    
    # 生成模擬大盤資料
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    index_prices = 18000 + np.cumsum(np.random.randn(len(dates)) * 50)
    
    index_df = pd.DataFrame({
        'Date': dates,
        'Close': index_prices,
        'Volume': np.random.randint(100_000_000, 300_000_000, len(dates))
    })
    
    market_env = system.analyze_market_environment(
        index_df=index_df,
        vix_value=18.5,
        foreign_net_buy=3_000_000_000
    )
    
    system.market_analyzer.print_environment(market_env)
    
    # === 2. 掃描股票 ===
    print("\n" + "="*70)
    print("步驟 2: 掃描並分析股票")
    print("="*70)
    
    # 生成模擬股票資料
    stock_data = {}
    for symbol in ['2330', '2454', '2317']:
        prices = 100 + np.cumsum(np.random.randn(len(dates)) * 2)
        stock_data[symbol] = pd.DataFrame({
            'Date': dates,
            'Open': prices * (1 + np.random.randn(len(dates)) * 0.01),
            'High': prices * (1 + abs(np.random.randn(len(dates))) * 0.02),
            'Low': prices * (1 - abs(np.random.randn(len(dates))) * 0.02),
            'Close': prices,
            'Volume': np.random.randint(50_000, 150_000, len(dates))
        })
    
    # 模擬法人資料
    institutional = {
        '2330': {'foreign': 5000, 'investment_trust': 2000, 'dealer': -1000},
        '2454': {'foreign': -3000, 'investment_trust': 500, 'dealer': 200},
        '2317': {'foreign': 1000, 'investment_trust': -500, 'dealer': 100}
    }
    
    # 掃描
    candidates = system.scan_and_filter_stocks(
        stocks_data=stock_data,
        institutional_data=institutional,
        market_env=market_env
    )
    
    # 顯示結果
    if candidates:
        print(f"\n找到 {len(candidates)} 檔符合條件的股票:\n")
        for i, stock in enumerate(candidates[:5], 1):
            print(f"{i}. {stock['symbol']} - 分數: {stock['score']}/100 - {stock['signal']}")
            print(f"   理由: {', '.join(stock['reasons'][:3])}")
    else:
        print("\n無符合條件的股票")
    
    # === 3. 執行回測 ===
    print("\n" + "="*70)
    print("步驟 3: 回測驗證")
    print("="*70)
    
    # 使用台積電資料回測
    result = system.run_backtest(stock_data['2330'])
    
    # === 4. 印出系統狀態 ===
    print("\n")
    system.print_status()
    
    # === 5. 生成報表 ===
    print("\n" + "="*70)
    print("步驟 4: 交易日誌")
    print("="*70)
    system.trade_logger.print_report()
