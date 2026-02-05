"""
增強版 Strategy C - 加入籌碼面分析
Enhanced Strategy with Chip Analysis (OBV, Institutional Investors)
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ChipAnalyzer:
    """籌碼分析器"""
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        計算 OBV (On-Balance Volume) 能量潮指標
        用於判斷主力資金流向
        
        邏輯:
        - 收盤價上漲: OBV += 當日成交量
        - 收盤價下跌: OBV -= 當日成交量
        - 收盤價持平: OBV 不變
        """
        if 'Close' not in df.columns or 'Volume' not in df.columns:
            logger.error("資料缺少 Close 或 Volume 欄位")
            return pd.Series([0] * len(df))
        
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=df.index)
    
    @staticmethod
    def obv_signal(df: pd.DataFrame, obv_ma_period: int = 20) -> str:
        """
        OBV 訊號判斷
        
        Returns:
            'bullish': 多頭訊號 (價漲量增)
            'bearish': 空頭訊號 (價跌量增)
            'divergence_bullish': 底背離 (價跌但 OBV 上升)
            'divergence_bearish': 頂背離 (價漲但 OBV 下降)
            'neutral': 中性
        """
        if len(df) < obv_ma_period + 5:
            return 'neutral'
        
        # 計算 OBV
        df['OBV'] = ChipAnalyzer.calculate_obv(df)
        df['OBV_MA'] = df['OBV'].rolling(window=obv_ma_period).mean()
        
        # 最近 5 天資料
        recent = df.tail(5)
        
        # 價格趨勢
        price_trend = recent['Close'].iloc[-1] > recent['Close'].iloc[0]
        # OBV 趨勢
        obv_trend = recent['OBV'].iloc[-1] > recent['OBV'].iloc[0]
        
        # OBV 是否在均線上
        obv_above_ma = df['OBV'].iloc[-1] > df['OBV_MA'].iloc[-1]
        
        # 判斷背離
        if price_trend and not obv_trend:
            return 'divergence_bearish'  # 價漲量不漲，頂背離
        elif not price_trend and obv_trend:
            return 'divergence_bullish'  # 價跌量不跌，底背離
        
        # 判斷多空
        if price_trend and obv_trend and obv_above_ma:
            return 'bullish'  # 價量齊揚
        elif not price_trend and not obv_trend:
            return 'bearish'  # 價量齊跌
        
        return 'neutral'
    
    @staticmethod
    def analyze_institutional(foreign: float, investment_trust: float, 
                             dealer: float, threshold: float = 1_000) -> Dict[str, str]:
        """
        分析三大法人買賣超
        
        Args:
            foreign: 外資買賣超 (張)
            investment_trust: 投信買賣超 (張)
            dealer: 自營商買賣超 (張)
            threshold: 判斷門檻 (張)
        
        Returns:
            {
                'foreign': '買超' | '賣超' | '中性',
                'investment_trust': ...,
                'dealer': ...,
                'consensus': '法人一致買超' | '法人一致賣超' | '分歧' | '中性'
            }
        """
        def classify(value: float) -> str:
            if value > threshold:
                return '買超'
            elif value < -threshold:
                return '賣超'
            else:
                return '中性'
        
        foreign_status = classify(foreign)
        trust_status = classify(investment_trust)
        dealer_status = classify(dealer)
        
        # 判斷一致性
        buy_count = sum([1 for s in [foreign_status, trust_status, dealer_status] if s == '買超'])
        sell_count = sum([1 for s in [foreign_status, trust_status, dealer_status] if s == '賣超'])
        
        if buy_count >= 2:
            consensus = '法人一致買超'
        elif sell_count >= 2:
            consensus = '法人一致賣超'
        elif buy_count == 1 and sell_count == 1:
            consensus = '分歧'
        else:
            consensus = '中性'
        
        return {
            'foreign': foreign_status,
            'investment_trust': trust_status,
            'dealer': dealer_status,
            'consensus': consensus,
            'total_net': foreign + investment_trust + dealer
        }


class EnhancedStrategyC:
    """增強版策略 C"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略
        
        config 範例:
        {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'williams_period': 14,
            'williams_oversold': -80,
            'williams_overbought': -20,
            'obv_ma_period': 20,
            'volume_ma_period': 20,
            'volume_threshold': 1.5,  # 成交量需大於均量的倍數
            'institutional_threshold': 1000  # 法人買賣超門檻 (張)
        }
        """
        self.config = config or self._default_config()
        self.chip_analyzer = ChipAnalyzer()
    
    def _default_config(self) -> Dict:
        return {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'williams_period': 14,
            'williams_oversold': -80,
            'williams_overbought': -20,
            'obv_ma_period': 20,
            'volume_ma_period': 20,
            'volume_threshold': 1.5,
            'institutional_threshold': 1000
        }
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算 RSI"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算 Williams %R"""
        highest_high = df['High'].rolling(window=period).max()
        lowest_low = df['Low'].rolling(window=period).min()
        williams_r = -100 * ((highest_high - df['Close']) / (highest_high - lowest_low))
        return williams_r
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算布林通道"""
        ma = df['Close'].rolling(window=period).mean()
        std_dev = df['Close'].rolling(window=period).std()
        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)
        return upper_band, ma, lower_band
    
    def analyze_stock(self, df: pd.DataFrame, 
                     institutional_data: Optional[Dict] = None) -> Dict:
        """
        分析個股
        
        Args:
            df: 股票資料 (需包含 Open, High, Low, Close, Volume)
            institutional_data: 法人資料 {
                'foreign': 外資買賣超(張),
                'investment_trust': 投信買賣超(張),
                'dealer': 自營商買賣超(張)
            }
        
        Returns:
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'score': 0-100,
                'reasons': [原因列表],
                'technical': {...},
                'chip': {...}
            }
        """
        if len(df) < 60:
            return {
                'signal': 'HOLD',
                'score': 0,
                'reasons': ['資料不足'],
                'technical': {},
                'chip': {}
            }
        
        # === 技術面分析 ===
        
        # RSI
        df['RSI'] = self.calculate_rsi(df, self.config['rsi_period'])
        rsi = df['RSI'].iloc[-1]
        
        # Williams %R
        df['Williams_R'] = self.calculate_williams_r(df, self.config['williams_period'])
        williams = df['Williams_R'].iloc[-1]
        
        # 布林通道
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self.calculate_bollinger_bands(df)
        close = df['Close'].iloc[-1]
        bb_position = (close - df['BB_Lower'].iloc[-1]) / (df['BB_Upper'].iloc[-1] - df['BB_Lower'].iloc[-1])
        
        # 成交量
        df['Volume_MA'] = df['Volume'].rolling(window=self.config['volume_ma_period']).mean()
        volume_ratio = df['Volume'].iloc[-1] / df['Volume_MA'].iloc[-1]
        
        # === 籌碼面分析 ===
        
        # OBV 訊號
        obv_signal = self.chip_analyzer.obv_signal(df, self.config['obv_ma_period'])
        
        # 法人買賣超
        institutional_analysis = None
        if institutional_data:
            institutional_analysis = self.chip_analyzer.analyze_institutional(
                institutional_data.get('foreign', 0),
                institutional_data.get('investment_trust', 0),
                institutional_data.get('dealer', 0),
                self.config['institutional_threshold']
            )
        
        # === 綜合評分 ===
        
        score = 50  # 基準分
        reasons = []
        
        # 技術面評分 (40 分)
        if rsi < self.config['rsi_oversold']:
            score += 10
            reasons.append(f"✓ RSI 超賣 ({rsi:.1f})")
        elif rsi > self.config['rsi_overbought']:
            score -= 10
            reasons.append(f"✗ RSI 超買 ({rsi:.1f})")
        
        if williams < self.config['williams_oversold']:
            score += 10
            reasons.append(f"✓ Williams %R 超賣 ({williams:.1f})")
        elif williams > self.config['williams_overbought']:
            score -= 10
            reasons.append(f"✗ Williams %R 超買 ({williams:.1f})")
        
        if bb_position < 0.2:
            score += 10
            reasons.append(f"✓ 價格接近布林下軌")
        elif bb_position > 0.8:
            score -= 10
            reasons.append(f"✗ 價格接近布林上軌")
        
        if volume_ratio > self.config['volume_threshold']:
            score += 10
            reasons.append(f"✓ 成交量放大 ({volume_ratio:.1f}x)")
        
        # 籌碼面評分 (40 分)
        if obv_signal == 'bullish':
            score += 15
            reasons.append("✓ OBV 價量齊揚")
        elif obv_signal == 'divergence_bullish':
            score += 20
            reasons.append("✓✓ OBV 底背離（強烈買訊）")
        elif obv_signal == 'bearish':
            score -= 15
            reasons.append("✗ OBV 價量齊跌")
        elif obv_signal == 'divergence_bearish':
            score -= 20
            reasons.append("✗✗ OBV 頂背離（強烈賣訊）")
        
        if institutional_analysis:
            if institutional_analysis['consensus'] == '法人一致買超':
                score += 25
                reasons.append(f"✓✓ 三大法人一致買超")
            elif institutional_analysis['consensus'] == '法人一致賣超':
                score -= 25
                reasons.append(f"✗✗ 三大法人一致賣超")
            elif institutional_analysis['foreign'] == '買超':
                score += 10
                reasons.append(f"✓ 外資買超")
            elif institutional_analysis['foreign'] == '賣超':
                score -= 10
                reasons.append(f"✗ 外資賣超")
        
        # === 決策 ===
        
        if score >= 70:
            signal = 'BUY'
        elif score <= 30:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        return {
            'signal': signal,
            'score': min(100, max(0, score)),
            'reasons': reasons,
            'technical': {
                'rsi': rsi,
                'williams_r': williams,
                'bb_position': bb_position,
                'volume_ratio': volume_ratio
            },
            'chip': {
                'obv_signal': obv_signal,
                'institutional': institutional_analysis
            }
        }
    
    def scan_stocks(self, stocks_data: Dict[str, pd.DataFrame],
                   institutional_data: Optional[Dict[str, Dict]] = None) -> List[Dict]:
        """
        掃描多檔股票
        
        Args:
            stocks_data: {股票代號: DataFrame}
            institutional_data: {股票代號: {法人資料}}
        
        Returns:
            排序後的股票列表，依評分由高到低
        """
        results = []
        
        for symbol, df in stocks_data.items():
            inst_data = institutional_data.get(symbol) if institutional_data else None
            analysis = self.analyze_stock(df, inst_data)
            
            results.append({
                'symbol': symbol,
                'signal': analysis['signal'],
                'score': analysis['score'],
                'reasons': analysis['reasons'],
                'technical': analysis['technical'],
                'chip': analysis['chip']
            })
        
        # 依評分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def print_analysis(self, symbol: str, analysis: Dict):
        """印出分析結果"""
        print("=" * 60)
        print(f"股票: {symbol}")
        print("=" * 60)
        print(f"訊號: {analysis['signal']} (評分: {analysis['score']}/100)")
        print(f"\n理由:")
        for reason in analysis['reasons']:
            print(f"  {reason}")
        
        print(f"\n技術指標:")
        tech = analysis['technical']
        print(f"  RSI: {tech['rsi']:.1f}")
        print(f"  Williams %R: {tech['williams_r']:.1f}")
        print(f"  布林通道位置: {tech['bb_position']:.2f}")
        print(f"  成交量比: {tech['volume_ratio']:.2f}x")
        
        print(f"\n籌碼面:")
        chip = analysis['chip']
        print(f"  OBV 訊號: {chip['obv_signal']}")
        if chip['institutional']:
            inst = chip['institutional']
            print(f"  外資: {inst['foreign']}")
            print(f"  投信: {inst['investment_trust']}")
            print(f"  自營: {inst['dealer']}")
            print(f"  法人共識: {inst['consensus']}")
        print("=" * 60)


# 使用範例
if __name__ == "__main__":
    # 生成模擬資料
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # 模擬股票資料
    df = pd.DataFrame({
        'Date': dates,
        'Open': 100 + np.random.randn(len(dates)).cumsum(),
        'High': 102 + np.random.randn(len(dates)).cumsum(),
        'Low': 98 + np.random.randn(len(dates)).cumsum(),
        'Close': 100 + np.random.randn(len(dates)).cumsum(),
        'Volume': np.random.randint(50_000, 150_000, len(dates))
    })
    
    # 初始化策略
    strategy = EnhancedStrategyC()
    
    # 模擬法人資料
    institutional = {
        'foreign': 5000,  # 外資買超 5000 張
        'investment_trust': 2000,  # 投信買超 2000 張
        'dealer': -1000  # 自營賣超 1000 張
    }
    
    # 分析
    analysis = strategy.analyze_stock(df, institutional)
    strategy.print_analysis('2330', analysis)
