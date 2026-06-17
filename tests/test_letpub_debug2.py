"""调试版2 — 监听网络请求 + 延长等待"""
import sys, os, json, time
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
PHPSESSID = config.get("cookies", {}).get("letpub", "").strip()
print(f"[DEBUG] PHPSESSID: {PHPSESSID[:20]}...")

from playwright.sync_api import sync_playwright

ADVISOR = "刘玉身"
UNIVERSITY = "清华大学"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(locale="zh-CN",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")

    if PHPSESSID:
        ctx.add_cookies([{"name": "PHPSESSID", "value": PHPSESSID, "domain": "www.letpub.com.cn", "path": "/"}])

    page = ctx.new_page()

    # 监听所有网络请求
    ajax_requests = []
    def on_request(req):
        if 'grant' in req.url.lower() or 'ajax' in req.url.lower() or 'search' in req.url.lower() or 'list' in req.url.lower():
            ajax_requests.append({"url": req.url, "method": req.method, "post_data": req.post_data[:200] if req.post_data else None})

    def on_response(resp):
        if 'grant' in resp.url.lower() or 'ajax' in resp.url.lower() or 'search' in resp.url.lower() or 'list' in resp.url.lower():
            try:
                body = resp.text()[:500]
            except:
                body = "(binary)"
            print(f"   [RESP] {resp.status} {resp.url[:100]}")
            if body and len(body) > 10:
                print(f"          body: {body[:200]}")

    page.on("request", on_request)
    page.on("response", on_response)

    print("[1] 访问搜索页...")
    page.goto("https://www.letpub.com.cn/index.php?page=grant", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # 关闭弹窗
    page.evaluate("""() => {
        document.querySelectorAll('.layui-layer-shade, .letpub_popup_notify_window').forEach(s => s.remove());
        document.querySelectorAll('.layui-layer-close').forEach(c => c.click());
    }""")
    time.sleep(0.5)

    print(f"\n[2] 填入表单 + 设置年份...")
    page.evaluate("""
    (data) => {
        var form = document.querySelector('#searchform_advanced');
        form.querySelector('input[name="person"]').value = data.name;
        if (data.univ) form.querySelector('input[name="company"]').value = data.univ;
        var startTime = form.querySelector('select[name="startTime"]');
        var endTime = form.querySelector('select[name="endTime"]');
        if (startTime) startTime.selectedIndex = startTime.options.length - 1;
        if (endTime) endTime.selectedIndex = 0;
    }
    """, {"name": ADVISOR, "univ": UNIVERSITY})

    print(f"\n[3] 触发 checksubmit...")

    # 检查 checksubmit 的完整代码
    checksubmit_code = page.evaluate("""() => {
        if (typeof checksubmit === 'function') {
            return checksubmit.toString().substring(0, 500);
        }
        return 'not found';
    }""")
    print(f"   checksubmit 代码:\n{checksubmit_code}")

    page.evaluate("""() => { checksubmit('advanced', 'list', 1); }""")

    # 等待更长时间 — 逐秒检查
    print(f"\n[4] 等待 AJAX 响应 (最多 15 秒)...")
    for i in range(15):
        time.sleep(1)
        row_count = page.evaluate("""() => {
            var t = document.getElementById('keyword-datalist');
            return t ? t.querySelectorAll('tbody tr td').length : 0;
        }""")
        if row_count > 0:
            print(f"   [{i+1}s] 发现 {row_count} 个单元格!")
            break
        if i % 3 == 2:
            print(f"   [{i+1}s] 仍无数据...")

    # 最终检查
    print(f"\n[5] 最终结果:")
    result = page.evaluate("""() => {
        var t = document.getElementById('keyword-datalist');
        if (!t) return {exists: false};
        var rows = t.querySelectorAll('tbody tr');
        var html = t.querySelector('tbody') ? t.querySelector('tbody').innerHTML.substring(0, 500) : '';
        return {exists: true, rows: rows.length, html: html};
    }""")
    print(f"   表格存在: {result.get('exists')}")
    print(f"   行数: {result.get('rows', 0)}")
    if result.get('html'):
        print(f"   tbody HTML: {result['html'][:300]}")

    print(f"\n[6] 捕获到的 AJAX 请求 ({len(ajax_requests)} 个):")
    for req in ajax_requests:
        print(f"   {req['method']} {req['url'][:120]}")
        if req.get('post_data'):
            print(f"        data: {req['post_data']}")

    # 检查是否有 loading 遮罩仍然显示
    loading = page.evaluate("""() => {
        var loaders = document.querySelectorAll('.layui-layer-loading, .layui-layer-load');
        return loaders.length;
    }""")
    print(f"\n[7] Loading 遮罩数: {loading}")

    ctx.close()
    browser.close()
    print("\n调试完成")
