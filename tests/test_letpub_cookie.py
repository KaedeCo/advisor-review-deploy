"""
LetPub (letpub.com.cn) Cookie 需求探查
========================================
目标: 确定搜索功能需要哪些 Cookie 字段
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import json

BASE = "https://www.letpub.com.cn"
SEARCH_URL = f"{BASE}/index.php?page=grant"

def probe():
    print("=" * 60)
    print("  LetPub Cookie 需求探查")
    print("=" * 60)

    with sync_playwright() as p:
        # ── 1. 无 Cookie 访问搜索页 ──
        print("\n[1] 无 Cookie 访问搜索页")
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(locale="zh-CN")
        page = ctx.new_page()
        page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # 检查是否被拦截
        title = page.title()
        has_login_form = page.locator('input[name="username"], input[name="email"], input[name="login"]').count() > 0
        has_search = page.locator('input[name="person"]').count() > 0
        url = page.url

        print(f"  URL: {url}")
        print(f"  Title: {title}")
        print(f"  搜索框可见: {has_search}")
        print(f"  登录表单可见: {has_login_form}")

        # 尝试搜索（不登录）
        if has_search:
            page.evaluate("() => { document.querySelector('input[name=\"person\"]').value = '张三'; }")
            page.evaluate("() => { if (typeof checksubmit === 'function') checksubmit('advanced','list',1); }")
            time.sleep(4)
            has_results = page.locator("table#keyword-datalist tbody tr td").count() >= 5
            print(f"  搜索'张三'有结果: {has_results}")
        ctx.close()

        # ── 2. 检查登录页 ──
        print("\n[2] 检查登录页")
        ctx2 = browser.new_context(locale="zh-CN")
        page2 = ctx2.new_page()
        page2.goto(f"{BASE}/index.php?page=login", wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        title2 = page2.title()
        print(f"  登录页 Title: {title2}")

        # 找登录表单
        username_inputs = page2.locator('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]').count()
        password_inputs = page2.locator('input[type="password"]').count()
        submit_btns = page2.locator('button[type="submit"], input[type="submit"]').count()

        print(f"  用户名输入框: {username_inputs}")
        print(f"  密码输入框: {password_inputs}")
        print(f"  提交按钮: {submit_btns}")

        if username_inputs > 0:
            # 列出所有可能的登录输入框
            for inp in page2.locator('input').all():
                name = inp.get_attribute('name') or ''
                ty = inp.get_attribute('type') or ''
                placeholder = inp.get_attribute('placeholder') or ''
                _id = inp.get_attribute('id') or ''
                is_visible = inp.is_visible()
                if is_visible and (ty in ('text', 'email', 'password') or name):
                    print(f"    可见: name={name} type={ty} id={_id} placeholder={placeholder[:30]}")

        # 当前 Cookie
        cookies_before = ctx2.cookies()
        print(f"  登录前 Cookie: {len(cookies_before)} 个")
        for c in cookies_before:
            print(f"    {c['name']} = {c['value'][:50]}")

        ctx2.close()

        # ── 3. 检查除登录外，搜索页本身给的 Cookie ──
        print("\n[3] 访问搜索页后获得的 Cookie")
        ctx3 = browser.new_context(locale="zh-CN")
        page3 = ctx3.new_page()
        page3.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        cookies_after = ctx3.cookies()
        print(f"  获得 Cookie: {len(cookies_after)} 个")
        for c in cookies_after:
            print(f"    {c['name']} = {c['value'][:80]}")
            print(f"      domain={c['domain']} expires={c.get('expires', 'session')}")

        ctx3.close()

        # ── 4. 检查已登录浏览器可能有的 Cookie ──
        print("\n[4] LetPub 已知 Cookie 参考（从页面可推断）")
        page4 = browser.new_context(locale="zh-CN").new_page()
        page4.goto(BASE, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        # 检查页面上是否有 JS 设置 localStorage 的迹象
        local_script = page4.evaluate("""() => {
            const keys = [];
            try {
                for (let i = 0; i < localStorage.length; i++) {
                    keys.push(localStorage.key(i));
                }
            } catch(e) {}
            return keys;
        }""")
        print(f"  localStorage keys: {local_script}")

        # 检查 PHPSESSID
        all_cookies = browser.new_context(locale="zh-CN").cookies()
        
        page4.close()
        browser.close()

    print("\n" + "=" * 60)
    print("  探查完成")
    print("=" * 60)


if __name__ == "__main__":
    probe()
