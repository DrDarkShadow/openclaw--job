import asyncio
from playwright.async_api import async_playwright
import json
import os

EMAIL = "gummyreaker@gmail.com"
PASSWORD = "Shadowgunner@linkedin123"

async def login():
    async with async_playwright() as p:
        # Launch browser with stealth args
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
                '--disable-blink-features=AutomationControlled', # Key for stealth
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata"
        )
        
        # Add init script to hide webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        page = await context.new_page()

        print(f"🔑 Navigating to Login Page for {EMAIL}...")
        await page.goto("https://www.linkedin.com/login")
        
        # Fill credentials
        await page.fill("#username", EMAIL)
        await page.fill("#password", PASSWORD)
        print("⌨️  Credentials entered. Clicking Sign In...")
        await page.click("button[type='submit']")
        
        await asyncio.sleep(5)
        
        # Check where we are
        url = page.url
        print(f"🌍 Current URL: {url}")
        
        if "feed" in url:
            print("✅ Login Success! Saving cookies...")
            cookies = await context.cookies()
            with open("jobs/cookies.json", "w") as f:
                json.dump(cookies, f)
            print("💾 Cookies saved to jobs/cookies.json")
            
        elif "challenge" in url or "checkpoint" in url:
            print("⚠️ SECURITY CHALLENGE DETECTED!")
            print("Please check your email/phone for a verification code.")
            
            # Take a screenshot to confirm what kind of challenge
            await page.screenshot(path="jobs/challenge.png")
            
            # Wait for user input (simulated here by checking for a file)
            print("⏳ Waiting for code... (I will ask the user)")
            # In a real script we'd pause here, but for this agent flow, we'll exit and ask the user
            return "CHALLENGE_REQUIRED"
            
        else:
            print("❓ Unknown state. Taking screenshot.")
            await page.screenshot(path="jobs/unknown_state.png")
            content = await page.content()
            if "Wrong email" in content or "password" in content:
                print("❌ Invalid credentials reported by page.")
            
        await browser.close()

if __name__ == "__main__":
    import sys
    result = asyncio.run(login())
    if result == "CHALLENGE_REQUIRED":
        print("OUTPUT: CHALLENGE_REQUIRED")
