"""测试：独立线程中 SelectorEventLoop + Playwright async"""
import asyncio
import sys
import threading
import time

def test_thread():
    print(f"[thread] Python: {sys.version}")
    # 关键：在新线程中显式创建 SelectorEventLoop
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    print(f"[thread] loop type: {type(loop).__name__}")
    
    async def test_inner():
        from playwright.async_api import async_playwright
        print("[thread] starting playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            print(f"[thread] browser launched: {browser}")
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            print(f"[thread] page title: {title}")
            await browser.close()
        print("[thread] done")
    
    try:
        loop.run_until_complete(test_inner())
    except Exception as e:
        print(f"[thread] ERROR: {type(e).__name__}: {e}")
    finally:
        loop.close()

t = threading.Thread(target=test_thread)
t.start()
t.join(timeout=30)
print("[main] thread finished")
