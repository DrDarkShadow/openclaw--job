# OpenClaw Job Finder - Complete Setup Guide

## 📋 System Overview

This is a complete job finding automation system that integrates natively with OpenClaw. The system:

1. **Scrapes job listings** every 2 hours (simulated or real LinkedIn scraping)
2. **Filters jobs** based on your preferences (keywords, location, salary)
3. **Sends notifications** via OpenClaw's messaging system (Discord/Telegram/etc.)
4. **Maintains state** to avoid duplicate notifications
5. **Runs automatically** via cron jobs

## 🚀 Quick Installation

```bash
# Navigate to jobs directory
cd /home/ubuntu/.openclaw/workspace/jobs

# Run the setup script
bash setup_job_finder.sh
```

This will:
- ✅ Install required Python packages
- ✅ Set up cron jobs for automatic execution
- ✅ Create all necessary data files
- ✅ Test the system

## ⚙️ Configuration

### 1. Job Preferences (`config.json`)
Edit `config.json` to customize your job search:

```json
{
  "keywords": ["AI", "Machine Learning", "Data Science"],
  "locations": ["Remote", "Noida", "Bengaluru"],
  "salary_range": "70000-",
  "platforms": ["LinkedIn"]
}
```

### 2. Heartbeat Configuration (`HEARTBEAT.md`)
The system uses OpenClaw's heartbeat system to check for jobs every 2 hours.

```markdown
# HEARTBEAT.md
- Check jobs every 2 hours (120 minutes)
- Report new jobs if found
- Send "no new jobs" if none found
```

### 3. OpenClaw Context Files

The system uses these OpenClaw context files for operation:

| File | Purpose |
|------|---------|
| `SOUL.md` | AI personality and behavior |
| `AGENTS.md` | Workspace protocols |
| `USER.md` | User information |
| `IDENTITY.md` | AI identity |
| `WORKFLOW_AUTO.md` | Automation workflows |
| `TOOLS.md` | Local tool config |

## 🔄 How It Works

### Job Scraping Flow:
1. **job_scraper.py** scrapes/simulates job listings
2. **job_notifier.py** checks `fresh_jobs.md` every 2 hours
3. **Filters** jobs based on your preferences
4. **Sends notifications** via OpenClaw messaging
5. **Updates state** in `heartbeat-state.json`

### Notification Format:
```
📢 Found 3 fresh matches:

🔥 AI Expert
   🏢 WSP in New Zealand (Noida, Uttar Pradesh, India)
   ⏳ 10 minutes ago
   🔗 [Apply Link]
```

## 🛠️ File Structure

```
jobs/
├── job_scraper.py          # Job scraping module
├── job_notifier.py         # Notification engine
├── config.json            # User preferences
├── setup_job_finder.sh    # Installation script
├── docs/                  # Documentation
│   ├── AGENTS.md
│   ├── HEARTBEAT.md
│   ├── SOUL.md
│   ├── USER.md
│   ├── IDENTITY.md
│   ├── WORKFLOW_AUTO.md
│   ├── TOOLS.md
│   └── SETUP_GUIDE.md
├── templates/             # Example templates
│   ├── fresh_jobs_example.md
│   ├── filtered_jobs_example.md
│   └── notification_example.md
├── README.md             # Main documentation
└── .gitignore           # Git exclusions
```

## 🔐 Security & Privacy

### Files NOT Included in Repository:
- `memory/*.md` - Daily logs (private)
- `MEMORY.md` - Curated memory (private)
- `resume.pdf` - Personal document
- `cookies.json` - Authentication data
- `email_config.json` - Email credentials
- `*.db` files - Job tracking databases

### Sensitive Data Protection:
- All authentication files are in `.gitignore`
- Memory files are excluded for privacy
- No hardcoded credentials in code
- Token authentication for GitHub

## 🤝 Integration with OpenClaw

The system works natively with OpenClaw:

1. **Heartbeat Integration**: Uses `HEARTBEAT.md` for scheduling
2. **Messaging Integration**: Sends notifications via built-in channels
3. **State Management**: Uses `heartbeat-state.json` for tracking
4. **Error Handling**: Graceful failure and logging

## 🐛 Troubleshooting

### Common Issues:

1. **No Jobs Found**
   - Check `config.json` filters aren't too restrictive
   - Verify scraping/simulation is working
   - Check cron jobs are running

2. **Notifications Not Sending**
   - Verify OpenClaw messaging is configured
   - Check `job_notifier.py` logs
   - Ensure heartbeat system is active

3. **Cron Jobs Not Running**
   - Run `crontab -l` to see scheduled jobs
   - Check system logs: `sudo tail -f /var/log/syslog`
   - Re-run setup script: `bash setup_job_finder.sh`

## 📈 Extending the System

### Add Real LinkedIn Scraping:
Replace the simulation in `job_scraper.py` with actual LinkedIn API calls or web scraping.

### Add More Job Boards:
Add additional scrapers for other platforms like Indeed, Naukri.com, etc.

### Custom Notifications:
Modify `job_notifier.py` to send emails, SMS, or other notification types.

## 📄 License & Credits

This system is part of the OpenClaw ecosystem. Developed for automated job search assistance.

**GitHub Repo**: `https://github.com/DrDarkShadow/openclaw--job.git`

*Note: This setup guide and system documentation are included in the repository to help others replicate and understand the complete OpenClaw job finder system.*