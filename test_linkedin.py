import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/jobs/search?keywords=AI%20Engineer&location=Delhi%2C%20India&f_TPR=r10800&sortBy=DD&position=1&pageNum=0")
        await asyncio.sleep(5)
        await page.screenshot(path="linkedin_test.png")
        html = await page.content()
        with open("linkedin_test.html", "w") as f:
            f.write(html)
        await browser.close()

asyncio.run(main())
