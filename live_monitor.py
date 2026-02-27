import asyncio
import json
import urllib.parse
import os
import sqlite3
import datetime
import re
import smtplib
import os
import json
from email.message import EmailMessage
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Chat Profile (AI/ML Focused)
CHAT_KEYWORDS_QUERY = "(AI Engineer OR Machine Learning OR Deep Learning OR Computer Vision OR Generative AI OR GenAI OR LLM OR RAG OR GAN)"
CHAT_REQUIRED_KEYWORDS = [
    "AI", "Artificial Intelligence", "Machine Learning", "Deep Learning", "Computer Vision", 
    "NLP", "Natural Language", "Generative", "GenAI", "LLM", "RAG", "GAN", 
    "Data Scientist", "Neural", "Mlops", "ML Engineer", "MLOps", "Generative AI", "AI Engineer"
]

# 2. Email Profile (SDE + DevOps + Cloud + Data)
EMAIL_KEYWORDS_QUERY = "(Software Engineer OR Software Developer OR SDE OR Backend Engineer OR Backend Developer OR Node.js Developer OR Python Backend Developer OR API Developer OR Distributed Systems Engineer OR Systems Engineer OR Platform Engineer OR Infrastructure Engineer OR Microservices Engineer OR Full Stack Engineer OR Full Stack Developer OR Web Developer OR Frontend Engineer OR Frontend Developer OR React Developer OR Next.js Developer OR JavaScript Developer OR TypeScript Developer OR Application Developer OR Product Engineer OR Cloud Engineer OR DevOps Engineer OR Site Reliability Engineer OR Data Platform Engineer OR Data Engineer)"

# Locations (Shared)
LOCATIONS = [
    "Noida, Uttar Pradesh, India",
    "Gurugram, Haryana, India",
    "Delhi, India",
    "Pune, Maharashtra, India",
    "Bengaluru, Karnataka, India"
]

TIME_WINDOW_SECONDS = "r10800" 
DB_FILE = os.path.join(BASE_DIR, "seen_jobs.db")

BLACKLIST_COMPANIES = ["Mindrift", "Accenture", "Crossover", "Turing", "Outlier", "Canonical"]
BLACKLIST_TITLES = [
    "Senior", "Sr.", "Sr", "Lead", "Principal", "Staff", "Manager", "Head", "Director", "Architect", "VP", "Chief", "AVP", "Intern",
    "3+", "4+", "5+", "6+", "7+", "8+", "9+", "10+", "III", "IV",
    "Rail", "Civil", "Medical", "Business Associate", "Mechatronics", "Robotics", "Tenure", "University", "Academic", "Casting", "Construction", "Pharmacist", "Doctor",
    "Sales", "Marketing", "Recruiter", "HR", "Account Executive", "Consultant", "Cofounder"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (link TEXT PRIMARY KEY, title TEXT, company TEXT, posted_at TIMESTAMP)''')
    conn.commit()
    conn.close()

def is_seen(link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM jobs WHERE link=?", (link,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_seen(link, title, company):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO jobs (link, title, company, posted_at) VALUES (?, ?, ?, ?)", 
                  (link, title, company, datetime.datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def parse_time_ago(text):
    """Returns minutes ago. Returns 999 if unknown."""
    text = text.lower()
    if "just now" in text:
        return 0
    
    match = re.search(r'(\d+)\s+(minute|hour|second)', text)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if "minute" in unit:
            return val
        if "hour" in unit:
            return val * 60
        if "second" in unit:
            return 0
    return 999 # Fallback

def is_blacklisted(title, company, required_keywords=None):
    # Check Company
    for bad_co in BLACKLIST_COMPANIES:
        if bad_co.lower() in company.lower():
            return True
    
    # Check Title for Blacklist
    for bad_title in BLACKLIST_TITLES:
        if re.search(r'\b' + re.escape(bad_title) + r'\b', title, re.IGNORECASE):
            return True
            
    # Strict Relevance Check (If Required Keywords Provided)
    if required_keywords:
        relevant = False
        for k in required_keywords:
            if re.search(r'\b' + re.escape(k) + r'\b', title, re.IGNORECASE):
                relevant = True
                break
        if not relevant:
            return True # Filter out if title is not strictly relevant
            
    return False

def send_email(subject, body):
    try:
        config_path = os.path.join(BASE_DIR, "email_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        
        if not config.get("enabled"):
            print(f"⚠️ Email notifications disabled in {config_path}")
            return

        sender = config["sender_email"]
        password = config["app_password"]
        recipient = config["recipient_email"]

        if not sender or "YOUR_GMAIL" in sender:
            print(f"⚠️ Sender email not configured in {config_path}")
            return

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        
        print(f"📧 Email sent to {recipient}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# ... (init_db, is_seen, mark_seen, parse_time_ago, is_blacklisted functions remain the same) ...

async def scan_feed(page, keywords, location, required_keywords=None):
    print(f"   Scanning {keywords[:40]}... in {location}...")
    
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": TIME_WINDOW_SECONDS,
        "sortBy": "DD",
        "position": 1,
        "pageNum": 0
    }
    url = f"https://www.linkedin.com/jobs/search?{urllib.parse.urlencode(params)}"
    
    found_batch = []

    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(3)
        
        cards = page.locator("li .base-card")
        count = await cards.count()
        print(f"   Found {count} cards on page.")
        
        for i in range(count):
            card = cards.nth(i)
            
            # Extract Time Text first
            time_text_loc = card.locator("time")
            if await time_text_loc.count() > 0:
                time_text = await time_text_loc.inner_text()
                time_text = time_text.strip()
                minutes = parse_time_ago(time_text)
                
                # Extract details
                title_loc = card.locator(".base-search-card__title")
                link_loc = card.locator("a.base-card__full-link")
                comp_loc = card.locator(".base-search-card__subtitle")
                
                link = await link_loc.get_attribute("href")
                if not link: continue
                # Strip query parameters to ensure stable deduplication
                if "?" in link:
                    link = link.split('?')[0]
                
                if is_seen(link):
                    # Skip if already seen
                    continue
                
                title = await title_loc.inner_text()
                company = await comp_loc.inner_text()
                title = title.strip()
                company = company.strip()

                # --- FILTERS ---
                if is_blacklisted(title, company, required_keywords):
                    # print(f"   Blacklisted: {title} @ {company}")
                    continue

                # Add to batch for sorting
                found_batch.append({
                    "minutes": minutes,
                    "time_text": time_text,
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link
                })
                
                # IMPORTANT: Mark seen globally so we don't re-process in subsequent runs/profiles?
                # Actually, for this dual-profile setup, we should probably mark seen AFTER we decide where it goes.
                # However, is_seen() uses the same DB. If we mark it seen for Chat, Email won't see it if we run sequentially.
                # BUT, we want Email to contain EVERYTHING.
                # So we should collect all found jobs first, then mark seen.
                # But scan_feed is called multiple times.
                # To keep it simple: we will mark seen here. If it's seen, it's processed.
                # Wait, if Chat sees it first, Email won't get it if we rely on `scan_feed` return.
                # FIX: We will return the job regardless of seen status IF it was seen *in this run*.
                # But is_seen checks the DB.
                # Solution: We won't mark seen here. We will return candidates.
                # Then in main(), we deduplicate and mark seen.
                
    except Exception as e:
        print(f"Error scanning: {e}")

    return found_batch

async def run_once():
    init_db()
    print("🚀 LinkedIn Dual-Profile Check Triggered")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        chat_jobs = []
        email_jobs = []
        
        # ---------------------------------------------------------
        # PROFILE 1: CHAT (AI ONLY)
        # ---------------------------------------------------------
        print("--- Processing Chat Profile (AI) ---")
        for loc in LOCATIONS:
            # Note: We must call the function with await
            batch = await scan_feed(page, CHAT_KEYWORDS_QUERY, loc, required_keywords=CHAT_REQUIRED_KEYWORDS)
            
            for job in batch:
                # Add to chat list
                chat_jobs.append(job)
                
                # Also add to email list (User wants AI + SDE in email)
                email_jobs.append(job)
                
                # Mark seen immediately to prevent SDE run from picking it up again?
                # Actually, duplicate detection relies on DB.
                mark_seen(job['link'], job['title'], job['company'])
            
            await asyncio.sleep(2)

        # ---------------------------------------------------------
        # PROFILE 2: EMAIL (SDE + DEVOPS + CLOUD)
        # ---------------------------------------------------------
        print("--- Processing Email Profile (SDE) ---")
        for loc in LOCATIONS:
            # No required keywords, strict check disabled for SDE
            batch = await scan_feed(page, EMAIL_KEYWORDS_QUERY, loc, required_keywords=None)
            
            for job in batch:
                # Add to email list regardless of chat status (if new)
                if not is_seen(job['link']):
                    email_jobs.append(job)
                    mark_seen(job['link'], job['title'], job['company'])
            
            await asyncio.sleep(2)
        
        await browser.close()
        
        # --- OUTPUT FOR CHAT ---
        chat_jobs.sort(key=lambda x: x['minutes'])
        output_lines = []
        
        # Always write file, even if empty, to clear old "Found" status if needed
        # But we only want to report if found.
        if chat_jobs:
            output_lines.append(f"\n📢 Found {len(chat_jobs)} fresh matches:")
            for job in chat_jobs:
                icon = "🔥" if job['minutes'] <= 60 else "⏰"
                output_lines.append(f"\n{icon} **{job['title']}**")
                output_lines.append(f"   🏢 {job['company']} ({job['location']})")
                output_lines.append(f"   ⏳ {job['time_text']}")
                output_lines.append(f"   🔗 {job['link']}")
            
            fresh_jobs_path = os.path.join(BASE_DIR, "fresh_jobs.md")
            with open(fresh_jobs_path, "w") as f:
                f.write("\n".join(output_lines))
        else:
            output_lines.append("\n💤 No new jobs found in the last check.")
            # Optional: Clear the file to avoid repeating old news? 
            # The agent checks timestamp.
            # But if I don't write, timestamp stays old.
            # If I write "No new jobs", agent sees "No new jobs".
            fresh_jobs_path = os.path.join(BASE_DIR, "fresh_jobs.md")
            with open(fresh_jobs_path, "w") as f:
                f.write("\n💤 No new jobs found.")

        print("\n".join(output_lines))
        
        # --- OUTPUT FOR EMAIL ---
        if email_jobs:
            # Deduplicate by link just in case
            unique_email_jobs = {j['link']: j for j in email_jobs}.values()
            sorted_email = sorted(unique_email_jobs, key=lambda x: x['minutes'])
            
            email_lines = []
            email_lines.append(f"📢 Found {len(sorted_email)} fresh matches (AI + SDE):")
            for job in sorted_email:
                icon = "🔥" if job['minutes'] <= 60 else "⏰"
                email_lines.append(f"\n{icon} **{job['title']}**")
                email_lines.append(f"   🏢 {job['company']} ({job['location']})")
                email_lines.append(f"   ⏳ {job['time_text']}")
                email_lines.append(f"   🔗 {job['link']}")
            
            email_body = "\n".join(email_lines)
            send_email("🔥 Fresh Job Alerts (AI + SDE)", email_body)
        else:
            print("No new jobs for email.")

if __name__ == "__main__":
    asyncio.run(run_once())
