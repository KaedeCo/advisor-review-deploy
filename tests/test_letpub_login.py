"""
LetPub 登录流程深度探查
"""
import sys, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE = "https://www.letpub.com.cn"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(locale="zh-CN")
    page = ctx.new_page()

    # 1. 访问登录页
    print("[1] 登录页分析")
    page.goto(f"{BASE}/index.php?page=login", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    print(f"   当前URL: {page.url}")
    print(f"   Title: {page.title()}")

    # 分析登录表单
    forms = page.evaluate("""() => {
        const forms = document.querySelectorAll('form');
        return Array.from(forms).map(f => ({
            action: f.action,
            method: f.method,
            inputs: Array.from(f.querySelectorAll('input')).map(i => ({
                name: i.name,
                type: i.type,
                id: i.id,
                placeholder: i.placeholder,
                visible: i.offsetParent !== null
            }))
        }));
    }""")
    
    for i, f in enumerate(forms):
        print(f"\n   表单 #{i}: {f['method']} -> {f['action']}")
        for inp in f['inputs']:
            if inp['visible'] or inp['type'] in ('submit', 'hidden'):
                print(f"     {inp['type']:8s} name={inp['name']:15s} id={inp['id']:15s} placeholder={inp.get('placeholder','')[:30]}")

    # 2. 尝试模拟登录（观察表单提交行为）
    print("\n[2] 登录请求探针")
    
    # 监听网络请求
    login_url_hit = []
    def on_request(req):
        if 'login' in req.url.lower() and req.method == 'POST':
            login_url_hit.append({
                'url': req.url,
                'method': req.method,
                'post_data': req.post_data[:200] if req.post_data else None,
            })
    
    page.on('request', on_request)

    # 填入假凭证并提交
    try:
        page.fill('input[name="email"]', 'test@example.com')
        page.fill('input[name="password"]', 'test123456')
    except:
        # 尝试其他选择器
        for sel in ['input#email', 'input[type="text"]', 'input[type="email"]']:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.fill('test@example.com')
                    break
            except:
                pass

    # 找到提交方式（可能是 button 或 input submit 或不带 type 的 button）
    submit_selectors = ['button', 'input[type="submit"]', 'a.login-btn', '.login-btn', '[class*="login"]']
    clicked = False
    for sel in submit_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible():
                # 检查是否包含登录文字
                text = btn.inner_text() if btn.is_visible() else ''
                if '登录' in text or 'login' in text.lower() or '登' in text:
                    btn.click()
                    clicked = True
                    print(f"   点击: {sel} (text={text[:20]})")
                    break
        except:
            pass

    if not clicked:
        # 直接触发表单提交
        page.evaluate("() => { const f = document.querySelector('form'); if (f) f.submit(); }")
        print("   备用: JS form.submit()")

    time.sleep(4)

    # 分析结果
    print(f"\n   提交后 URL: {page.url}")
    print(f"   Title: {page.title()}")
    
    # 检查报错信息
    error = page.locator('.error, .alert, .msg, [class*="error"], [class*="warning"]').first
    if error.is_visible():
        print(f"   错误提示: {error.inner_text()[:200]}")

    # 捕获到的登录请求
    print(f"\n   捕获到 {len(login_url_hit)} 个登录 POST 请求:")
    for r in login_url_hit:
        print(f"     {r['method']} {r['url']}")
        if r.get('post_data'):
            print(f"     data: {r['post_data']}")

    # 3. 登录后 Cookie
    cookies_after = ctx.cookies()
    print(f"\n[3] 登录尝试后 Cookie ({len(cookies_after)} 个):")
    for c in cookies_after:
        if c['name'] not in ('_ga', '_gid', '_gat', '__utma', '__utmb', '__utmc', '__utmt', '__utmz',
                              '_ga_MQPLXSWFB7', '_ga_JVDFHF8S2G'):
            print(f"    ★ {c['name']} = {c['value'][:80]}")
        else:
            print(f"      {c['name']} = {c['value'][:50]} (GA)")

    # 4. 回到搜索页测试
    print("\n[4] 回搜索页测试搜索")
    page.goto(f"{BASE}/index.php?page=grant", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    
    page.evaluate("() => { document.querySelector('input[name=\"person\"]').value = '张三'; }")
    page.evaluate("() => { if (typeof checksubmit === 'function') checksubmit('advanced','list',1); }")
    time.sleep(4)
    has_results = page.locator("table#keyword-datalist tbody tr td").count() >= 5
    print(f"   搜索'张三'有结果: {has_results}")
    
    if has_results:
        rows = page.locator("table#keyword-datalist tbody tr").count()
        print(f"   表格行数: {rows}")
        # 输出第一行数据
        first_row = page.locator("table#keyword-datalist tbody tr").first.inner_text()
        print(f"   首行: {first_row[:200]}")

    ctx.close()
    browser.close()
    print("\n探查完成")
