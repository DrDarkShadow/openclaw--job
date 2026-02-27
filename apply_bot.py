import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run():
    with open('jobs/config.json') as f:
        config = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata" # Match user location
        )

        # Load cookies
        try:
            with open('jobs/cookies.json') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
        except FileNotFoundError:
            print("⚠️ cookies.json not found! Please provide the li_at cookie.")
            return

        page = await context.new_page()
        
        # Go to LinkedIn Feed
        try:
            await page.goto("https://www.linkedin.com/feed/", timeout=60000)
        except Exception as e:
            print(f"⚠️ Error going to feed: {e}")

        await asyncio.sleep(5)
        
        print(f"🌍 Current URL: {page.url}")
        await page.screenshot(path="/home/ubuntu/.openclaw/workspace/jobs/debug_screenshot.png")
        
        # Check login status
        if "login" in page.url or "signup" in page.url or "guest" in page.url:
            print("❌ Redirected to Login/Signup page! Cookie might be invalid or expired.")
            return

        print("✅ Logged in! Navigating to jobs...")
        await page.goto("https://www.linkedin.com/jobs/")
        await asyncio.sleep(5)

        # Search for jobs
        keywords = config['job_preferences']['titles'][0] # Start with first title
        location = config['job_preferences']['locations'][0]
        
        print(f"🔎 Searching for {keywords} in {location}...")
        
        # Fill search box
        await page.get_by_placeholder("Search jobs").fill(keywords)
        await page.get_by_placeholder("Search location").fill(location)
        await page.keyboard.press("Enter")
        
        await asyncio.sleep(5)

        # Filter for "Easy Apply" if configured
        if config['linkedin']['easy_apply_only']:
            try:
                await page.get_by_label("Easy Apply filter").click()
                await asyncio.sleep(3)
            except:
                print("⚠️ Could not click Easy Apply filter")

        # Iterate through job cards
        job_cards = await page.locator(".job-card-container").all()
        print(f"Found {len(job_cards)} potential jobs.")

        for card in job_cards[:5]: # Try first 5
            await card.click()
            await asyncio.sleep(2)
            
            title = await page.locator(".job-details-jobs-unified-top-card__job-title").first.inner_text()
            print(f"👉 Checking: {title}")
            
            # Click Easy Apply button
            apply_btn = page.locator("button.jobs-apply-button")
            if await apply_btn.is_visible():
                await apply_btn.click()
                print("   🚀 Clicked Easy Apply!")
                # Here we would add the form filling logic
                # For now, we pause to observe
                await asyncio.sleep(5)
                # Close modal to continue
                await page.keyboard.press("Escape")
            else:
                print("   ❌ Already applied or not Easy Apply")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
