
import pandas as pd
from datetime import date

# 讀取今日資料
today = date(2026, 2, 5)
df = pd.read_csv(f'data/daily/prices_{today}.csv')

print(f"📊 今日股票資料摘要 ({today})")
print("=" * 70)
print(f"總筆數: {len(df):,} 筆")
print(f"\n前 10 檔股票:")
print(df.head(10)[['stock_id', 'name', 'close', 'volume']].to_string(index=False))

# 篩選有成交量的股票
active = df[df['volume'] > 0].copy()
print(f"\n有成交的股票: {len(active):,} 檔")

# 計算漲跌統計
active['is_up'] = active['change'] > 0
up_count = active['is_up'].sum()
down_count = (~active['is_up']).sum()

print(f"\n漲跌分布:")
print(f"  上漲: {up_count:,} 檔 ({up_count/len(active)*100:.1f}%)")
print(f"  下跌: {down_count:,} 檔 ({down_count/len(active)*100:.1f}%)")

# Top 10 成交量
print(f"\n🔥 成交量 Top 10:")
top_vol = active.nlargest(10, 'volume')[['stock_id', 'name', 'close', 'volume', 'change']]
print(top_vol.to_string(index=False))

print("\n✅ 資料測試完成！")
