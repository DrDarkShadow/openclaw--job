#!/bin/bash
# Setup Job Finder System
# Complete setup with cron jobs and everything

set -e

echo "🛠️  Setting up Job Finder System..."

# Check Python version
python3 --version

# Install required packages
echo "📦 Installing Python packages..."
pip3 install aiohttp requests

# Make scripts executable
chmod +x job_notifier.py
chmod +x job_scraper.py
chmod +x telegram_notifier.py

echo "🔧 Creating required directories..."
mkdir -p /home/ubuntu/.openclaw/workspace/memory

# Create default config if doesn't exist
if [ ! -f config.json ]; then
    echo "📝 Creating default config.json..."
    cat > config.json << EOF
{
  "user": {
    "name": "Developer",
    "email": "dev@example.com"
  },
  "search": {
    "keywords": ["software engineer", "data scientist", "machine learning", "full stack"],
    "skills": ["python", "javascript", "react", "node.js"],
    "locations": ["Remote", "Bangalore", "Gurugram", "Pune", "Hyderabad"],
    "experience": {
      "min": 2,
      "max": 10
    }
  },
  "filters": {
    "minSalary": 1500000,
    "postedWithinDays": 7,
    "remoteOnly": false
  },
  "notifications": {
    "enabled": true,
    "channels": ["console", "file"],
    "telegram": {
      "chatId": "1304657802"
    },
    "rateLimit": {
      "maxPerHour": 10,
      "minMatchScore": 70
    }
  },
  "sources": {
    "linkedin": {
      "enabled": true,
      "geoId": "102713006"
    },
    "naukri": {
      "enabled": false
    }
  },
  "respectful": {
    "delayBetweenRequestsMs": 2000,
    "maxRetries": 3,
    "retryDelayMs": 5000
  }
}
EOF
fi

# Create initial fresh jobs file
if [ ! -f fresh_jobs.md ]; then
    echo "📋 Creating initial fresh_jobs.md..."
    echo "💤 No new jobs found yet. First run will populate this." > fresh_jobs.md
fi

# Test the system
echo "🧪 Testing the system..."
echo "Running job scraper..."
python3 job_scraper.py

echo "Running job notifier..."
python3 job_notifier.py

echo ""
echo "📊 System Summary:"
echo "✅ job_notifier.py - Main notification system"
echo "✅ job_scraper.py - Job scraping system"
echo "✅ telegram_notifier.py - Legacy Telegram notifier"
echo "✅ fresh_jobs.md - Fresh jobs storage"
echo "✅ config.json - Configuration file"
echo "✅ jobs/job_notifications.md - Generated notifications for heartbeat"

# Setup cron jobs
echo ""
echo "⏰ Setting up cron jobs..."
# Clear any existing job finder crons
crontab -l > /tmp/current_crons 2>/dev/null || true
grep -v "job_notifier\|job_scraper" /tmp/current_crons > /tmp/cleaned_crons || true

# Add new crons
echo "# Job Finder System - Run every 2 hours" >> /tmp/cleaned_crons
echo "0 */2 * * * cd /home/ubuntu/.openclaw/workspace/jobs && /usr/bin/python3 /home/ubuntu/.openclaw/workspace/jobs/job_notifier.py >> /tmp/job_notifier_cron.log 2>&1" >> /tmp/cleaned_crons
echo "30 */2 * * * cd /home/ubuntu/.openclaw/workspace/jobs && /usr/bin/python3 /home/ubuntu/.openclaw/workspace/jobs/job_scraper.py >> /tmp/job_scraper_cron.log 2>&1" >> /tmp/cleaned_crons

# Install the crontab
crontab /tmp/cleaned_crons

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 What's working:"
echo "1. Every 2 hours: job_notifier.py runs and checks fresh_jobs.md"
echo "2. If new jobs found: Sends notification via heartbeat system"
echo "3. Every 2 hours: job_scraper.py simulates finding new jobs"
echo ""
echo "🔍 Manual test:"
echo "  cd /home/ubuntu/.openclaw/workspace/jobs"
echo "  ./job_notifier.py"
echo ""
echo "📁 Important files:"
echo "  - jobs/fresh_jobs.md: Latest found jobs"
echo "  - jobs/filtered_jobs_summary.md: Filtered job matches"
echo "  - jobs/job_notifications.md: Ready notifications"
echo "  - /tmp/job_*_cron.log: Cron logs"
echo ""
echo "⚙️  Customize:"
echo "  1. Edit config.json: Change keywords, locations, salary"
echo "  2. Edit job_notifier.py: Modify filters and preferences"
echo "  3. Edit job_scraper.py: Add real scraping code"
echo ""
echo "🚀 Next steps:"
echo "  1. Replace job_scraper.py with real LinkedIn/Indeed scraping"
echo "  2. Configure actual notification channels (Telegram bot)"
echo "  3. Add more job sources (Naukri, Glassdoor, etc.)"