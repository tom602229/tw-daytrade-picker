"""
資料驗證模組

提供完整的資料驗證功能，確保輸入資料品質，避免 NaN、異常值等問題。
專為台股當沖交易系統設計。

Author: TW DayTrade Picker
Version: 2.0
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, time
import logging

from .error_handler import DataValidationError, ErrorHandler


class DataValidator:
    """
    資料驗證器
    
    提供各種資料驗證方法，確保交易系統使用的資料符合品質要求
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化資料驗證器
        
        Args:
            logger: 日誌記錄器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.validation_log = []
    
    def validate_ohlcv_data(
        self,
        df: pd.DataFrame,
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        驗證 OHLCV 資料的完整性和正確性
        
        Args:
            df: OHLCV DataFrame
            strict: 是否使用嚴格模式（發現問題立即拋出異常）
        
        Returns:
            (是否通過驗證, 錯誤訊息列表)
        
        Raises:
            DataValidationError: 在 strict 模式下驗證失敗時
        """
        errors = []
        
        # 1. 檢查必要欄位
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(df.columns)
        
        if missing_columns:
            error_msg = f"缺少必要欄位: {missing_columns}"
            errors.append(error_msg)
            if strict:
                raise DataValidationError(error_msg)
        
        # 2. 檢查資料是否為空
        if df.empty:
            error_msg = "資料為空"
            errors.append(error_msg)
            if strict:
                raise DataValidationError(error_msg)
            return False, errors
        
        # 3. 檢查 NaN 值
        for col in required_columns:
            if col in df.columns:
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    error_msg = f"欄位 '{col}' 包含 {nan_count} 個 NaN 值"
                    errors.append(error_msg)
                    if strict:
                        raise DataValidationError(error_msg)
        
        # 4. 檢查價格關係 (High >= Low, High >= Open/Close, Low <= Open/Close)
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_high_low = df[df['high'] < df['low']]
            if len(invalid_high_low) > 0:
                error_msg = f"發現 {len(invalid_high_low)} 筆 High < Low 的異常資料"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
            
            invalid_high = df[(df['high'] < df['open']) | (df['high'] < df['close'])]
            if len(invalid_high) > 0:
                error_msg = f"發現 {len(invalid_high)} 筆 High 低於 Open/Close 的異常資料"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
            
            invalid_low = df[(df['low'] > df['open']) | (df['low'] > df['close'])]
            if len(invalid_low) > 0:
                error_msg = f"發現 {len(invalid_low)} 筆 Low 高於 Open/Close 的異常資料"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
        
        # 5. 檢查價格是否為正數
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                negative_prices = df[df[col] <= 0]
                if len(negative_prices) > 0:
                    error_msg = f"欄位 '{col}' 包含 {len(negative_prices)} 筆非正數價格"
                    errors.append(error_msg)
                    if strict:
                        raise DataValidationError(error_msg)
        
        # 6. 檢查成交量
        if 'volume' in df.columns:
            negative_volume = df[df['volume'] < 0]
            if len(negative_volume) > 0:
                error_msg = f"發現 {len(negative_volume)} 筆負數成交量"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
        
        # 7. 檢查時間序列是否單調遞增（如果有 datetime index）
        if isinstance(df.index, pd.DatetimeIndex):
            if not df.index.is_monotonic_increasing:
                error_msg = "時間序列不是單調遞增"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
        
        # 8. 檢查是否有重複的時間戳記
        if isinstance(df.index, pd.DatetimeIndex):
            duplicates = df.index.duplicated()
            if duplicates.any():
                dup_count = duplicates.sum()
                error_msg = f"發現 {dup_count} 筆重複的時間戳記"
                errors.append(error_msg)
                if strict:
                    raise DataValidationError(error_msg)
        
        # 記錄驗證結果
        if errors:
            self.logger.warning(f"資料驗證發現問題: {errors}")
            self.validation_log.append({
                'timestamp': datetime.now(),
                'validation_type': 'ohlcv',
                'passed': False,
                'errors': errors
            })
            return False, errors
        else:
            self.logger.info("OHLCV 資料驗證通過")
            self.validation_log.append({
                'timestamp': datetime.now(),
                'validation_type': 'ohlcv',
                'passed': True,
                'errors': []
            })
            return True, []
    
    def clean_ohlcv_data(
        self,
        df: pd.DataFrame,
        method: str = 'drop'
    ) -> pd.DataFrame:
        """
        清理 OHLCV 資料
        
        Args:
            df: 原始 OHLCV DataFrame
            method: 清理方法
                - 'drop': 刪除有問題的行
                - 'fill': 填補 NaN 值（使用前一筆有效資料）
                - 'interpolate': 使用插值法
        
        Returns:
            清理後的 DataFrame
        """
        df_clean = df.copy()
        
        # 1. 處理 NaN 值
        if method == 'drop':
            df_clean = df_clean.dropna()
            self.logger.info(f"刪除 {len(df) - len(df_clean)} 筆含 NaN 的資料")
        
        elif method == 'fill':
            # 使用前一筆有效資料填補
            df_clean = df_clean.fillna(method='ffill')
            # 如果第一筆就是 NaN，用後一筆填補
            df_clean = df_clean.fillna(method='bfill')
            self.logger.info("使用前向填補處理 NaN 值")
        
        elif method == 'interpolate':
            # 使用線性插值
            df_clean = df_clean.interpolate(method='linear')
            # 處理邊界的 NaN
            df_clean = df_clean.fillna(method='bfill').fillna(method='ffill')
            self.logger.info("使用插值法處理 NaN 值")
        
        # 2. 修正價格關係異常
        if all(col in df_clean.columns for col in ['open', 'high', 'low', 'close']):
            # 確保 High >= max(Open, Close, Low)
            df_clean['high'] = df_clean[['open', 'high', 'low', 'close']].max(axis=1)
            # 確保 Low <= min(Open, Close, High)
            df_clean['low'] = df_clean[['open', 'high', 'low', 'close']].min(axis=1)
        
        # 3. 移除非正數價格
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df_clean.columns:
                before_count = len(df_clean)
                df_clean = df_clean[df_clean[col] > 0]
                removed = before_count - len(df_clean)
                if removed > 0:
                    self.logger.warning(f"移除 {removed} 筆 {col} 非正數的資料")
        
        # 4. 移除負數成交量
        if 'volume' in df_clean.columns:
            before_count = len(df_clean)
            df_clean = df_clean[df_clean['volume'] >= 0]
            removed = before_count - len(df_clean)
            if removed > 0:
                self.logger.warning(f"移除 {removed} 筆負數成交量的資料")
        
        # 5. 移除重複時間戳記
        if isinstance(df_clean.index, pd.DatetimeIndex):
            before_count = len(df_clean)
            df_clean = df_clean[~df_clean.index.duplicated(keep='first')]
            removed = before_count - len(df_clean)
            if removed > 0:
                self.logger.warning(f"移除 {removed} 筆重複時間戳記的資料")
        
        # 6. 確保時間序列單調遞增
        if isinstance(df_clean.index, pd.DatetimeIndex):
            df_clean = df_clean.sort_index()
        
        self.logger.info(f"資料清理完成: {len(df)} -> {len(df_clean)} 筆")
        
        return df_clean
    
    @staticmethod
    def detect_outliers(
        data: pd.Series,
        method: str = 'iqr',
        threshold: float = 3.0
    ) -> pd.Series:
        """
        偵測異常值
        
        Args:
            data: 要檢測的資料序列
            method: 檢測方法
                - 'iqr': 四分位距法（預設）
                - 'zscore': Z-score 方法
                - 'mad': 中位數絕對偏差
            threshold: 異常值閾值
                - IQR: 通常使用 1.5 或 3.0
                - Z-score: 通常使用 3.0
                - MAD: 通常使用 3.0
        
        Returns:
            布林序列，True 表示異常值
        """
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            return (data < lower_bound) | (data > upper_bound)
        
        elif method == 'zscore':
            mean = data.mean()
            std = data.std()
            z_scores = np.abs((data - mean) / std)
            return z_scores > threshold
        
        elif method == 'mad':
            median = data.median()
            mad = np.median(np.abs(data - median))
            modified_z_scores = 0.6745 * (data - median) / mad
            return np.abs(modified_z_scores) > threshold
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def validate_trading_hours(
        self,
        df: pd.DataFrame,
        market_open: time = time(9, 0),
        market_close: time = time(13, 30)
    ) -> Tuple[bool, List[str]]:
        """
        驗證資料是否在交易時間內（台股：09:00-13:30）
        
        Args:
            df: 包含時間索引的 DataFrame
            market_open: 市場開盤時間
            market_close: 市場收盤時間
        
        Returns:
            (是否通過驗證, 錯誤訊息列表)
        """
        errors = []
        
        if not isinstance(df.index, pd.DatetimeIndex):
            error_msg = "資料索引不是 DatetimeIndex"
            errors.append(error_msg)
            return False, errors
        
        # 檢查是否有盤外時間的資料
        out_of_hours = df[
            (df.index.time < market_open) | 
            (df.index.time > market_close)
        ]
        
        if len(out_of_hours) > 0:
            error_msg = f"發現 {len(out_of_hours)} 筆盤外時間的資料"
            errors.append(error_msg)
            self.logger.warning(error_msg)
            return False, errors
        
        return True, []
    
    def validate_indicator(
        self,
        indicator: pd.Series,
        name: str,
        valid_range: Optional[Tuple[float, float]] = None,
        allow_nan: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        驗證技術指標的有效性
        
        Args:
            indicator: 技術指標序列
            name: 指標名稱
            valid_range: 有效範圍 (min, max)，例如 RSI 為 (0, 100)
            allow_nan: 是否允許 NaN 值
        
        Returns:
            (是否通過驗證, 錯誤訊息列表)
        """
        errors = []
        
        # 檢查 NaN
        if not allow_nan:
            nan_count = indicator.isna().sum()
            if nan_count > 0:
                error_msg = f"指標 '{name}' 包含 {nan_count} 個 NaN 值"
                errors.append(error_msg)
        
        # 檢查無限值
        inf_count = np.isinf(indicator).sum()
        if inf_count > 0:
            error_msg = f"指標 '{name}' 包含 {inf_count} 個無限值"
            errors.append(error_msg)
        
        # 檢查範圍
        if valid_range is not None:
            min_val, max_val = valid_range
            out_of_range = indicator[(indicator < min_val) | (indicator > max_val)]
            if len(out_of_range) > 0:
                error_msg = (
                    f"指標 '{name}' 有 {len(out_of_range)} 筆資料超出範圍 "
                    f"[{min_val}, {max_val}]"
                )
                errors.append(error_msg)
        
        if errors:
            self.logger.warning(f"指標 '{name}' 驗證失敗: {errors}")
            return False, errors
        
        return True, []
    
    def validate_signal(
        self,
        signal: pd.Series,
        valid_values: List[Any] = [1, 0, -1]
    ) -> Tuple[bool, List[str]]:
        """
        驗證交易信號的有效性
        
        Args:
            signal: 交易信號序列
            valid_values: 有效的信號值列表（預設：1=買, 0=持有, -1=賣）
        
        Returns:
            (是否通過驗證, 錯誤訊息列表)
        """
        errors = []
        
        # 檢查是否包含無效值
        invalid_signals = signal[~signal.isin(valid_values + [np.nan])]
        if len(invalid_signals) > 0:
            error_msg = f"發現 {len(invalid_signals)} 筆無效信號值"
            errors.append(error_msg)
        
        # 檢查 NaN
        nan_count = signal.isna().sum()
        if nan_count > 0:
            error_msg = f"信號包含 {nan_count} 個 NaN 值"
            errors.append(error_msg)
        
        if errors:
            self.logger.warning(f"信號驗證失敗: {errors}")
            return False, errors
        
        return True, []
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        獲取驗證報告
        
        Returns:
            包含驗證統計的字典
        """
        total_validations = len(self.validation_log)
        passed_validations = sum(1 for v in self.validation_log if v['passed'])
        
        return {
            'total_validations': total_validations,
            'passed_validations': passed_validations,
            'failed_validations': total_validations - passed_validations,
            'pass_rate': passed_validations / total_validations if total_validations > 0 else 0,
            'recent_validations': self.validation_log[-10:]
        }


# 工具函數：快速驗證
def quick_validate_ohlcv(df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
    """
    快速驗證並清理 OHLCV 資料
    
    Args:
        df: 原始 OHLCV DataFrame
        strict: 是否使用嚴格模式
    
    Returns:
        清理後的 DataFrame
    """
    validator = DataValidator()
    
    # 驗證
    is_valid, errors = validator.validate_ohlcv_data(df, strict=strict)
    
    # 如果不嚴格且有錯誤，則清理資料
    if not strict and not is_valid:
        df = validator.clean_ohlcv_data(df, method='drop')
        # 再次驗證
        validator.validate_ohlcv_data(df, strict=True)
    
    return df


if __name__ == "__main__":
    # 測試範例
    validator = DataValidator()
    
    # 創建測試資料
    test_data = pd.DataFrame({
        'open': [100, 101, np.nan, 103],
        'high': [102, 103, 104, 105],
        'low': [99, 100, 101, 102],
        'close': [101, 102, 103, 104],
        'volume': [1000, 1200, 1100, -100]  # 包含異常值
    })
    
    print("=" * 80)
    print("測試 OHLCV 驗證")
    print("=" * 80)
    
    # 驗證（非嚴格模式）
    is_valid, errors = validator.validate_ohlcv_data(test_data, strict=False)
    print(f"\n驗證結果: {'通過' if is_valid else '失敗'}")
    if errors:
        print("發現的問題:")
        for error in errors:
            print(f"  - {error}")
    
    # 清理資料
    print("\n" + "=" * 80)
    print("清理資料")
    print("=" * 80)
    clean_data = validator.clean_ohlcv_data(test_data, method='fill')
    print(f"\n清理後資料:\n{clean_data}")
    
    # 再次驗證
    is_valid, errors = validator.validate_ohlcv_data(clean_data, strict=False)
    print(f"\n清理後驗證結果: {'通過' if is_valid else '失敗'}")
    
    # 顯示驗證報告
    print("\n" + "=" * 80)
    print("驗證報告")
    print("=" * 80)
    report = validator.get_validation_report()
    print(f"\n總驗證次數: {report['total_validations']}")
    print(f"通過次數: {report['passed_validations']}")
    print(f"失敗次數: {report['failed_validations']}")
    print(f"通過率: {report['pass_rate']:.1%}")
