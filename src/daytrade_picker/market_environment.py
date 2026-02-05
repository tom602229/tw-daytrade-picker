"""
市場環境判斷模組 - Market Environment Analysis Module
判斷大盤趨勢、恐慌指標、產業輪動
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MarketTrend(Enum):
    """市場趨勢"""
    STRONG_BULL = "強勢多頭"
    BULL = "多頭"
    NEUTRAL = "盤整"
    BEAR = "空頭"
    STRONG_BEAR = "強勢空頭"


class MarketSentiment(Enum):
    """市場情緒"""
    EXTREME_GREED = "極度貪婪"
    GREED = "貪婪"
    NEUTRAL = "中性"
    FEAR = "恐慌"
    EXTREME_FEAR = "極度恐慌"


@dataclass
class MarketEnvironment:
    """市場環境狀態"""
    trend: MarketTrend
    sentiment: MarketSentiment
    index_ma_status: Dict[str, bool]  # 均線狀態
    volume_status: str
    foreign_bias: str  # 外資偏好
    can_long: bool  # 是否適合做多
    can_short: bool  # 是否適合做空
    signals: List[str]  # 訊號列表


class MarketAnalyzer:
    """市場分析器"""
    
    def __init__(self):
        self.index_symbol = "^TWII"  # 加權指數
        
    def analyze_trend(self, df: pd.DataFrame) -> MarketTrend:
        """
        分析大盤趨勢
        df 需包含: Close, MA5, MA10, MA20, MA60
        """
        if len(df) < 60:
            logger.warning("資料不足 60 天，無法完整分析趨勢")
            return MarketTrend.NEUTRAL
        
        latest = df.iloc[-1]
        close = latest['Close']
        
        # 計算均線（如果不存在）
        if 'MA5' not in df.columns:
            df['MA5'] = df['Close'].rolling(window=5).mean()
        if 'MA10' not in df.columns:
            df['MA10'] = df['Close'].rolling(window=10).mean()
        if 'MA20' not in df.columns:
            df['MA20'] = df['Close'].rolling(window=20).mean()
        if 'MA60' not in df.columns:
            df['MA60'] = df['Close'].rolling(window=60).mean()
        
        latest = df.iloc[-1]
        ma5, ma10, ma20, ma60 = latest['MA5'], latest['MA10'], latest['MA20'], latest['MA60']
        
        # 多頭排列: 短均 > 長均
        bull_alignment = ma5 > ma10 > ma20 > ma60
        # 空頭排列: 短均 < 長均
        bear_alignment = ma5 < ma10 < ma20 < ma60
        
        # 計算趨勢強度
        above_ma60 = close > ma60
        above_ma20 = close > ma20
        
        # 計算 20 日漲跌幅
        if len(df) >= 20:
            price_change_20d = ((close - df.iloc[-20]['Close']) / df.iloc[-20]['Close']) * 100
        else:
            price_change_20d = 0
        
        # 判斷趨勢
        if bull_alignment and above_ma60 and price_change_20d > 5:
            return MarketTrend.STRONG_BULL
        elif above_ma20 and above_ma60:
            return MarketTrend.BULL
        elif bear_alignment and not above_ma60 and price_change_20d < -5:
            return MarketTrend.STRONG_BEAR
        elif not above_ma20 and not above_ma60:
            return MarketTrend.BEAR
        else:
            return MarketTrend.NEUTRAL
    
    def analyze_sentiment(self, df: pd.DataFrame, vix_value: Optional[float] = None) -> MarketSentiment:
        """
        分析市場情緒
        基於波動率、成交量、漲跌家數比
        """
        if len(df) < 20:
            return MarketSentiment.NEUTRAL
        
        # 計算波動率（20 日標準差）
        returns = df['Close'].pct_change()
        volatility = returns.rolling(window=20).std().iloc[-1] * 100
        
        # 成交量變化
        if 'Volume' in df.columns:
            avg_volume_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        else:
            volume_ratio = 1
        
        # VIX 恐慌指標（如果提供）
        # 台灣 VIX 正常範圍 10-20，>25 恐慌，<10 過度樂觀
        if vix_value is not None:
            if vix_value > 30:
                return MarketSentiment.EXTREME_FEAR
            elif vix_value > 25:
                return MarketSentiment.FEAR
            elif vix_value < 10:
                return MarketSentiment.EXTREME_GREED
            elif vix_value < 12:
                return MarketSentiment.GREED
        
        # 基於波動率判斷
        if volatility > 3.0 and volume_ratio > 1.5:
            return MarketSentiment.FEAR
        elif volatility > 4.0:
            return MarketSentiment.EXTREME_FEAR
        elif volatility < 0.8 and volume_ratio < 0.7:
            return MarketSentiment.EXTREME_GREED
        elif volatility < 1.2:
            return MarketSentiment.GREED
        else:
            return MarketSentiment.NEUTRAL
    
    def analyze_ma_status(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        分析均線狀態
        Returns: {
            'above_ma5': bool,
            'above_ma20': bool,
            'above_ma60': bool,
            'ma5_up': bool,  # MA5 向上
            'ma20_up': bool
        }
        """
        if len(df) < 60:
            return {}
        
        # 確保均線存在
        if 'MA5' not in df.columns:
            df['MA5'] = df['Close'].rolling(window=5).mean()
        if 'MA20' not in df.columns:
            df['MA20'] = df['Close'].rolling(window=20).mean()
        if 'MA60' not in df.columns:
            df['MA60'] = df['Close'].rolling(window=60).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        close = latest['Close']
        
        return {
            'above_ma5': close > latest['MA5'],
            'above_ma20': close > latest['MA20'],
            'above_ma60': close > latest['MA60'],
            'ma5_up': latest['MA5'] > prev['MA5'],
            'ma20_up': latest['MA20'] > prev['MA20'],
            'golden_cross': latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20'],  # 黃金交叉
            'death_cross': latest['MA5'] < latest['MA20'] and prev['MA5'] >= prev['MA20']   # 死亡交叉
        }
    
    def analyze_foreign_investment(self, net_buy_amount: float, threshold: float = 5_000_000_000) -> str:
        """
        分析外資動向
        net_buy_amount: 外資買賣超金額（台幣）
        threshold: 判斷門檻（預設 50 億）
        """
        if net_buy_amount > threshold:
            return "強力買超"
        elif net_buy_amount > 0:
            return "買超"
        elif net_buy_amount < -threshold:
            return "強力賣超"
        elif net_buy_amount < 0:
            return "賣超"
        else:
            return "平衡"
    
    def get_market_environment(self, index_df: pd.DataFrame, 
                               vix_value: Optional[float] = None,
                               foreign_net_buy: Optional[float] = None) -> MarketEnvironment:
        """
        綜合分析市場環境
        
        Args:
            index_df: 大盤資料 (需包含 Close, Volume)
            vix_value: VIX 恐慌指標（可選）
            foreign_net_buy: 外資買賣超金額（可選）
        
        Returns:
            MarketEnvironment 物件
        """
        # 分析趨勢
        trend = self.analyze_trend(index_df)
        
        # 分析情緒
        sentiment = self.analyze_sentiment(index_df, vix_value)
        
        # 分析均線狀態
        ma_status = self.analyze_ma_status(index_df)
        
        # 分析外資動向
        if foreign_net_buy is not None:
            foreign_bias = self.analyze_foreign_investment(foreign_net_buy)
        else:
            foreign_bias = "未知"
        
        # 判斷成交量
        if 'Volume' in index_df.columns and len(index_df) >= 20:
            avg_volume = index_df['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = index_df['Volume'].iloc[-1]
            if current_volume > avg_volume * 1.5:
                volume_status = "爆量"
            elif current_volume > avg_volume * 1.2:
                volume_status = "量增"
            elif current_volume < avg_volume * 0.7:
                volume_status = "量縮"
            else:
                volume_status = "正常"
        else:
            volume_status = "未知"
        
        # 決策邏輯
        signals = []
        can_long = False
        can_short = False
        
        # 做多條件
        if trend in [MarketTrend.STRONG_BULL, MarketTrend.BULL]:
            if ma_status.get('above_ma20', False):
                can_long = True
                signals.append("✓ 大盤多頭，站穩月線")
            
            if ma_status.get('golden_cross', False):
                signals.append("✓ 黃金交叉出現")
                can_long = True
            
            if sentiment in [MarketSentiment.FEAR, MarketSentiment.EXTREME_FEAR]:
                signals.append("⚠ 恐慌情緒，可能短線超跌反彈")
        
        # 做空/觀望條件
        if trend in [MarketTrend.BEAR, MarketTrend.STRONG_BEAR]:
            can_long = False
            can_short = True
            signals.append("✗ 大盤空頭，避免做多")
            
            if ma_status.get('death_cross', False):
                signals.append("✗ 死亡交叉出現")
            
            if not ma_status.get('above_ma60', False):
                signals.append("✗ 跌破季線")
        
        # 極端情緒警告
        if sentiment == MarketSentiment.EXTREME_GREED:
            signals.append("⚠ 市場過度樂觀，注意風險")
            can_long = False
        
        if sentiment == MarketSentiment.EXTREME_FEAR:
            signals.append("⚠ 市場極度恐慌，可能轉折點")
        
        # 外資訊號
        if foreign_bias in ["強力買超", "買超"]:
            signals.append(f"✓ 外資{foreign_bias}")
        elif foreign_bias in ["強力賣超", "賣超"]:
            signals.append(f"✗ 外資{foreign_bias}")
            if can_long:
                signals.append("⚠ 外資賣壓，謹慎操作")
        
        # 成交量訊號
        if volume_status == "爆量" and trend in [MarketTrend.BEAR, MarketTrend.STRONG_BEAR]:
            signals.append("⚠ 空頭爆量，可能恐慌殺盤")
            can_long = False
        
        return MarketEnvironment(
            trend=trend,
            sentiment=sentiment,
            index_ma_status=ma_status,
            volume_status=volume_status,
            foreign_bias=foreign_bias,
            can_long=can_long,
            can_short=can_short,
            signals=signals
        )
    
    def print_environment(self, env: MarketEnvironment):
        """印出市場環境分析結果"""
        print("=" * 60)
        print("市場環境分析")
        print("=" * 60)
        print(f"趨勢: {env.trend.value}")
        print(f"情緒: {env.sentiment.value}")
        print(f"成交量: {env.volume_status}")
        print(f"外資: {env.foreign_bias}")
        print(f"\n操作建議:")
        print(f"  做多: {'✓ 可以' if env.can_long else '✗ 不宜'}")
        print(f"  做空: {'✓ 可以' if env.can_short else '✗ 不宜'}")
        print(f"\n訊號:")
        for signal in env.signals:
            print(f"  {signal}")
        print("=" * 60)


# 使用範例
if __name__ == "__main__":
    # 模擬大盤資料
    import pandas as pd
    import numpy as np
    
    # 生成模擬資料
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 2)  # 隨機遊走
    volumes = np.random.randint(100_000_000, 300_000_000, len(dates))
    
    df = pd.DataFrame({
        'Date': dates,
        'Close': prices,
        'Volume': volumes
    })
    
    # 初始化分析器
    analyzer = MarketAnalyzer()
    
    # 分析市場環境
    env = analyzer.get_market_environment(
        index_df=df,
        vix_value=18.5,  # 模擬 VIX 值
        foreign_net_buy=3_000_000_000  # 外資買超 30 億
    )
    
    # 印出結果
    analyzer.print_environment(env)
