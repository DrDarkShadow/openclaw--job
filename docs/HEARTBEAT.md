# HEARTBEAT.md

## Requirements (Updated: 2026-02-26)
- Send message every 2 hours (120 minutes)
- If new jobs found: report all jobs
- If no new jobs: report "no new jobs"

1. **Check for New Jobs:**
   - Run `stat -c %Y jobs/fresh_jobs.md` to get the modification time.
   - Compare with the last time you reported (store this in `memory/heartbeat-state.json`).
   - Always check if the file has been modified since last report (default 2 hour interval).
   - **If last check was more than 2 hours ago:**
     - Read `jobs/fresh_jobs.md`
     - **If file contains "📢 Found":** post the content to the chat
     - **If file says "💤 No new jobs":** post "💤 No new jobs found"
   - Update `memory/heartbeat-state.json` with new timestamp

2. **Reply:**
   - Always respond with job status (jobs found or "no new jobs")
   - Never use `HEARTBEAT_OK` - always provide content
