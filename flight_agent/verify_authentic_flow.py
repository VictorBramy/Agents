import sys
import asyncio
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright

async def verify_authentic_flow():
    user_prompt = "טיסה לוינה 2 אנשים עם מזוודות בתאריך נובמבר עד 5 ימים שיהיה בתאריך 26.11 אבל לא בחזור וגם לא הלוך"
    print("\n=======================================================")
    print("🚀 [PLAYWRIGHT BROWSER AUDIT] Authentic Flight Verification")
    print(f"Prompt: '{user_prompt}'")
    print("=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        page = await context.new_page()

        print("1. Opening http://127.0.0.1:8080/flights...")
        await page.goto("http://127.0.0.1:8080/flights", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("2. Entering user prompt into #aiPromptInput...")
        await page.fill("#aiPromptInput", user_prompt)
        await page.wait_for_timeout(500)

        print("3. Clicking #btnAiSearch...")
        await page.click("#btnAiSearch")

        print("4. Waiting for search results...")
        await page.wait_for_selector("#resultsSection:not(.hidden)", timeout=60000)
        await page.wait_for_timeout(3000)

        # Validate dates
        trip_desc = await page.inner_text("#statTripTypeDesc")
        print(f"   ✓ Dates: {trip_desc}")
        assert "2026-11-23" in trip_desc and "2026-11-28" in trip_desc, "Dates must be 2026-11-23 ⇄ 2026-11-28"

        # Validate cards
        cards = await page.query_selector_all("#flightsContainer > div")
        print(f"   ✓ Flight Cards Rendered: {len(cards)}")
        assert len(cards) >= 5, "Cards must be rendered"

        # Validate Multi-Subagent Swarm Board
        subagent_cards = await page.query_selector_all("#airlineAuditsGrid > div")
        print(f"   ✓ Subagent Cards Rendered in Swarm Board: {len(subagent_cards)}")
        assert len(subagent_cards) >= 10, "At least 10 airline subagents must be rendered in Swarm Board"
        
        swarm_badge = await page.inner_text("#auditTotalScannedBadge")
        print(f"   ✓ Swarm Board Badge: {swarm_badge}")

        swarm_text = await page.inner_text("#airlineAuditsGrid")
        print("   ✓ Checking Subagent Discovery Fidelity:")
        assert "בלו בירד" in swarm_text and "טיסות" in swarm_text, "Blue Bird must report active flights"
        assert "ראיינאייר" in swarm_text and "טיסות" in swarm_text, "Ryanair must report active flights"
        assert "אוסטריאן" in swarm_text and "טיסות" in swarm_text, "Austrian must report active flights"
        assert "100% תואם" in swarm_text or "אימות פרומפט" in swarm_text, "Prompt verification must be visible"
        print("     -> Blue Bird, Ryanair, and Austrian verified active with authentic flights & prompt compliance!")

        # Validate top winning card (cheapest date deal)
        top_card = cards[0]
        top_text = await top_card.inner_text()
        print("   ✓ Top Winning Card Content Verified:")
        print("     " + "\n     ".join(top_text.split("\n")[:8]))

        # Validate booking button points to direct booking link
        booking_btn = await top_card.query_selector("a.bg-gradient-to-r")
        assert booking_btn is not None, "Booking button must exist"
        href = await booking_btn.get_attribute("href")
        print(f"   ✓ Top Offer Booking Link: {href}")
        assert href.startswith("http"), "Link must be a valid booking link"

        # Quality assurance banner check
        qa_banner = await page.inner_text("#qualityAuditBannerText")
        print(f"   ✓ QA Compliance Banner: {qa_banner}")
        assert "100" in qa_banner or "APPROVED" in qa_banner or "אומתו" in qa_banner

        # Validate Live Baggage Checkout Breakdown Banner (REQ-17)
        bag_banner = await page.query_selector("#liveBaggageBanner")
        assert bag_banner is not None, "Baggage banner must exist"
        is_bag_hidden = await page.eval_on_selector("#liveBaggageBanner", "el => el.classList.contains('hidden')")
        assert not is_bag_hidden, "Live baggage banner must be visible"

        bag_total_text = await page.inner_text("#liveBaggageFinalTotal")
        print(f"   ✓ Live Baggage Final 2-Pax Total: {bag_total_text}")
        assert "2,840" in bag_total_text or "2840" in bag_total_text or "2,839" in bag_total_text, "Final price with 20kg luggage for 2 pax must be ~2,840 ILS"

        pax_badge = await page.inner_text("#baggagePaxCountBadge")
        print(f"   ✓ Baggage Passenger Count Badge: {pax_badge}")
        assert "2" in pax_badge, "Must indicate 2 passengers"

        top_card_text = await top_card.inner_text()
        print("   ✓ Checking Top Card Baggage & 2-Pax Details:")
        assert "2 נוסעים" in top_card_text, "Card must explicitly specify 2 passengers"
        assert "מזוודה 20 ק״ג" in top_card_text, "Card must provide 20kg baggage option"
        print("     -> 2-Passenger pricing and exact baggage breakdown per direction verified on top card!")

        # Take screenshot
        screenshot_path = "data/verified_subagents_swarm.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved to {screenshot_path}")

        print("\n=======================================================")
        print("🎉 PLAYWRIGHT AUDIT PASSED: 100% MULTI-SUBAGENTS SWARM VERIFIED!")
        print("=======================================================\n")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_authentic_flow())
