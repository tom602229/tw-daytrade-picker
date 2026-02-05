"""
錯誤處理基礎模組

提供統一的錯誤處理機制，確保系統在異常情況下能夠安全處理並記錄。
適用於所有交易系統模組。

Author: TW DayTrade Picker
Version: 2.0
"""

import logging
import functools
import traceback
from typing import Callable, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class TradingError(Exception):
    """交易系統基礎錯誤類別"""
    pass


class DataValidationError(TradingError):
    """資料驗證錯誤"""
    pass


class CalculationError(TradingError):
    """計算錯誤"""
    pass


class RiskManagementError(TradingError):
    """風險管理錯誤"""
    pass


class StrategyError(TradingError):
    """策略執行錯誤"""
    pass


class ErrorHandler:
    """
    統一錯誤處理器
    
    提供裝飾器和工具方法來處理各種錯誤情況
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化錯誤處理器
        
        Args:
            logger: 日誌記錄器，如果為 None 則創建默認記錄器
        """
        self.logger = logger or self._create_default_logger()
        self.error_count = 0
        self.error_log = []
    
    @staticmethod
    def _create_default_logger() -> logging.Logger:
        """創建默認日誌記錄器"""
        logger = logging.getLogger('TradingErrorHandler')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def safe_execute(
        self,
        default_return: Any = None,
        raise_on_error: bool = False,
        log_traceback: bool = True
    ) -> Callable:
        """
        安全執行裝飾器
        
        Args:
            default_return: 發生錯誤時的返回值
            raise_on_error: 是否在錯誤時拋出異常
            log_traceback: 是否記錄完整堆疊追蹤
        
        Returns:
            裝飾器函數
        
        Example:
            @error_handler.safe_execute(default_return=0.0)
            def calculate_rsi(data):
                # 可能會出錯的計算
                return rsi_value
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.error_count += 1
                    error_info = {
                        'timestamp': datetime.now(),
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'args': str(args)[:100],  # 限制長度
                        'kwargs': str(kwargs)[:100]
                    }
                    self.error_log.append(error_info)
                    
                    # 記錄錯誤
                    if log_traceback:
                        self.logger.error(
                            f"Error in {func.__name__}: {str(e)}\n"
                            f"Traceback: {traceback.format_exc()}"
                        )
                    else:
                        self.logger.error(
                            f"Error in {func.__name__}: {str(e)}"
                        )
                    
                    # 決定是否拋出異常
                    if raise_on_error:
                        raise
                    
                    return default_return
            
            return wrapper
        return decorator
    
    @staticmethod
    def validate_dataframe(
        df: pd.DataFrame,
        required_columns: list,
        min_rows: int = 1,
        check_nan: bool = True
    ) -> bool:
        """
        驗證 DataFrame 是否符合要求
        
        Args:
            df: 要驗證的 DataFrame
            required_columns: 必須存在的列名
            min_rows: 最小行數
            check_nan: 是否檢查 NaN 值
        
        Returns:
            是否通過驗證
        
        Raises:
            DataValidationError: 驗證失敗時
        """
        # 檢查是否為 DataFrame
        if not isinstance(df, pd.DataFrame):
            raise DataValidationError(f"Expected DataFrame, got {type(df)}")
        
        # 檢查是否為空
        if df.empty:
            raise DataValidationError("DataFrame is empty")
        
        # 檢查行數
        if len(df) < min_rows:
            raise DataValidationError(
                f"DataFrame has {len(df)} rows, minimum required: {min_rows}"
            )
        
        # 檢查必要的列
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise DataValidationError(
                f"Missing required columns: {missing_columns}"
            )
        
        # 檢查 NaN 值
        if check_nan:
            for col in required_columns:
                if df[col].isna().any():
                    nan_count = df[col].isna().sum()
                    raise DataValidationError(
                        f"Column '{col}' contains {nan_count} NaN values"
                    )
        
        return True
    
    @staticmethod
    def safe_division(
        numerator: float,
        denominator: float,
        default: float = 0.0
    ) -> float:
        """
        安全除法，避免除以零
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 除以零時的默認值
        
        Returns:
            計算結果或默認值
        """
        try:
            if denominator == 0 or np.isnan(denominator) or np.isinf(denominator):
                return default
            
            result = numerator / denominator
            
            # 檢查結果是否有效
            if np.isnan(result) or np.isinf(result):
                return default
            
            return result
        except:
            return default
    
    @staticmethod
    def clean_nan(
        value: Any,
        default: Any = 0.0,
        strategy: str = 'replace'
    ) -> Any:
        """
        清理 NaN 值
        
        Args:
            value: 要清理的值（可以是單一值或 Series）
            default: NaN 的替換值
            strategy: 處理策略 ('replace', 'forward_fill', 'drop')
        
        Returns:
            清理後的值
        """
        if isinstance(value, pd.Series):
            if strategy == 'replace':
                return value.fillna(default)
            elif strategy == 'forward_fill':
                return value.fillna(method='ffill').fillna(default)
            elif strategy == 'drop':
                return value.dropna()
            else:
                return value.fillna(default)
        else:
            # 單一值處理
            if pd.isna(value) or np.isnan(value) if isinstance(value, (int, float)) else False:
                return default
            return value
    
    @staticmethod
    def validate_price(price: float, min_price: float = 0.01) -> bool:
        """
        驗證價格是否有效
        
        Args:
            price: 要驗證的價格
            min_price: 最小有效價格
        
        Returns:
            是否為有效價格
        
        Raises:
            DataValidationError: 價格無效時
        """
        if pd.isna(price) or np.isnan(price):
            raise DataValidationError(f"Price is NaN")
        
        if np.isinf(price):
            raise DataValidationError(f"Price is infinite")
        
        if price <= 0:
            raise DataValidationError(f"Price must be positive, got {price}")
        
        if price < min_price:
            raise DataValidationError(
                f"Price {price} below minimum {min_price}"
            )
        
        return True
    
    @staticmethod
    def validate_quantity(quantity: int, max_quantity: int = 1000) -> bool:
        """
        驗證交易數量是否有效
        
        Args:
            quantity: 要驗證的數量（單位：張）
            max_quantity: 最大允許數量
        
        Returns:
            是否為有效數量
        
        Raises:
            DataValidationError: 數量無效時
        """
        if pd.isna(quantity):
            raise DataValidationError("Quantity is NaN")
        
        if quantity < 0:
            raise DataValidationError(f"Quantity cannot be negative: {quantity}")
        
        if quantity > max_quantity:
            raise DataValidationError(
                f"Quantity {quantity} exceeds maximum {max_quantity}"
            )
        
        return True
    
    def get_error_summary(self) -> dict:
        """
        獲取錯誤統計摘要
        
        Returns:
            包含錯誤統計的字典
        """
        return {
            'total_errors': self.error_count,
            'recent_errors': self.error_log[-10:] if self.error_log else [],
            'error_types': self._count_error_types()
        }
    
    def _count_error_types(self) -> dict:
        """統計各類型錯誤的數量"""
        error_types = {}
        for error in self.error_log:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return error_types
    
    def reset_error_log(self):
        """重置錯誤日誌"""
        self.error_count = 0
        self.error_log = []
        self.logger.info("Error log has been reset")


# 創建全局錯誤處理器實例
global_error_handler = ErrorHandler()


def safe_calculate(default_return: Any = None):
    """
    快速裝飾器：使用全局錯誤處理器
    
    Example:
        @safe_calculate(default_return=0.0)
        def my_calculation(data):
            return risky_operation(data)
    """
    return global_error_handler.safe_execute(
        default_return=default_return,
        raise_on_error=False
    )


if __name__ == "__main__":
    # 測試範例
    error_handler = ErrorHandler()
    
    @error_handler.safe_execute(default_return=0.0)
    def test_calculation(a, b):
        """測試函數"""
        return a / b
    
    # 正常情況
    print("正常計算:", test_calculation(10, 2))
    
    # 除以零
    print("除以零:", test_calculation(10, 0))
    
    # 測試 DataFrame 驗證
    df = pd.DataFrame({
        'open': [100, 101, 102],
        'close': [101, 102, 103]
    })
    
    try:
        ErrorHandler.validate_dataframe(
            df,
            required_columns=['open', 'close', 'high', 'low'],
            min_rows=3
        )
    except DataValidationError as e:
        print(f"驗證錯誤: {e}")
    
    # 顯示錯誤摘要
    print("\n錯誤摘要:", error_handler.get_error_summary())
