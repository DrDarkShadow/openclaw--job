#!/bin/bash
# Run Telegram notifier every 2 hours
# This script should be called by cron

cd "$(dirname "$0")" || exit 1
WORKSPACE_DIR="/home/ubuntu/.openclaw/workspace"
JOBS_DIR="$WORKSPACE_DIR/jobs"

# Activate virtualenv
source "$JOBS_DIR/venv/bin/activate"

echo "================================================================================"
echo "📱 TELEGRAM JOB NOTIFIER - $(date)"
echo "================================================================================"

# Check if scraper should run first
LAST_RUN_FILE="$JOBS_DIR/last_scrape.timestamp"
CURRENT_TIME=$(date +%s)
MIN_INTERVAL=$((2 * 60 * 60))  # 2 hours in seconds

if [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE")
    TIME_DIFF=$((CURRENT_TIME - LAST_RUN))
    
    if [ $TIME_DIFF -ge $MIN_INTERVAL ]; then
        echo "⏰ Time to scrape fresh jobs (last run: $TIME_DIFF seconds ago)"
        
        # Run scraper to get fresh jobs
        echo "🔄 Running job scraper..."
        node scraper.js --silent
        
        # Update last scrape time
        echo "$CURRENT_TIME" > "$LAST_RUN_FILE"
    else
        echo "⏳ Skipping scrape (only $TIME_DIFF seconds since last)"
    fi
else
    echo "⏰ First time scraping..."
    echo "🔄 Running job scraper..."
    node scraper.js --silent
    echo "$CURRENT_TIME" > "$LAST_RUN_FILE"
fi

# Run Telegram notifier
echo "📤 Sending to Telegram..."
python3 telegram_notifier.py

echo "✅ Telegram notifier completed at $(date)"
echo "================================================================================"