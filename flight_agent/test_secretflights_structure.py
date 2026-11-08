import asyncio
from playwright.async_api import async_playwright
import re
import json

async def inspect_secretflights_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        url = "https://secretflights.co.il/flights-to-athens/"
        print(f"Loading {url}...")
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Get full HTML text and search for flight sections
        html = await page.content()
        with open("secretflights_athens.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved HTML to secretflights_athens.html. Total length:", len(html))

        # Look for flight deals text
        body_text = await page.inner_text("body")
        lines = [line.strip() for line in body_text.split("\n") if line.strip()]
        
        deals_found = []
        for i, line in enumerate(lines):
            if "$" in line or "₪" in line:
                surrounding = " | ".join(lines[max(0, i-2):min(len(lines), i+3)])
                if any(k in surrounding for k in ["TLV", "נתב״ג", "טיסה", "הלוך", "ישיר", "2026"]):
                    deals_found.append(surrounding)

        print(f"Total deal snippets found: {len(deals_found)}")
        for d in deals_found[:8]:
            print("Deal:", d)

        await browser.close()

asyncio.run(inspect_secretflights_structure())
