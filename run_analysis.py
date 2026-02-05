#!/usr/bin/env python3
"""
簡化版策略分析腳本 - 直接執行不依賴複雜導入
"""
import sys
import os
from pathlib import Path
import datetime as dt

# 設定路徑
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import yaml

# 直接導入需要的函數
from daytrade_picker.strategy_c.strategy import run_strategy_c


def main():
    target_date = dt.date(2026, 2, 5)
    
    print(f"🎯 執行策略 C 分析 ({target_date})")
    print("=" * 70)
    
    # 1. 讀取設定
    config_path = PROJECT_ROOT / "config" / "config_enhanced_v2.yml"
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    print("✓ 載入設定檔")
    
    # 2. 讀取價格資料
    prices_file = PROJECT_ROOT / "data" / "daily" / f"prices_{target_date}.csv"
    if not prices_file.exists():
        print(f"❌ 找不到價格資料: {prices_file}")
        return 1
    
    df_prices = pd.read_csv(prices_file, encoding='utf-8-sig')
    print(f"✓ 載入價格資料: {len(df_prices):,} 筆")
    
    # 3. 準備資料格式
    # 添加必要的欄位
    if 'trade_date' not in df_prices.columns:
        df_prices['trade_date'] = target_date
    df_prices['trade_date'] = pd.to_datetime(df_prices['trade_date']).dt.date
    
    # 確保必要欄位存在
    required_cols = ['stock_id', 'open', 'high', 'low', 'close', 'volume', 'pct_change']
    for col in required_cols:
        if col not in df_prices.columns:
            if col == 'pct_change':
                df_prices[col] = 0.0
            else:
                print(f"⚠️  缺少欄位: {col}")
    
    # 添加漲跌停標記（如果沒有）
    if 'is_limit_up' not in df_prices.columns:
        df_prices['is_limit_up'] = False
    if 'is_limit_down' not in df_prices.columns:
        df_prices['is_limit_down'] = False
    if 'turnover' not in df_prices.columns:
        df_prices['turnover'] = 0
    
    # 4. 準備股票元數據
    stock_meta = df_prices[['stock_id', 'name']].copy()
    stock_meta = stock_meta.rename(columns={'name': 'stock_name'})
    stock_meta = stock_meta.drop_duplicates(subset=['stock_id'])
    
    # 添加市場和產業資訊
    stock_meta['market'] = stock_meta['stock_id'].apply(
        lambda x: 'TWSE' if len(str(x)) == 4 else 'TPEX'
    )
    stock_meta['industry'] = 'UNKNOWN'
    
    print(f"✓ 準備股票元數據: {len(stock_meta):,} 檔")
    
    # 5. 執行策略
    print("\n執行策略分析...")
    try:
        candidates, top_picks, sec_rank, strong_sectors = run_strategy_c(
            trade_date=target_date,
            stock_meta=stock_meta,
            daily_price=df_prices,
            risk_flags=None,
            cfg=cfg,
            sector_mode='industry'
        )
        
        print(f"✅ 分析完成")
        print(f"   候選股數量: {len(candidates)}")
        print(f"   強勢產業: {len(strong_sectors)}")
        
        # 6. 儲存結果
        if len(candidates) > 0:
            results_dir = PROJECT_ROOT / "DayTradePicker_Results"
            results_dir.mkdir(exist_ok=True)
            
            # 合併股票名稱
            output = candidates.merge(
                stock_meta[['stock_id', 'stock_name', 'market']], 
                on='stock_id', 
                how='left'
            )
            
            csv_path = results_dir / f"strategyC_candidates_{target_date}.csv"
            output.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"   ✓ 結果已儲存: {csv_path.name}")
            
            # 顯示前 10 檔
            print(f"\n📊 Top 10 候選股:")
            top10 = output.head(10)
            display_cols = ['stock_id', 'stock_name', 'score_total', 'suggest_entry', 'suggest_stop']
            for col in display_cols:
                if col not in top10.columns:
                    if col == 'score_total':
                        top10[col] = 0
                    else:
                        top10[col] = ''
            
            for idx, row in top10.iterrows():
                print(f"   {row['stock_id']:6s} {str(row.get('stock_name', ''))[:10]:10s} "
                      f"分數: {row.get('score_total', 0):5.2f} "
                      f"進場: {row.get('suggest_entry', 0):6.2f} "
                      f"停損: {row.get('suggest_stop', 0):6.2f}")
            
            return 0
        else:
            print("   未找到符合條件的候選股")
            return 0
            
    except Exception as e:
        print(f"❌ 策略執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
