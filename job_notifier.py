#!/usr/bin/env python3
"""
Job Finder - Native OpenClaw Integration
Direct job notifications using OpenClaw's internal messaging system
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_notifier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
WORKSPACE_DIR = Path('/home/ubuntu/.openclaw/workspace')
JOBS_DIR = WORKSPACE_DIR / 'jobs'
FRESH_JOBS_FILE = JOBS_DIR / 'fresh_jobs.md'
SEEN_DB = JOBS_DIR / 'seen_jobs.db'
CONFIG_FILE = JOBS_DIR / 'config.json'
MESSAGE_FILE = JOBS_DIR / 'job_notifications.md'

# Telegram chat ID
TELEGRAM_CHAT_ID = "1304657802"

class JobNotifier:
    """Native job notifier that integrates with OpenClaw messaging"""
    
    def __init__(self):
        self.config = self.load_config()
        self.last_check_file = JOBS_DIR / 'last_notification.txt'
        
    def load_config(self):
        """Load job configuration"""
        config = {
            'keywords': ['software engineer', 'data scientist', 'machine learning'],
            'locations': ['Remote', 'Bangalore', 'Gurugram', 'Pune'],
            'min_salary': 1500000,
            'check_interval_hours': 2
        }
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    # Merge configs
                    if 'search' in user_config:
                        config.update({
                            'keywords': user_config['search'].get('keywords', config['keywords']),
                            'locations': user_config['search'].get('locations', config['locations'])
                        })
                    if 'filters' in user_config:
                        config.update({
                            'min_salary': user_config['filters'].get('minSalary', config['min_salary'])
                        })
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        
        return config
    
    def should_run_check(self):
        """Check if enough time has passed since last check"""
        if not self.last_check_file.exists():
            return True
        
        try:
            with open(self.last_check_file, 'r') as f:
                last_time = float(f.read().strip())
            
            interval_hours = self.config.get('check_interval_hours', 2)
            time_since_last = (time.time() - last_time) / 3600
            
            return time_since_last >= interval_hours
            
        except Exception as e:
            logger.warning(f"Error reading last check time: {e}")
            return True
    
    def update_last_check_time(self):
        """Update last check timestamp"""
        try:
            with open(self.last_check_file, 'w') as f:
                f.write(str(time.time()))
        except Exception as e:
            logger.error(f"Failed to update last check time: {e}")
    
    def read_fresh_jobs(self):
        """Read fresh jobs from markdown file"""
        if not FRESH_JOBS_FILE.exists():
            logger.warning(f"Fresh jobs file not found: {FRESH_JOBS_FILE}")
            return []
        
        try:
            with open(FRESH_JOBS_FILE, 'r') as f:
                content = f.read().strip()
            
            # If file is empty or has no jobs
            if not content or "📢 Found" not in content:
                return []
            
            # Parse jobs from markdown
            jobs = []
            lines = content.split('\n')
            
            current_job = {}
            in_job = False
            
            for line in lines:
                line = line.strip()
                
                # Start of job block
                if line.startswith('🔥'):
                    if current_job:
                        jobs.append(current_job)
                    current_job = {}
                    in_job = True
                    
                    # Extract title
                    title = line.split('🔥')[1].strip()
                    current_job['title'] = title
                
                # Job details
                elif in_job:
                    if line.startswith('🏢'):
                        current_job['company'] = line.split('🏢')[1].strip()
                    elif line.startswith('📍'):
                        current_job['location'] = line.split('📍')[1].strip()
                    elif line.startswith('⏳'):
                        current_job['time_ago'] = line.split('⏳')[1].strip()
                    elif line.startswith('🔗'):
                        current_job['url'] = line.split('🔗')[1].strip()
                    elif line.startswith('🔥') or line.startswith('📢'):
                        # End of current job
                        jobs.append(current_job)
                        current_job = {}
                        # Start new job if line starts with 🔥
                        if line.startswith('🔥'):
                            title = line.split('🔥')[1].strip()
                            current_job['title'] = title
                            in_job = True
            
            # Add last job
            if current_job:
                jobs.append(current_job)
            
            logger.info(f"Parsed {len(jobs)} jobs from {FRESH_JOBS_FILE}")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to parse fresh jobs: {e}")
            return []
    
    def filter_jobs_by_preferences(self, jobs):
        """Filter jobs based on user preferences"""
        if not jobs:
            return []
        
        filtered_jobs = []
        keywords = self.config.get('keywords', [])
        locations = self.config.get('locations', [])
        
        for job in jobs:
            # Check title against keywords
            title_match = False
            job_title = job.get('title', '').lower()
            
            for keyword in keywords:
                if keyword.lower() in job_title:
                    title_match = True
                    break
            
            # Check location
            location_match = False
            job_location = job.get('location', '').lower()
            
            for location in locations:
                if location.lower() in job_location:
                    location_match = True
                    break
            
            # Keep job if matches either title or location
            if title_match or location_match:
                filtered_jobs.append(job)
        
        logger.info(f"Filtered to {len(filtered_jobs)} jobs matching preferences")
        return filtered_jobs
    
    def format_telegram_message(self, jobs):
        """Format jobs for Telegram message"""
        if not jobs:
            return "🎯 No new job matches found this time. Next check in 2 hours."
        
        message = f"🎯 *{len(jobs)} NEW JOB MATCHES FOUND!*\n"
        message += f"_Scanned at {datetime.now().strftime('%H:%M IST')}_\n\n"
        
        # Limit to top 5 jobs to avoid message length issues
        jobs_to_send = jobs[:5]
        
        for i, job in enumerate(jobs_to_send):
            message += f"*{i+1}. {job['title']}*\n"
            
            if job.get('company'):
                message += f"🏢 {job['company']}\n"
            if job.get('location'):
                message += f"📍 {job['location']}\n"
            if job.get('time_ago'):
                message += f"⏰ {job['time_ago']}\n"
            if job.get('url'):
                message += f"🔗 [Apply Here]({job['url']})\n"
            
            message += "\n"
        
        if len(jobs) > 5:
            message += f"📋 _{len(jobs) - 5} more jobs not shown_\n"
        
        message += "💡 *Next automatic check in 2 hours*"
        return message
    
    def send_to_openclaw_session(self, message):
        """Send notification using OpenClaw's internal session mechanism"""
        try:
            # Create a notification file that heartbeat will pick up
            notification_file = MESSAGE_FILE
            
            with open(notification_file, 'w') as f:
                f.write("# JOB NOTIFICATION\n\n")
                f.write(message + "\n")
                f.write("\n---\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            logger.info(f"Notification written to {notification_file}")
            
            # Also trigger a direct message if heartbeat file exists
            heartbeat_file = WORKSPACE_DIR / 'HEARTBEAT.md'
            if heartbeat_file.exists():
                # The heartbeat system will pick this up
                logger.info("Heartbeat system will deliver notification")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def run_job_search(self):
        """Run the job scraping system"""
        try:
            logger.info("Running job search system...")
            
            # Check what scraping methods are available
            scraper_files = ['scraper.js', 'hunter.py', 'live_monitor.py']
            
            for file in scraper_files:
                if (JOBS_DIR / file).exists():
                    logger.info(f"Found scraper: {file}")
                    # The file exists, scraping will run from cron
                    return True
            
            # If no scraper found, create a simple one
            logger.warning("No existing scraper found, using mock data")
            return False
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return False
    
    def run(self):
        """Main execution"""
        logger.info("🔍 Job Notifier starting...")
        
        # Check if we should run
        if not self.should_run_check():
            logger.info("Not enough time since last check, skipping")
            return
        
        logger.info("Checking for fresh jobs...")
        
        # Update last check time first
        self.update_last_check_time()
        
        # Read fresh jobs
        jobs = self.read_fresh_jobs()
        
        if not jobs:
            logger.info("No fresh jobs found")
            message = "🎯 Scan completed - No new jobs found in last 2 hours."
        else:
            # Filter by preferences
            filtered_jobs = self.filter_jobs_by_preferences(jobs)
            
            if filtered_jobs:
                # Format and send message
                telegram_message = self.format_telegram_message(filtered_jobs)
                success = self.send_to_openclaw_session(telegram_message)
                
                if success:
                    logger.info(f"✅ Successfully notified about {len(filtered_jobs)} jobs")
                else:
                    logger.error("Failed to send notification")
                
                # Also write to fresh jobs summary
                self.write_job_summary(filtered_jobs)
                
                message = telegram_message
            else:
                message = f"🎯 Found {len(jobs)} jobs but none matched your preferences. Next check in 2 hours."
                logger.info(message)
        
        # Update heartbeat state if needed
        self.update_heartbeat_state()
        
        logger.info("Job Notifier completed")
        return message
    
    def write_job_summary(self, jobs):
        """Write filtered jobs summary"""
        try:
            summary_file = JOBS_DIR / 'filtered_jobs_summary.md'
            
            with open(summary_file, 'w') as f:
                f.write(f"# Filtered Job Matches - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Total Matches:** {len(jobs)}\n\n")
                
                for i, job in enumerate(jobs, 1):
                    f.write(f"## {i}. {job['title']}\n")
                    if job.get('company'):
                        f.write(f"- **Company:** {job['company']}\n")
                    if job.get('location'):
                        f.write(f"- **Location:** {job['location']}\n")
                    if job.get('time_ago'):
                        f.write(f"- **Posted:** {job['time_ago']}\n")
                    if job.get('url'):
                        f.write(f"- **Apply:** {job['url']}\n")
                    f.write("\n")
            
            logger.info(f"Job summary written to {summary_file}")
            
        except Exception as e:
            logger.error(f"Failed to write job summary: {e}")
    
    def update_heartbeat_state(self):
        """Update heartbeat state file"""
        try:
            state_file = WORKSPACE_DIR / 'memory' / 'heartbeat-state.json'
            state_dir = state_file.parent
            
            # Create directory if needed
            if not state_dir.exists():
                state_dir.mkdir(parents=True, exist_ok=True)
            
            # Load or create state
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
            else:
                state = {"lastChecks": {}}
            
            # Update job notifier state
            state["lastChecks"]["job_notifier"] = {
                "timestamp": int(time.time()),
                "date": datetime.now().isoformat()
            }
            
            # Write back
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Updated heartbeat state: {state_file}")
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat state: {e}")

def main():
    """Main function"""
    notifier = JobNotifier()
    result = notifier.run()
    
    # Print result for cron logging
    if result:
        print(result)

if __name__ == "__main__":
    # Make file executable
    os.chmod(__file__, 0o755)
    
    # Run
    main()