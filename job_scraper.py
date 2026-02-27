#!/usr/bin/env python3
"""
Simple Job Scraper for Job Notifier System
Creates fresh jobs data for testing and demonstration
"""

import os
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
JOBS_DIR = Path('/home/ubuntu/.openclaw/workspace/jobs')
FRESH_JOBS_FILE = JOBS_DIR / 'fresh_jobs.md'
SEEN_JOBS_FILE = JOBS_DIR / 'seen_jobs.json'
LAST_SCRAPE_FILE = JOBS_DIR / 'last_scrape.timestamp'

# Sample job data
SAMPLE_JOBS = [
    {
        "title": "Software Engineer",
        "company": "TechCorp Inc.",
        "location": "Bangalore, Karnataka, India",
        "url": "https://in.linkedin.com/jobs/view/software-engineer-at-techcorp-1234567890",
        "keywords": ["software", "engineer", "javascript"]
    },
    {
        "title": "Data Scientist",
        "company": "DataAnalytics Co.",
        "location": "Remote",
        "url": "https://in.linkedin.com/jobs/view/data-scientist-at-dataanalytics-2345678901",
        "keywords": ["data", "scientist", "machine learning", "python"]
    },
    {
        "title": "Full Stack Developer",
        "company": "WebSolutions Ltd.",
        "location": "Gurugram, Haryana, India",
        "url": "https://in.linkedin.com/jobs/view/full-stack-developer-at-websolutions-3456789012",
        "keywords": ["full stack", "developer", "react", "node.js"]
    },
    {
        "title": "Machine Learning Engineer",
        "company": "AI Innovations",
        "location": "Pune, Maharashtra, India",
        "url": "https://in.linkedin.com/jobs/view/machine-learning-engineer-at-ai-innovations-4567890123",
        "keywords": ["machine learning", "ml", "deep learning", "python"]
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudSystems",
        "location": "Hyderabad, Telangana, India",
        "url": "https://in.linkedin.com/jobs/view/devops-engineer-at-cloudsystems-5678901234",
        "keywords": ["devops", "aws", "kubernetes", "docker"]
    },
    {
        "title": "Product Manager",
        "company": "ProductLabs",
        "location": "Remote",
        "url": "https://in.linkedin.com/jobs/view/product-manager-at-productlabs-6789012345",
        "keywords": ["product", "manager", "strategy", "agile"]
    }
]

class JobScraper:
    """Simple job scraper that simulates finding new jobs"""
    
    def __init__(self):
        self.seen_jobs = self.load_seen_jobs()
        self.fresh_jobs = []
        
    def load_seen_jobs(self):
        """Load list of already seen job IDs"""
        if SEEN_JOBS_FILE.exists():
            try:
                with open(SEEN_JOBS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load seen jobs: {e}")
        
        return []
    
    def save_seen_jobs(self):
        """Save seen jobs list"""
        try:
            with open(SEEN_JOBS_FILE, 'w') as f:
                json.dump(self.seen_jobs, f, indent=2)
            logger.info(f"Saved {len(self.seen_jobs)} seen jobs")
        except Exception as e:
            logger.error(f"Failed to save seen jobs: {e}")
    
    def generate_job_id(self, job):
        """Generate a unique ID for a job"""
        # Use URL slug for ID if available
        if job.get('url'):
            # Extract job ID from URL
            url_parts = job['url'].split('/')
            for part in reversed(url_parts):
                if part.isdigit():
                    return f"linkedin_{part}"
        
        # Fallback: hash of title + company
        import hashlib
        job_str = f"{job['title']}_{job['company']}".encode('utf-8')
        return hashlib.md5(job_str).hexdigest()[:12]
    
    def scrape_jobs(self):
        """Simulate scraping new jobs"""
        logger.info("🕸️ Scraping for new jobs...")
        
        # Simulate network delay
        import random
        time.sleep(random.uniform(1.0, 3.0))
        
        new_jobs = []
        
        # Randomly select 0-3 new jobs each time
        num_new_jobs = random.randint(0, min(3, len(SAMPLE_JOBS)))
        available_jobs = SAMPLE_JOBS.copy()
        random.shuffle(available_jobs)
        
        for i in range(num_new_jobs):
            job = available_jobs[i].copy()
            
            # Generate ID and check if seen
            job_id = self.generate_job_id(job)
            
            if job_id not in self.seen_jobs:
                # Add time ago
                time_ago_options = ["1 minute", "15 minutes", "30 minutes", "1 hour", "2 hours"]
                job['time_ago'] = random.choice(time_ago_options)
                
                new_jobs.append(job)
                self.seen_jobs.append(job_id)
        
        self.fresh_jobs = new_jobs
        logger.info(f"Found {len(new_jobs)} new jobs")
        
        # Save seen jobs
        self.save_seen_jobs()
        
        return new_jobs
    
    def write_fresh_jobs_md(self, jobs):
        """Write fresh jobs to markdown file"""
        if not jobs:
            content = "💤 No new jobs found in the last 2 hours.\n"
        else:
            content = f"📢 Found {len(jobs)} fresh matches:\n\n"
            
            for job in jobs:
                content += f"🔥 **{job['title']}**\n"
                content += f"   🏢 {job['company']}\n"
                content += f"   📍 {job['location']}\n"
                content += f"   ⏳ {job.get('time_ago', 'Recently')} ago\n"
                content += f"   🔗 {job['url']}\n\n"
        
        try:
            with open(FRESH_JOBS_FILE, 'w') as f:
                f.write(content)
            
            logger.info(f"Wrote to {FRESH_JOBS_FILE}")
            
            # Update last scrape timestamp
            with open(LAST_SCRAPE_FILE, 'w') as f:
                f.write(str(int(time.time())))
            
        except Exception as e:
            logger.error(f"Failed to write fresh jobs: {e}")
    
    def run(self):
        """Main execution"""
        logger.info("🚀 Starting job scraper...")
        
        # Check if we need to scrape (every 2 hours)
        should_scrape = False
        
        if LAST_SCRAPE_FILE.exists():
            try:
                with open(LAST_SCRAPE_FILE, 'r') as f:
                    last_time = int(f.read().strip())
                
                # Scrape if more than 2 hours have passed
                if (time.time() - last_time) > (2 * 3600):
                    should_scrape = True
            except Exception as e:
                logger.warning(f"Error reading last scrape time: {e}")
                should_scrape = True
        else:
            should_scrape = True
        
        if not should_scrape:
            logger.info("Less than 2 hours since last scrape, skipping")
            return
        
        # Scrape jobs
        new_jobs = self.scrape_jobs()
        
        # Write to file
        self.write_fresh_jobs_md(new_jobs)
        
        # Log results
        if new_jobs:
            logger.info(f"✅ Successfully found {len(new_jobs)} new jobs")
        else:
            logger.info("ℹ️ No new jobs found this time")

def main():
    """Main function"""
    scraper = JobScraper()
    scraper.run()

if __name__ == "__main__":
    # Make file executable
    os.chmod(__file__, 0o755)
    
    # Run
    main()