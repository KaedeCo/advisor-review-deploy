"""测试：multiprocessing 子进程运行 Playwright"""
import multiprocessing
import sys
import os

def run_playwright_in_subprocess(result_queue, phpsessid, advisor_name, university):
    """在独立子进程中运行 Playwright（完整 Python 解释器实例）"""
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    async def inner():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            await browser.close()
            return title
    
    try:
        result = asyncio.run(inner())
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {e}"))

if __name__ == "__main__":
    # 必须用 spawn 方式（Windows 默认），确保子进程是全新 Python 解释器
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=run_playwright_in_subprocess, args=(q, "", "张三", "清华"))
    p.start()
    p.join(timeout=30)
    
    if not q.empty():
        status, result = q.get()
        print(f"Status: {status}")
        print(f"Result: {result}")
    else:
        print("No result (timeout or crash)")
    print("Done")
