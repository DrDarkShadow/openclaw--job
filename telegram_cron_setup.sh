#!/bin/bash
# Setup cron job for Telegram notifications every 2 hours

echo "================================================================================"
echo "🕐 SETTING UP TELEGRAM JOB NOTIFICATIONS (2-HOUR INTERVAL)"
echo "================================================================================"

CRON_JOB="0 */2 * * * cd /home/ubuntu/.openclaw/workspace/jobs && ./run_telegram_notifier.sh >> /home/ubuntu/.openclaw/workspace/jobs/telegram_notifier_cron.log 2>&1"

# Add to crontab
(crontab -l 2>/dev/null; echo "") | crontab -  # Ensure blank line
(crontab -l 2>/dev/null; echo "# Telegram Job Notifier - Runs every 2 hours") | crontab -
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Added cron job:"
echo "   $CRON_JOB"

# Show current crontab
echo ""
echo "📋 CURRENT CRONTAB:"
echo "────────────────────────────────────────────────────────────────────────────────"
crontab -l 2>/dev/null | grep -A2 -B2 "telegram_notifier"
echo "────────────────────────────────────────────────────────────────────────────────"

# Create log file
touch /home/ubuntu/.openclaw/workspace/jobs/telegram_notifier_cron.log
chmod 644 /home/ubuntu/.openclaw/workspace/jobs/telegram_notifier_cron.log

# Test run (first time)
echo ""
echo "🧪 TESTING FIRST RUN..."
cd /home/ubuntu/.openclaw/workspace/jobs && ./run_telegram_notifier.sh

echo ""
echo "🔧 DEDUPLICATION FEATURES:"
echo "   • SQLite database (seen_jobs.db) tracks unique jobs"
echo "   • Only jobs < 24 hours old are sent"
echo "   • Skip if no new jobs in fresh_jobs.md"
echo ""
echo "📊 NEXT RUN SCHEDULE:"
echo "   Runs at: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00,"
echo "            16:00, 18:00, 20:00, 22:00 (every 2 hours)"
echo ""
echo "✅ Setup complete! You'll receive Telegram notifications every 2 hours."
echo "   Logs: ~/.openclaw/workspace/jobs/telegram_notifier_cron.log"
echo "================================================================================"