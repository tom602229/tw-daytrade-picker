#!/bin/bash
# 設定每日自動執行的 cron job
# 建議執行時間：每天下午 6:00（台股盤後資料已公布）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/daily_update.py"
LOG_DIR="$SCRIPT_DIR/logs"

# 建立 log 目錄
mkdir -p "$LOG_DIR"

# 顯示當前 cron 設定
echo "當前的 cron jobs:"
crontab -l 2>/dev/null || echo "（無現有 cron jobs）"
echo ""
echo "================================"
echo "建議的 cron job 設定："
echo "================================"
echo ""
echo "# 每天下午 6:00 執行台股當沖選股系統更新"
echo "0 18 * * * cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT >> $LOG_DIR/daily_\$(date +\%Y\%m\%d).log 2>&1"
echo ""
echo "================================"
echo "手動加入 cron job 的步驟："
echo "================================"
echo "1. 執行: crontab -e"
echo "2. 加入上方的 cron job 設定"
echo "3. 儲存並退出"
echo ""
echo "或者使用以下指令自動加入："
echo "================================"
echo "(crontab -l 2>/dev/null; echo '0 18 * * * cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT >> $LOG_DIR/daily_\$(date +\%Y\%m\%d).log 2>&1') | crontab -"
echo ""
echo "💡 其他執行時間建議："
echo "  - 0 18 * * 1-5  （週一到週五 6:00 PM，排除週末）"
echo "  - 30 17 * * *   （每天 5:30 PM，提早一點）"
echo "  - 0 19 * * *    （每天 7:00 PM，確保資料已公布）"
