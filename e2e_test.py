import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser Error: {err}"))
        
        print("Navigating to frontend...")
        await page.goto("http://localhost:3000", timeout=60000)
        
        print("Entering search query...")
        await page.fill('input[placeholder="What would you like to explore today?"]', "Impact of Quantum Computing on Modern Cryptography")
        await page.click('button:has-text("Research")')
        
        print("Waiting for research to complete (this may take up to 2 minutes)...")
        export_btn = page.locator('button:has-text("Export PDF")')
        await export_btn.wait_for(state="visible", timeout=120000)
        
        print("Research complete. Exporting PDF...")
        # Start clicking before expect_download to avoid missing the event
        async with page.expect_download(timeout=120000) as download_info:
            await export_btn.click()
            
        download = await download_info.value
        
        out_dir = "d:/deep_research_agent/info_files"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "test_research_report.pdf")
        
        print(f"Saving downloaded PDF to {out_path}...")
        await download.save_as(out_path)
        
        print("Success! File saved.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
