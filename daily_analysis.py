#!/usr/bin/env python3
"""
台股當沖選股 - 每日自動分析腳本
整合資料抓取、分析、報告生成
"""
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
from io import StringIO
import time

# ============================================================
# 步驟 1: 抓取資料
# ============================================================

def fetch_twse_data():
    """從台灣證交所抓取近10個交易日資料"""
    print("\n" + "="*60)
    print("📥 步驟 1: 抓取台灣證交所資料")
    print("="*60)
    
    base_path = Path("code/tw-daytrade-picker/data/daily")
    base_path.mkdir(parents=True, exist_ok=True)
    
    # 抓取最近10天（確保有足夠交易日資料）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    dates_to_fetch = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 週一到週五
            dates_to_fetch.append(current)
        current += timedelta(days=1)
    
    print(f"準備抓取 {len(dates_to_fetch)} 個交易日資料...")
    
    for date in dates_to_fetch:
        date_str = date.strftime("%Y%m%d")
        date_filename = date.strftime("%Y-%m-%d")
        
        # 每日股價
        try:
            url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=csv&date={date_str}&type=ALL"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 100:
                lines = [line for line in resp.text.split('\n') if '=' not in line and len(line.split('",')) > 8]
                if lines:
                    csv_data = '\n'.join(lines)
                    df = pd.read_csv(StringIO(csv_data))
                    output_file = base_path / f"prices_{date_filename}.csv"
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"✓ 股價: {date_filename}")
            time.sleep(3)
        except Exception as e:
            print(f"✗ 股價 {date_filename}: {e}")
        
        # 市場統計
        try:
            url = f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=csv&date={date_str}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 100:
                lines = [line for line in resp.text.split('\n') if '=' not in line and len(line.split('",')) > 5]
                if lines:
                    csv_data = '\n'.join(lines)
                    df = pd.read_csv(StringIO(csv_data))
                    output_file = base_path / f"market_{date_filename}.csv"
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"✓ 市場: {date_filename}")
            time.sleep(3)
        except Exception as e:
            print(f"✗ 市場 {date_filename}: {e}")
        
        # 法人買賣
        try:
            url = f"https://www.twse.com.tw/fund/T86?response=csv&date={date_str}&selectType=ALL"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 100:
                lines = [line for line in resp.text.split('\n') if '=' not in line and len(line.split('",')) > 5]
                if lines:
                    csv_data = '\n'.join(lines)
                    df = pd.read_csv(StringIO(csv_data))
                    output_file = base_path / f"institution_{date_filename}.csv"
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"✓ 法人: {date_filename}")
            time.sleep(3)
        except Exception as e:
            print(f"✗ 法人 {date_filename}: {e}")
    
    print("\n✅ 資料抓取完成！")
    return True

# ============================================================
# 步驟 2: 分析資料
# ============================================================

def analyze_data():
    """執行當沖選股分析"""
    print("\n" + "="*60)
    print("📊 步驟 2: 執行當沖選股分析")
    print("="*60)
    
    # 這裡直接複製 analyze_with_targets.py 的核心邏輯
    from datetime import datetime, timedelta
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    # 找出最新的交易日
    data_dir = Path("code/tw-daytrade-picker/data/daily")
    price_files = sorted(data_dir.glob("prices_*.csv"))
    
    if not price_files:
        print("❌ 找不到股價資料檔案")
        return False
    
    latest_date = price_files[-1].stem.replace("prices_", "")
    print(f"分析日期: {latest_date}")
    
    # 載入資料
    prices_file = data_dir / f"prices_{latest_date}.csv"
    inst_file = data_dir / f"institution_{latest_date}.csv"
    
    df_prices = pd.read_csv(prices_file)
    df_inst = pd.read_csv(inst_file) if inst_file.exists() else pd.DataFrame()
    
    # 清理資料
    df_prices.columns = df_prices.columns.str.strip().str.replace('"', '')
    if not df_inst.empty:
        df_inst.columns = df_inst.columns.str.strip().str.replace('"', '')
    
    # 取得股價欄位名稱
    col_code = [c for c in df_prices.columns if '證券代號' in c][0]
    col_name = [c for c in df_prices.columns if '證券名稱' in c][0]
    col_close = [c for c in df_prices.columns if '收盤價' in c][0]
    col_volume = [c for c in df_prices.columns if '成交股數' in c][0]
    col_open = [c for c in df_prices.columns if '開盤價' in c][0]
    col_high = [c for c in df_prices.columns if '最高價' in c][0]
    col_low = [c for c in df_prices.columns if '最低價' in c][0]
    col_change = [c for c in df_prices.columns if '漲跌價差' in c][0]
    
    # 基本篩選
    df = df_prices.copy()
    df[col_close] = pd.to_numeric(df[col_close].astype(str).str.replace(',', ''), errors='coerce')
    df[col_volume] = pd.to_numeric(df[col_volume].astype(str).str.replace(',', ''), errors='coerce')
    df[col_open] = pd.to_numeric(df[col_open].astype(str).str.replace(',', ''), errors='coerce')
    df[col_high] = pd.to_numeric(df[col_high].astype(str).str.replace(',', ''), errors='coerce')
    df[col_low] = pd.to_numeric(df[col_low].astype(str).str.replace(',', ''), errors='coerce')
    df[col_change] = pd.to_numeric(df[col_change].astype(str).str.replace(',', ''), errors='coerce')
    
    # 篩選條件
    df = df[
        (df[col_close] >= 10) &
        (df[col_close] <= 200) &
        (df[col_volume] >= 1000)
    ].copy()
    
    # 計算指標
    df['volume_shares'] = df[col_volume] / 1000  # 張數
    df['change_pct'] = (df[col_change] / (df[col_close] - df[col_change])) * 100
    df['amplitude'] = ((df[col_high] - df[col_low]) / df[col_close]) * 100
    
    # 計算ATR (簡化版，使用當日振幅)
    df['atr'] = df[col_high] - df[col_low]
    
    # 合併法人資料
    if not df_inst.empty:
        col_inst_code = [c for c in df_inst.columns if '證券代號' in c][0]
        col_foreign = [c for c in df_inst.columns if '外陸資買賣超股數(不含外資自營商)' in c]
        col_trust = [c for c in df_inst.columns if '投信買賣超股數' in c]
        
        # 選擇需要的欄位
        inst_cols = [col_inst_code]
        col_mapping = {'stock_id': col_inst_code}
        
        if col_foreign:
            inst_cols.append(col_foreign[0])
            col_mapping['foreign_net'] = col_foreign[0]
        if col_trust:
            inst_cols.append(col_trust[0])
            col_mapping['trust_net'] = col_trust[0]
        
        df_inst_sub = df_inst[inst_cols].copy()
        df_inst_sub.columns = ['stock_id'] + list(col_mapping.keys())[1:]
        
        # 清理數值欄位
        for col in df_inst_sub.columns:
            if col != 'stock_id':
                df_inst_sub[col] = pd.to_numeric(
                    df_inst_sub[col].astype(str).str.replace(',', ''), 
                    errors='coerce'
                ).fillna(0)
        
        df = df.merge(df_inst_sub, left_on=col_code, right_on='stock_id', how='left')
        df['foreign_net'] = df.get('foreign_net', 0).fillna(0) / 1000  # 轉張數
        df['trust_net'] = df.get('trust_net', 0).fillna(0) / 1000
    else:
        df['foreign_net'] = 0
        df['trust_net'] = 0
    
    # 計算評分
    scores = []
    for _, row in df.iterrows():
        score = 50  # 基礎分
        
        # 振幅加分 (0-15分)
        amp = row['amplitude']
        if amp >= 5:
            score += 15
        elif amp >= 3:
            score += 10
        elif amp >= 2:
            score += 5
        
        # 成交量加分 (0-15分)
        vol = row['volume_shares']
        if vol >= 10000:
            score += 15
        elif vol >= 5000:
            score += 10
        elif vol >= 2000:
            score += 5
        
        # 法人買賣超加分 (0-20分)
        foreign = row.get('foreign_net', 0)
        trust = row.get('trust_net', 0)
        if foreign > 500 or trust > 100:
            score += 20
        elif foreign > 100 or trust > 50:
            score += 10
        elif foreign < -500 or trust < -100:
            score -= 10
        
        scores.append(score)
    
    df['score'] = scores
    
    # 排序並取前50
    df = df.sort_values('score', ascending=False).head(50)
    
    # 計算目標價和停損價
    results = []
    for _, row in df.iterrows():
        close = row[col_close]
        atr = row['atr']
        change_pct = row['change_pct']
        foreign = row.get('foreign_net', 0)
        
        # 判斷做多或做空
        if change_pct > 1 and foreign > 0:
            action = '做多'
            target_price = close + 2 * atr
            stop_loss = close - atr
            # 建議購買價：收盤價下方 0.5-1 個 ATR (取平均 0.75 ATR)
            suggested_buy = close - 0.75 * atr
        elif change_pct < -1 and foreign < 0:
            action = '做空'
            target_price = close - 2 * atr
            stop_loss = close + atr
            # 建議購買價（放空）：收盤價上方 0.5-1 個 ATR
            suggested_buy = close + 0.75 * atr
        else:
            action = '觀望'
            target_price = close + 2 * atr
            stop_loss = close - atr
            # 觀望時建議價格為當前收盤價
            suggested_buy = close
        
        target_pct = ((target_price - close) / close) * 100
        stop_pct = ((stop_loss - close) / close) * 100
        suggested_buy_pct = ((suggested_buy - close) / close) * 100
        
        if stop_pct != 0:
            risk_reward = f"1:{abs(target_pct / stop_pct):.2f}"
        else:
            risk_reward = "N/A"
        
        results.append({
            'stock_id': row[col_code],
            'name': row[col_name],
            'close': close,
            'suggested_buy': suggested_buy,
            'suggested_buy_pct': suggested_buy_pct,
            'volume': row['volume_shares'],
            'change_pct': change_pct,
            'amplitude': row['amplitude'],
            'foreign_net': foreign,
            'trust_net': row.get('trust_net', 0),
            'atr': atr,
            'score': row['score'],
            'action': action,
            'target_price': target_price,
            'target_pct': target_pct,
            'stop_loss': stop_loss,
            'stop_pct': stop_pct,
            'risk_reward': risk_reward
        })
    
    df_result = pd.DataFrame(results)
    
    # 儲存結果到分析目錄
    output_dir = Path("code/tw-daytrade-picker/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"daytrade_targets_{latest_date}.csv"
    df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # 同時儲存到本地指定路徑（使用日期格式如：2026-2-5.csv）
    try:
        local_path = Path(r"C:\Users\sdasd\OneDrive\桌面\stock")
        local_path.mkdir(parents=True, exist_ok=True)
        
        # 將日期格式從 2026-02-05 轉換為 2026-2-5
        date_parts = latest_date.split('-')
        year = date_parts[0]
        month = str(int(date_parts[1]))  # 移除前導零
        day = str(int(date_parts[2]))    # 移除前導零
        local_filename = f"{year}-{month}-{day}.csv"
        
        local_file = local_path / local_filename
        df_result.to_csv(local_file, index=False, encoding='utf-8-sig')
        print(f"✓ 本地儲存: {local_file}")
    except Exception as e:
        print(f"⚠️  本地儲存失敗（但分析已完成）: {e}")
    
    print(f"✅ 分析完成！篩選出 {len(df_result)} 檔潛力股")
    print(f"結果已儲存: {output_file}")
    
    return latest_date

# ============================================================
# 步驟 3: 生成報告
# ============================================================

def generate_report(analysis_date):
    """生成摘要報告"""
    print("\n" + "="*60)
    print("📝 步驟 3: 生成分析報告")
    print("="*60)
    
    analysis_file = Path(f"code/tw-daytrade-picker/analysis/daytrade_targets_{analysis_date}.csv")
    
    if not analysis_file.exists():
        print(f"❌ 找不到分析檔案: {analysis_file}")
        return False
    
    df = pd.read_csv(analysis_file)
    
    # 生成文字報告
    report_lines = [
        f"📊 台股當沖選股分析報告",
        f"📅 日期: {analysis_date}",
        f"{'='*60}",
        f"",
        f"🎯 篩選結果: 共 {len(df)} 檔潛力股",
        f"",
        f"🏆 TOP 5 推薦標的:",
        f""
    ]
    
    for i, row in df.head(5).iterrows():
        action_emoji = {
            '做多': '💹',
            '做空': '📉',
            '觀望': '⚪'
        }.get(row['action'], '❓')
        
        report_lines.extend([
            f"{i+1}. {row['stock_id']} {row['name']} - {action_emoji} {row['action']}",
            f"   收盤: ${row['close']:.2f}  評分: {row['score']:.1f}分",
            f"   建議買進: ${row['suggested_buy']:.2f} ({row['suggested_buy_pct']:+.2f}%)",
            f"   目標價: ${row['target_price']:.2f} ({row['target_pct']:+.2f}%)",
            f"   停損價: ${row['stop_loss']:.2f} ({row['stop_pct']:+.2f}%)",
            f"   報酬比: {row['risk_reward']}",
            f""
        ])
    
    # 統計資訊
    action_counts = df['action'].value_counts()
    report_lines.extend([
        f"",
        f"📈 訊號統計:",
        f"   做多: {action_counts.get('做多', 0)} 檔",
        f"   做空: {action_counts.get('做空', 0)} 檔",
        f"   觀望: {action_counts.get('觀望', 0)} 檔",
        f"",
        f"💡 風險提醒:",
        f"   • 嚴格遵守停損價，不要心存僥倖",
        f"   • 開盤後觀察 15-30 分鐘再進場",
        f"   • 單筆投入不超過總資金 10-20%",
        f"   • 當沖需密切關注盤勢變化",
        f"",
        f"📁 完整分析: analysis/daytrade_targets_{analysis_date}.csv",
        f"{'='*60}"
    ])
    
    report_text = "\n".join(report_lines)
    
    # 儲存報告
    report_file = Path(f"code/tw-daytrade-picker/analysis/report_{analysis_date}.txt")
    report_file.write_text(report_text, encoding='utf-8')
    
    print(report_text)
    print(f"\n✅ 報告已生成: {report_file.name}")
    
    return report_text

# ============================================================
# 步驟 4: 發送郵件通知
# ============================================================

def send_email_notification(analysis_date):
    """發送郵件通知"""
    print("\n" + "="*60)
    print("📧 步驟 4: 發送郵件通知")
    print("="*60)
    
    try:
        # 讀取報告內容
        report_file = Path(f"code/tw-daytrade-picker/analysis/report_{analysis_date}.txt")
        if not report_file.exists():
            print("❌ 報告檔案不存在，無法發送郵件")
            return False
        
        report_content = report_file.read_text(encoding='utf-8')
        
        # 讀取分析結果（用於附件）
        csv_file = Path(f"code/tw-daytrade-picker/analysis/daytrade_targets_{analysis_date}.csv")
        
        # 建立郵件內容
        email_subject = f"📊 台股當沖選股分析報告 - {analysis_date}"
        
        email_body = f"""
{report_content}

---

📎 附件包含完整的 50 檔潛力股分析資料（CSV格式）

💡 使用提醒：
- 本報告僅供參考，投資有風險，請謹慎評估
- 建議搭配其他技術指標與基本面分析
- 嚴格執行風險控管與停損策略

🔄 此為每日自動化分析報告
- 每個交易日下午 3:00 自動執行
- 資料來源：台灣證券交易所

---
Generated by Nebula AI
        """
        
        # 這裡僅打印郵件內容，實際發送會由 task recipe 中的步驟處理
        print("✅ 郵件內容已準備完成")
        print(f"   主旨: {email_subject}")
        print(f"   內容長度: {len(email_body)} 字元")
        print(f"   附件: {csv_file.name}")
        
        # 儲存郵件內容供後續使用
        email_file = Path(f"code/tw-daytrade-picker/analysis/email_{analysis_date}.txt")
        email_file.write_text(f"Subject: {email_subject}\n\n{email_body}", encoding='utf-8')
        
        return True
        
    except Exception as e:
        print(f"❌ 郵件準備失敗: {e}")
        return False

# ============================================================
# 主流程
# ============================================================

def main():
    """執行完整分析流程"""
    print("\n" + "="*60)
    print("🚀 台股當沖選股 - 每日自動分析")
    print("="*60)
    
    try:
        # 步驟 1: 抓取資料
        if not fetch_twse_data():
            print("\n❌ 資料抓取失敗")
            return False
        
        # 步驟 2: 分析資料
        analysis_date = analyze_data()
        if not analysis_date:
            print("\n❌ 分析執行失敗")
            return False
        
        # 步驟 3: 生成報告
        if not generate_report(analysis_date):
            print("\n❌ 報告生成失敗")
            return False
        
        # 步驟 4: 準備郵件通知
        if not send_email_notification(analysis_date):
            print("\n⚠️  郵件準備失敗（但分析已完成）")
        
        print("\n" + "="*60)
        print("✅ 每日分析流程完成！")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ 執行過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
