#!/usr/bin/env python3
"""
Telegram Auto-Pusher - Sends fresh jobs to Telegram every 2 hours
Direct notification without waiting for heartbeat
"""

import os
import sys
import json
import sqlite3
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_notifier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
WORKSPACE_DIR = Path('/home/ubuntu/.openclaw/workspace')
JOBS_DIR = WORKSPACE_DIR / 'jobs'
FRESH_JOBS_FILE = JOBS_DIR / 'fresh_jobs.md'
SEEN_DB = JOBS_DIR / 'seen_jobs.db'
MEMORY_FILE = WORKSPACE_DIR / 'memory/heartbeat-state.json'
TELEGRAM_CONFIG = JOBS_DIR / 'telegram_config.json'

# Telegram API setup (using OpenClaw's internal API)
TELEGRAM_CHAT_ID = "1304657802"  # Your Telegram chat ID
OPENCLAW_API_URL = "http://localhost:3010"  # OpenClaw gateway (adjust if needed)

class TelegramJobNotifier:
    """Sends job notifications directly to Telegram"""
    
    def __init__(self):
        self.session = None
        self.last_processed_times = {}
        self.load_config()
        
    def load_config(self):
        """Load configuration"""
        config_paths = [
            WORKSPACE_DIR / '.openclaw' / 'config.json',
            Path('/etc/openclaw/config.json'),
            Path.home() / '.openclaw' / 'config.json'
        ]
        
        self.config = {}
        for path in config_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        self.config.update(json.load(f))
                        logger.info(f"Loaded config from {path}")
                        break
                except Exception as e:
                    logger.warning(f"Failed to load config from {path}: {e}")
    
    async def send_to_telegram(self, message: str) -> bool:
        """
        Send message to Telegram via OpenClaw's internal API
        Uses session_send to post directly to chat
        """
        try:
            # Method 1: Use http request to OpenClaw gateway
            url = f"{OPENCLAW_API_URL}/api/v1/sessions/send"
            payload = {
                "sessionKey": f"telegram:{TELEGRAM_CHAT_ID}",
                "message": message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Message sent to Telegram")
                        return True
                    else:
                        logger.error(f"Failed to send: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            # Fallback: Write to file for OpenClaw to pick up
            self.write_to_file(message)
            return False
    
    def write_to_file(self, message: str):
        """Fallback: Write to file for heartbeat pickup"""
        notification_file = JOBS_DIR / 'telegram_ready.md'
        try:
            with open(notification_file, 'w') as f:
                f.write(f"📢 TELEGRAM NOTIFICATION READY\n\n{message}\n")
            logger.info(f"Written to {notification_file}")
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
    
    def read_fresh_jobs(self) -> list:
        """Read and parse fresh jobs from markdown file"""
        if not FRESH_JOBS_FILE.exists():
            logger.warning(f"No fresh jobs file: {FRESH_JOBS_FILE}")
            return []
        
        try:
            with open(FRESH_JOBS_FILE, 'r') as f:
                content = f.read()
            
            # Check if file actually has "Found" header
            if "📢 Found" not in content:
                logger.info("No fresh jobs found in file")
                return []
            
            # Parse jobs
            jobs = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if '🔥' in line:
                    # Parse job entry
                    job = {'title': '', 'company': '', 'location': '', 'url': '', 'time_ago': ''}
                    
                    # Title line
                    title_text = line.split('🔥')[1].strip()
                    job['title'] = title_text.split('\n')[0].strip()
                    
                    # Parse following lines
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if '🏢' in next_line:
                            job['company'] = next_line.split('🏢')[1].strip()
                        elif '📍' in next_line:
                            job['location'] = next_line.split('📍')[1].strip()
                        elif '⏳' in next_line:
                            job['time_ago'] = next_line.split('⏳')[1].strip()
                        elif '🔗' in next_line:
                            job['url'] = next_line.split('🔗')[1].strip()
                        elif '🔥' in next_line or '📢' in next_line:
                            break
                    
                    jobs.append(job)
            
            logger.info(f"Parsed {len(jobs)} jobs from {FRESH_JOBS_FILE}")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to parse fresh jobs: {e}")
            return []
    
    def format_telegram_message(self, jobs: list) -> str:
        """Format jobs for Telegram message"""
        if not jobs:
            return "No fresh jobs found in the last 2 hours."
        
        message = f"🎯 *{len(jobs)} FRESH JOBS FOUND!* \n"
        message += f"_Scanned at {datetime.now().strftime('%H:%M IST')}_\n\n"
        
        for i, job in enumerate(jobs[:7]):  # Max 7 jobs to avoid message length limits
            message += f"*{i+1}. {job['title']}*\n"
            message += f"🏢 {job.get('company', 'N/A')}\n"
            message += f"📍 {job.get('location', 'N/A')}\n"
            message += f"⏰ {job.get('time_ago', 'Recently')}\n"
            if job.get('url'):
                message += f"🔗 [Apply Here]({job['url']})\n"
            message += "\n"
        
        message += "\n💡 *Next check in 2 hours*"
        message += "\n❌ Stale jobs auto-filtered"
        
        return message
    
    def check_freshness(self, jobs: list) -> list:
        """Filter only fresh jobs (less than 24 hours old)"""
        fresh_jobs = []
        now = datetime.now()
        
        for job in jobs:
            time_text = job.get('time_ago', '')
            
            # Parse time ago
            hours_ago = 0
            if 'minute' in time_text:
                hours_ago = 0
            elif 'hour' in time_text:
                try:
                    hours_ago = int(time_text.split('hour')[0].strip())
                except:
                    hours_ago = 24
            else:
                hours_ago = 24  # Default if can't parse
            
            # Keep only jobs < 24 hours old
            if hours_ago < 24:
                fresh_jobs.append(job)
        
        logger.info(f"Filtered to {len(fresh_jobs)} fresh jobs (<24 hours)")
        return fresh_jobs
    
    async def run(self):
        """Main function to check and send jobs"""
        logger.info("⚡ Telegram Job Notifier starting...")
        
        # Read fresh jobs
        jobs = self.read_fresh_jobs()
        
        if not jobs:
            logger.info("No jobs to send")
            return
        
        # Filter for freshness
        fresh_jobs = self.check_freshness(jobs)
        
        if not fresh_jobs:
            logger.info("No fresh jobs to send")
            return
        
        # Format message
        message = self.format_telegram_message(fresh_jobs)
        
        # Send to Telegram
        logger.info(f"Sending {len(fresh_jobs)} jobs to Telegram")
        success = await self.send_to_telegram(message)
        
        if success:
            logger.info(f"✅ Successfully sent {len(fresh_jobs)} jobs to Telegram")
            
            # Update last processed time
            self.update_last_processed()
        else:
            logger.warning("Failed to send to Telegram, using fallback")
    
    def update_last_processed(self):
        """Update last processed timestamp"""
        timestamp = int(datetime.now().timestamp())
        
        try:
            state_path = MEMORY_FILE
            if state_path.exists():
                with open(state_path, 'r') as f:
                    state = json.load(f)
            else:
                state = {"lastChecks": {}}
            
            state["lastChecks"]["telegram_notify"] = timestamp
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Updated last_processed time: {timestamp}")
            
        except Exception as e:
            logger.error(f"Failed to update state: {e}")

async def main():
    """Main async entry point"""
    notifier = TelegramJobNotifier()
    await notifier.run()

if __name__ == "__main__":
    # Make file executable
    os.chmod(__file__, 0o755)
    
    # Run async main
    asyncio.run(main())
    
    logger.info("Telegram notifier completed")