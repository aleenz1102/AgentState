import asyncio
import os
from playwright.async_api import async_playwright
from PIL import Image

async def capture_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        # Enable dialog handler to automatically accept rollbacks
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        
        await page.goto("http://localhost:8080/dashboard")
        await page.wait_for_timeout(1000)
        
        frames = []
        
        async def snap(times=1, delay=200):
            for _ in range(times):
                path = f"frame_temp.png"
                await page.screenshot(path=path)
                img = Image.open(path).convert("RGB")
                frames.append(img.copy())
                await page.wait_for_timeout(delay)
                if os.path.exists(path):
                    os.remove(path)

        # 1. Initial load
        await snap(3, 300)
        
        # 2. Click session if list exists
        session_item = page.locator(".cursor-pointer").first
        if await session_item.count() > 0:
            await session_item.click()
            await snap(2, 200)
            
        # 3. Scroll down slowly
        for i in range(4):
            await page.mouse.wheel(0, 150)
            await snap(1, 150)
            
        # 4. Click rollback button on Step #2 if present
        rollback_btn = page.locator("button:has-text('Rollback')").last
        if await rollback_btn.count() > 0:
            await rollback_btn.click()
            await snap(4, 300)
            
        # 5. Final pause
        await snap(3, 300)
        
        await browser.close()
        
        # Save as optimized GIF
        if frames:
            os.makedirs("assets", exist_ok=True)
            frames[0].save(
                "assets/demo.gif",
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=250,
                loop=0
            )
            print("Successfully saved assets/demo.gif!")

if __name__ == "__main__":
    asyncio.run(capture_demo())
