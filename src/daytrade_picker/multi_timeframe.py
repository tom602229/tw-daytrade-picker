"""
多時間框架確認機制 - Multi-Timeframe Analysis
避免只看單一時間週期造成的誤判
"""
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """時間週期"""
    MINUTE_1 = "1分鐘"
    MINUTE_5 = "5分鐘"
    MINUTE_15 = "15分鐘"
    MINUTE_30 = "30分鐘"
    HOUR_1 = "1小時"
    DAILY = "日線"
    WEEKLY = "週線"
    MONTHLY = "月線"


class TrendDirection(Enum):
    """趨勢方向"""
    STRONG_UP = "強勢上漲"
    UP = "上漲"
    SIDEWAYS = "盤整"
    DOWN = "下跌"
    STRONG_DOWN = "強勢下跌"


class MultiTimeFrameAnalyzer:
    """多時間框架分析器"""
    
    def __init__(self):
        pass
    
    def analyze_trend(self, df: pd.DataFrame) -> TrendDirection:
        """
        分析趨勢方向
        使用均線斜率和價格位置
        """
        if len(df) < 20:
            return TrendDirection.SIDEWAYS
        
        # 計算均線
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        latest = df.iloc[-1]
        close = latest['Close']
        ma5 = latest['MA5']
        ma20 = latest['MA20']
        
        # 計算均線斜率（用最近 5 筆資料）
        if len(df) >= 5:
            ma5_slope = (df['MA5'].iloc[-1] - df['MA5'].iloc[-5]) / df['MA5'].iloc[-5] * 100
            ma20_slope = (df['MA20'].iloc[-1] - df['MA20'].iloc[-5]) / df['MA20'].iloc[-5] * 100
        else:
            ma5_slope = 0
            ma20_slope = 0
        
        # 判斷趨勢
        if close > ma5 > ma20 and ma5_slope > 2 and ma20_slope > 1:
            return TrendDirection.STRONG_UP
        elif close > ma20 and ma5_slope > 0:
            return TrendDirection.UP
        elif close < ma5 < ma20 and ma5_slope < -2 and ma20_slope < -1:
            return TrendDirection.STRONG_DOWN
        elif close < ma20 and ma5_slope < 0:
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS
    
    def analyze_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """
        分析支撐壓力
        
        Returns:
            {
                'support': float,
                'resistance': float,
                'near_support': bool,
                'near_resistance': bool
            }
        """
        if len(df) < lookback:
            lookback = len(df)
        
        recent = df.tail(lookback)
        
        # 簡單的支撐壓力：最近的最高/最低
        support = recent['Low'].min()
        resistance = recent['High'].max()
        
        current_price = df['Close'].iloc[-1]
        
        # 判斷是否接近支撐/壓力（±2%）
        support_distance = abs(current_price - support) / support
        resistance_distance = abs(current_price - resistance) / resistance
        
        return {
            'support': support,
            'resistance': resistance,
            'near_support': support_distance < 0.02,
            'near_resistance': resistance_distance < 0.02,
            'support_distance_pct': support_distance * 100,
            'resistance_distance_pct': resistance_distance * 100
        }
    
    def multi_timeframe_check(self, data_dict: Dict[TimeFrame, pd.DataFrame]) -> Dict:
        """
        多時間框架綜合分析
        
        Args:
            data_dict: {TimeFrame: DataFrame} 例如：
                {
                    TimeFrame.DAILY: daily_df,
                    TimeFrame.HOUR_1: hourly_df,
                    TimeFrame.MINUTE_15: min15_df
                }
        
        Returns:
            {
                'alignment': 'bullish' | 'bearish' | 'mixed',
                'trends': {TimeFrame: TrendDirection},
                'entry_timeframe': TimeFrame,  # 建議進場時間框架
                'confidence': float,  # 0-100
                'analysis': [分析內容]
            }
        """
        if not data_dict:
            return {
                'alignment': 'mixed',
                'trends': {},
                'entry_timeframe': None,
                'confidence': 0,
                'analysis': ['無資料']
            }
        
        # 分析各時間框架趨勢
        trends = {}
        for timeframe, df in data_dict.items():
            trends[timeframe] = self.analyze_trend(df)
        
        # 統計多空方向
        up_count = sum(1 for t in trends.values() 
                      if t in [TrendDirection.UP, TrendDirection.STRONG_UP])
        down_count = sum(1 for t in trends.values() 
                        if t in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN])
        total_count = len(trends)
        
        # 判斷一致性
        analysis = []
        
        if up_count >= total_count * 0.7:
            alignment = 'bullish'
            confidence = (up_count / total_count) * 100
            analysis.append(f"✓ {up_count}/{total_count} 個時間框架看多")
        elif down_count >= total_count * 0.7:
            alignment = 'bearish'
            confidence = (down_count / total_count) * 100
            analysis.append(f"✗ {down_count}/{total_count} 個時間框架看空")
        else:
            alignment = 'mixed'
            confidence = 50
            analysis.append(f"⚠ 時間框架分歧 (多:{up_count} 空:{down_count})")
        
        # 詳細分析每個時間框架
        for timeframe, trend in trends.items():
            analysis.append(f"{timeframe.value}: {trend.value}")
        
        # 決定進場時間框架（使用最短的時間框架）
        entry_timeframe = min(data_dict.keys(), key=lambda x: list(TimeFrame).index(x))
        
        return {
            'alignment': alignment,
            'trends': trends,
            'entry_timeframe': entry_timeframe,
            'confidence': confidence,
            'analysis': analysis
        }
    
    def get_entry_signal(self, long_term_df: pd.DataFrame, 
                        short_term_df: pd.DataFrame,
                        trend_alignment: str) -> Dict:
        """
        獲取進場訊號
        
        策略：
        1. 長週期看趨勢（日線/小時線）
        2. 短週期找進場點（15分/5分）
        
        Args:
            long_term_df: 長週期資料（例如日線）
            short_term_df: 短週期資料（例如 15 分鐘）
            trend_alignment: 'bullish' | 'bearish' | 'mixed'
        
        Returns:
            {
                'signal': 'BUY' | 'SELL' | 'WAIT',
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'reason': str
            }
        """
        # 分析長週期支撐壓力
        lt_sr = self.analyze_support_resistance(long_term_df)
        
        # 分析短週期趨勢
        st_trend = self.analyze_trend(short_term_df)
        
        current_price = short_term_df['Close'].iloc[-1]
        
        signal = 'WAIT'
        reason = ''
        stop_loss = 0
        take_profit = 0
        
        # 做多訊號
        if trend_alignment == 'bullish':
            # 長週期看多，等待短週期回調買入
            if st_trend in [TrendDirection.DOWN, TrendDirection.SIDEWAYS]:
                if lt_sr['near_support']:
                    signal = 'BUY'
                    reason = '長週期多頭，短週期回調至支撐區'
                    stop_loss = lt_sr['support'] * 0.97  # 支撐下方 3%
                    take_profit = lt_sr['resistance']
            elif st_trend in [TrendDirection.UP, TrendDirection.STRONG_UP]:
                signal = 'BUY'
                reason = '多時間框架一致看多'
                # 使用短週期均線作為停損
                short_term_df['MA5'] = short_term_df['Close'].rolling(window=5).mean()
                stop_loss = short_term_df['MA5'].iloc[-1] * 0.98
                take_profit = current_price * 1.06  # 6% 停利
        
        # 做空訊號
        elif trend_alignment == 'bearish':
            if st_trend in [TrendDirection.UP, TrendDirection.SIDEWAYS]:
                if lt_sr['near_resistance']:
                    signal = 'SELL'
                    reason = '長週期空頭，短週期反彈至壓力區'
                    stop_loss = lt_sr['resistance'] * 1.03
                    take_profit = lt_sr['support']
            elif st_trend in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]:
                signal = 'SELL'
                reason = '多時間框架一致看空'
                short_term_df['MA5'] = short_term_df['Close'].rolling(window=5).mean()
                stop_loss = short_term_df['MA5'].iloc[-1] * 1.02
                take_profit = current_price * 0.94
        
        # 分歧時觀望
        else:
            reason = '時間框架分歧，等待明確訊號'
        
        return {
            'signal': signal,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': reason
        }
    
    def print_analysis(self, result: Dict):
        """印出分析結果"""
        print("=" * 60)
        print("多時間框架分析")
        print("=" * 60)
        print(f"趨勢一致性: {result['alignment'].upper()}")
        print(f"信心指數: {result['confidence']:.1f}%")
        print(f"\n分析:")
        for item in result['analysis']:
            print(f"  {item}")
        print("=" * 60)


# 使用範例
if __name__ == "__main__":
    import numpy as np
    
    # 模擬資料生成函數
    def generate_data(length: int, trend: str = 'up'):
        dates = pd.date_range(start='2024-01-01', periods=length, freq='D')
        
        if trend == 'up':
            prices = 100 + np.cumsum(np.random.randn(length) * 0.5 + 0.2)
        elif trend == 'down':
            prices = 100 + np.cumsum(np.random.randn(length) * 0.5 - 0.2)
        else:
            prices = 100 + np.cumsum(np.random.randn(length) * 0.5)
        
        return pd.DataFrame({
            'Date': dates,
            'Open': prices * (1 + np.random.randn(length) * 0.01),
            'High': prices * (1 + abs(np.random.randn(length)) * 0.02),
            'Low': prices * (1 - abs(np.random.randn(length)) * 0.02),
            'Close': prices,
            'Volume': np.random.randint(100000, 200000, length)
        })
    
    # 生成多時間框架資料
    daily_df = generate_data(60, 'up')
    hourly_df = generate_data(120, 'up')
    min15_df = generate_data(200, 'sideways')
    
    # 初始化分析器
    analyzer = MultiTimeFrameAnalyzer()
    
    # 多時間框架分析
    data_dict = {
        TimeFrame.DAILY: daily_df,
        TimeFrame.HOUR_1: hourly_df,
        TimeFrame.MINUTE_15: min15_df
    }
    
    result = analyzer.multi_timeframe_check(data_dict)
    analyzer.print_analysis(result)
    
    # 獲取進場訊號
    entry_signal = analyzer.get_entry_signal(
        long_term_df=daily_df,
        short_term_df=min15_df,
        trend_alignment=result['alignment']
    )
    
    print(f"\n進場訊號:")
    print(f"  訊號: {entry_signal['signal']}")
    print(f"  進場價: {entry_signal['entry_price']:.2f}")
    print(f"  停損價: {entry_signal['stop_loss']:.2f}")
    print(f"  停利價: {entry_signal['take_profit']:.2f}")
    print(f"  理由: {entry_signal['reason']}")
