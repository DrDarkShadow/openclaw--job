import asyncio
import json
import urllib.parse
from playwright.async_api import async_playwright

async def scrape_linkedin_public(page, keywords, location):
    print(f"   🔎 Scanning for '{keywords}' in '{location}'...")
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": "r604800", # Past week (fresh jobs)
        "position": 1,
        "pageNum": 0
    }
    url = f"https://www.linkedin.com/jobs/search?{urllib.parse.urlencode(params)}"
    
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(3) # Let skeleton loader finish
        
        # Scroll to load more
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        
        # Public LinkedIn usually uses 'base-card' for job listings
        cards = page.locator("li .base-card")
        count = await cards.count()
        
        jobs = []
        for i in range(min(count, 5)): # Take top 5 per search query
            card = cards.nth(i)
            try:
                title_loc = card.locator(".base-search-card__title")
                company_loc = card.locator(".base-search-card__subtitle")
                link_loc = card.locator("a.base-card__full-link")
                
                if await title_loc.count() > 0:
                    title = await title_loc.inner_text()
                    company = await company_loc.inner_text()
                    link = await link_loc.get_attribute("href")
                    
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": location,
                        # Keep full link including query params for tracking/redirects
                        "link": link if link else "#"
                    })
            except:
                continue
                
        return jobs
    except Exception as e:
        print(f"   ⚠️ Error searching {keywords}: {e}")
        return []

async def run():
    # User Preferences
    searches = [
        ("AI Engineer", "Noida, Uttar Pradesh, India"),
        ("Machine Learning Engineer", "Remote"),
        ("Generative AI", "Gurugram, Haryana, India"),
        ("Python Developer", "Noida, Uttar Pradesh, India")
    ]

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("🕵️  Hunter Bot Initialized. Scanning public boards...")
        
        for kw, loc in searches:
            found = await scrape_linkedin_public(page, kw, loc)
            results.extend(found)
            await asyncio.sleep(2) # Be polite

        await browser.close()

    # Deduplicate by link
    seen = set()
    unique_results = []
    for job in results:
        if job['link'] not in seen and job['link'] != "#":
            seen.add(job['link'])
            unique_results.append(job)

    print(f"\n✅ Found {len(unique_results)} unique jobs.")
    
    # Save to file
    with open('jobs/hunter_results.json', 'w') as f:
        json.dump(unique_results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run())
