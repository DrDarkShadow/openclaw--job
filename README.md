# Job Search Automation System

An intelligent job monitoring system that automatically searches LinkedIn, Naukri, and other platforms for new job postings matching your criteria.

## 🚀 Quick Start

### 1. Configure Your Preferences

Edit `config.json` to set your job preferences:

```bash
cd jobs
# Edit with your details
nano config.json
```

**Key sections to customize:**
- `user` - Your name and email
- `search.keywords` - Job titles to search for
- `search.skills` - Your technical skills
- `search.locations` - Preferred locations
- `search.experience` - Your experience range
- `filters.minSalary` - Minimum expected salary
- `notifications` - How you want to be alerted

### 2. Initialize (First Run Only)

Mark all current jobs as "seen" so you only get alerts for NEW postings:

```bash
node scraper.js --init
```

### 3. Run a Test Check

Test the system without sending notifications:

```bash
node scraper.js --dry-run
```

### 4. Start Monitoring

Run once:
```bash
node scraper.js
```

Run continuously (daemon mode):
```bash
node scraper.js --daemon
```

## 📁 File Structure

```
jobs/
├── config.json          # Your preferences and filters
├── scraper.js          # Main monitoring engine
├── matcher.js          # Job matching/scoring logic
├── notifier.js         # Alert system
├── storage.js          # Tracks seen jobs
├── package.json        # Dependencies
├── seen-jobs.json      # Auto-generated (tracked jobs)
├── job-monitor.log     # Activity log
└── README.md           # This file
```

## ⚙️ Configuration

### Search Preferences

```json
{
  "search": {
    "keywords": ["software engineer", "full stack developer"],
    "skills": ["JavaScript", "Node.js", "React"],
    "locations": ["Remote", "Bangalore", "Hyderabad"],
    "experience": { "min": 2, "max": 8 }
  }
}
```

### Filters

```json
{
  "filters": {
    "minSalary": 1500000,
    "postedWithinDays": 7,
    "remoteOnly": false,
    "excludeCompanies": ["CompanyX"]
  }
}
```

### Notifications

```json
{
  "notifications": {
    "enabled": true,
    "channels": ["console", "file"],
    "rateLimit": {
      "maxPerHour": 10,
      "minMatchScore": 70
    }
  }
}
```

**Channels:**
- `console` - Print to terminal (default)
- `file` - Write to `job-alerts.log`
- `webhook` - Send to Discord/Slack (configure `webhookUrl`)
- `email` - Requires SMTP configuration

### Sources

```json
{
  "sources": {
    "linkedin": {
      "enabled": true,
      "geoId": "102713006"
    },
    "naukri": {
      "enabled": true
    }
  }
}
```

## 🔄 Automation (Cron)

To run automatically every 4 hours:

```bash
# Add to crontab
crontab -e

# Add this line (adjust path as needed)
0 */4 * * * cd /home/ubuntu/.openclaw/workspace/jobs && /usr/bin/node scraper.js >> /tmp/job-monitor-cron.log 2>&1
```

Or use daemon mode:
```bash
node scraper.js --daemon
```

## 🧪 Testing

Test the matcher with sample jobs:

```bash
npm test
# or
node -e "require('./matcher').test()"
```

## 📊 How Matching Works

Jobs are scored on multiple factors (max 100%):

| Factor | Weight |
|--------|--------|
| Keyword match (title/description) | 30% |
| Skills match | 40% |
| Location match | 15% |
| Job type match | 10% |
| Experience match | 5% |

Minimum match score (default 70%) required for notification.

## 🛡️ Respecting Job Sites

The system includes several protections:

- **Rate limiting** - Configurable delays between requests (default 2s)
- **Retry logic** - Exponential backoff on failures
- **User-Agent** - Identifies as automated tool
- **Request limits** - Caps max jobs per check (default 50)
- **Storage** - Remembers seen jobs to avoid re-checking

Adjust in `config.json`:
```json
{
  "respectful": {
    "delayBetweenRequestsMs": 2000,
    "maxRetries": 3,
    "retryDelayMs": 5000
  }
}
```

## 📝 Logs

View activity:
```bash
tail -f job-monitor.log
```

View alerts:
```bash
cat job-alerts.log
```

## 🔧 Troubleshooting

### No jobs found
- Check if keywords are too specific
- Verify sources are enabled in config
- Look at `job-monitor.log` for errors

### Too many notifications
- Increase `minMatchScore` in notifications config
- Add more `excludeKeywords`
- Reduce `maxPerHour` rate limit

### Rate limiting errors
- Increase `delayBetweenRequestsMs`
- Reduce `maxJobsPerCheck`
- Run less frequently (increase `checkIntervalHours`)

## 🎯 Future Enhancements

- [ ] Email notifications with nodemailer
- [ ] More job sources (Indeed, Glassdoor)
- [ ] Resume matching with NLP
- [ ] Auto-apply preparation
- [ ] Interview question suggestions
- [ ] Salary trend analysis

## 📝 License

MIT
