"""调试版3 — 直接监听 nsfcfund_search.php 响应"""
import sys, os, json, time
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
PHPSESSID = config.get("cookies", {}).get("letpub", "").strip()

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

    # 捕获 nsfcfund_search 响应
    search_response_body = [None]
    def on_response(resp):
        if 'nsfcfund_search' in resp.url:
            print(f"[RESP] {resp.status} {resp.url}")
            try:
                body = resp.text()
                search_response_body[0] = body
                print(f"[RESP] body length: {len(body)}")
                print(f"[RESP] body preview: {body[:500]}")
                # 检查是否是 JSON
                if body.strip().startswith('{') or body.strip().startswith('['):
                    data = json.loads(body)
                    print(f"[RESP] JSON keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                else:
                    print(f"[RESP] not JSON, first 200 chars: {body[:200]}")
            except Exception as e:
                print(f"[RESP] body read error: {e}")

    page.on("response", on_response)

    print("[1] 访问搜索页...")
    page.goto("https://www.letpub.com.cn/index.php?page=grant", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    page.evaluate("""() => {
        document.querySelectorAll('.layui-layer-shade, .letpub_popup_notify_window').forEach(s => s.remove());
        document.querySelectorAll('.layui-layer-close').forEach(c => c.click());
    }""")
    time.sleep(0.5)

    print(f"\n[2] 填入表单...")
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

    print(f"\n[3] 触发搜索...")
    page.evaluate("""() => { checksubmit('advanced', 'list', 1); }""")

    # 等待响应
    print(f"\n[4] 等待 AJAX 响应...")
    for i in range(20):
        time.sleep(1)
        if search_response_body[0] is not None:
            print(f"   [{i+1}s] 响应已收到!")
            break
        row_count = page.evaluate("""() => {
            var t = document.getElementById('keyword-datalist');
            return t ? t.querySelectorAll('tbody tr td').length : 0;
        }""")
        if row_count > 0:
            print(f"   [{i+1}s] 表格有 {row_count} 个单元格!")
            break

    # 最终检查
    print(f"\n[5] 最终状态:")
    final = page.evaluate("""() => {
        var t = document.getElementById('keyword-datalist');
        if (!t) return {exists: false};
        var tbody = t.querySelector('tbody');
        return {
            exists: true,
            rows: t.querySelectorAll('tbody tr').length,
            tbodyHTML: tbody ? tbody.innerHTML.substring(0, 1000) : 'no tbody',
            tbodyText: tbody ? tbody.innerText.substring(0, 500) : '',
        };
    }""")
    print(f"   表格存在: {final.get('exists')}")
    print(f"   行数: {final.get('rows', 0)}")
    if final.get('tbodyHTML'):
        print(f"   tbody HTML: {final['tbodyHTML'][:500]}")
    if final.get('tbodyText'):
        print(f"   tbody Text: {final['tbodyText'][:300]}")

    # 如果有响应体，检查其中的数据
    if search_response_body[0]:
        body = search_response_body[0]
        print(f"\n[6] AJAX 响应分析:")
        print(f"   长度: {len(body)}")
        # 尝试解析
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        print(f"   {k}: list[{len(v)}]")
                        if v:
                            print(f"      first item: {str(v[0])[:200]}")
                    elif isinstance(v, str):
                        print(f"   {k}: '{v[:100]}'")
                    else:
                        print(f"   {k}: {v}")
            elif isinstance(data, list):
                print(f"   array[{len(data)}]")
                if data:
                    print(f"   first: {str(data[0])[:200]}")
        except json.JSONDecodeError:
            # 可能是 HTML 片段
            print(f"   非 JSON，可能是 HTML 片段:")
            print(f"   {body[:500]}")
            # 检查是否有 <tr> 标签
            tr_count = body.count('<tr')
            print(f"   <tr> 标签数: {tr_count}")

    ctx.close()
    browser.close()
    print("\n调试完成")
