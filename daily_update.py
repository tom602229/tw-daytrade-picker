#!/usr/bin/env python3
"""
台股當沖選股系統 - 每日自動更新腳本
功能：
1. 抓取最新交易日的股票資料
2. 執行策略 C 分析
3. 生成候選股清單和報告
4. 清理超過 30 天的舊資料
"""

import os
import sys
import datetime as dt
import shutil
from pathlib import Path

# 加入專案路徑
PROJECT_ROOT = Path(__file__).parent
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    
# 同時設定環境變數確保子程序也能找到模組
os.environ['PYTHONPATH'] = src_path + os.pathsep + os.environ.get('PYTHONPATH', '')

from daytrade_picker.sources.twse_tpex import fetch_daily_prices_all, fetch_institution_net_all


def get_latest_trading_day():
    """取得最新交易日（排除週末）"""
    today = dt.date.today()
    
    # 如果是週六，往前推到週五
    if today.weekday() == 5:  # Saturday
        return today - dt.timedelta(days=1)
    # 如果是週日，往前推到週五
    elif today.weekday() == 6:  # Sunday
        return today - dt.timedelta(days=2)
    else:
        return today


def ensure_data_dir():
    """確保資料目錄存在"""
    data_dir = PROJECT_ROOT / "data" / "daily"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def cleanup_old_data(days_to_keep=30):
    """清理超過指定天數的舊資料"""
    print(f"\n🧹 清理超過 {days_to_keep} 天的舊資料...")
    
    cutoff_date = dt.date.today() - dt.timedelta(days=days_to_keep)
    
    # 清理每日資料
    data_dir = PROJECT_ROOT / "data" / "daily"
    if data_dir.exists():
        for file in data_dir.glob("*.csv"):
            try:
                # 從檔名解析日期 (格式: prices_YYYY-MM-DD.csv)
                date_str = file.stem.split('_')[-1]
                file_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                
                if file_date < cutoff_date:
                    file.unlink()
                    print(f"  ✓ 刪除: {file.name}")
            except (ValueError, IndexError):
                continue
    
    # 清理結果目錄
    results_dir = PROJECT_ROOT / "DayTradePicker_Results"
    if results_dir.exists():
        for file in results_dir.glob("strategyC_candidates_*.csv"):
            try:
                date_str = file.stem.split('_')[-1]
                file_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                
                if file_date < cutoff_date:
                    file.unlink()
                    print(f"  ✓ 刪除: {file.name}")
            except (ValueError, IndexError):
                continue
    
    print("✅ 清理完成")


def fetch_and_save_data(target_date):
    """抓取並儲存指定日期的股票資料"""
    data_dir = ensure_data_dir()
    
    print(f"\n📥 抓取 {target_date} 的股票資料...")
    
    # 1. 抓取價格資料
    print("  - 抓取價格資料...")
    try:
        df_prices = fetch_daily_prices_all(target_date)
        
        if len(df_prices) == 0:
            print("  ⚠️  無價格資料（可能是假日或資料尚未公布）")
            return False
        
        prices_file = data_dir / f"prices_{target_date}.csv"
        df_prices.to_csv(prices_file, index=False, encoding='utf-8-sig')
        print(f"  ✓ 儲存 {len(df_prices)} 筆價格資料至: {prices_file.name}")
        
    except Exception as e:
        print(f"  ❌ 價格資料抓取失敗: {e}")
        return False
    
    # 2. 抓取法人資料
    print("  - 抓取三大法人資料...")
    try:
        df_inst = fetch_institution_net_all(target_date)
        
        if len(df_inst) > 0:
            inst_file = data_dir / f"institution_{target_date}.csv"
            df_inst.to_csv(inst_file, index=False, encoding='utf-8-sig')
            print(f"  ✓ 儲存 {len(df_inst)} 筆法人資料至: {inst_file.name}")
        else:
            print("  ⚠️  無法人資料")
            
    except Exception as e:
        print(f"  ⚠️  法人資料抓取失敗: {e}")
        # 法人資料不是必須，繼續執行
    
    return True


def run_strategy_c(target_date):
    """執行策略 C 分析"""
    print(f"\n🎯 執行策略 C 分析...")
    
    try:
        import pandas as pd
        from daytrade_picker.strategy_c.real_run import run_strategy_c_real
        
        # 設定路徑
        config_path = PROJECT_ROOT / "config" / "config_enhanced_v2.yml"
        market_dir = PROJECT_ROOT / "data" / "daily"
        themes_path = PROJECT_ROOT / "data" / "themes_mapping.csv"
        out_dir = PROJECT_ROOT / "DayTradePicker_Results"
        
        # 檢查必要檔案
        prices_file = market_dir / f"prices_{target_date}.csv"
        if not prices_file.exists():
            print(f"❌ 找不到價格資料: {prices_file}")
            return False
        
        # 將 prices_*.csv 複製/重命名為 market_*.csv（策略需要這個格式）
        market_file = market_dir / f"market_{target_date}.csv"
        if not market_file.exists():
            import shutil
            shutil.copy(prices_file, market_file)
            print(f"  ✓ 建立 market 格式檔案: {market_file.name}")
        
        # 檢查 themes_mapping.csv
        if not themes_path.exists():
            print("  ⚠️  themes_mapping.csv 不存在，使用預設產業分類")
            # 建立基本的 themes mapping
            df = pd.read_csv(prices_file)
            themes_df = pd.DataFrame({
                'stock_id': df['stock_id'].unique(),
                'themes': 'UNKNOWN'
            })
            themes_df.to_csv(themes_path, index=False, encoding='utf-8-sig')
        
        # 執行策略
        candidates = run_strategy_c_real(
            trade_date=target_date,
            config_path=config_path,
            market_dir=market_dir,
            themes_mapping_path=themes_path,
            history_days=60,  # 使用 60 天歷史資料
            out_dir=out_dir
        )
        
        if len(candidates) > 0:
            print(f"\n✅ 策略分析完成")
            print(f"  找到 {len(candidates)} 檔候選股")
            print(f"  結果已儲存至: DayTradePicker_Results/")
            return True
        else:
            print("\n⚠️  未找到符合條件的候選股")
            return False
            
    except Exception as e:
        print(f"❌ 執行策略時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("=" * 70)
    print("🚀 台股當沖選股系統 - 每日自動更新")
    print("=" * 70)
    
    # 取得最新交易日
    target_date = get_latest_trading_day()
    print(f"\n📅 目標日期: {target_date} ({target_date.strftime('%A')})")
    
    # 1. 清理舊資料
    cleanup_old_data(days_to_keep=30)
    
    # 2. 抓取最新資料
    success = fetch_and_save_data(target_date)
    
    if not success:
        print("\n❌ 資料抓取失敗，程式結束")
        print("\n💡 提示:")
        print("  - 台股盤後資料通常在下午 5:00-6:00 後才會公布")
        print("  - 如果是假日或非交易日，請等待下一個交易日")
        return 1
    
    # 3. 執行策略分析
    strategy_success = run_strategy_c(target_date)
    
    if strategy_success:
        print("\n" + "=" * 70)
        print("✅ 每日更新完成！")
        print("=" * 70)
        
        # 顯示結果檔案位置
        results_dir = PROJECT_ROOT / "DayTradePicker_Results"
        latest_csv = results_dir / f"strategyC_candidates_{target_date}.csv"
        
        if latest_csv.exists():
            print(f"\n📄 最新候選股清單: {latest_csv}")
            print(f"\n💡 下一步:")
            print(f"  python -m daytrade_picker report {target_date}")
        
        return 0
    else:
        print("\n⚠️  資料已更新，但策略分析失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
