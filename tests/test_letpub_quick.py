"""快速诊断 AJAX 响应"""
import json, time, re
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
PHPSESSID = config.get("cookies", {}).get("letpub", "").strip()
print(f"PHPSESSID: {PHPSESSID[:15]}...")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(locale="zh-CN", user_agent="Mozilla/5.0 Chrome/124")
    ctx.add_cookies([{"name": "PHPSESSID", "value": PHPSESSID, "domain": "www.letpub.com.cn", "path": "/"}])
    page = ctx.new_page()

    ajax = []
    def on_resp(r):
        if "nsfcfund_search" in r.url:
            try: ajax.append(r.text())
            except: pass
    page.on("response", on_resp)

    page.goto("https://www.letpub.com.cn/index.php?page=grant", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    # 关闭所有弹窗（关键！弹窗可能阻止表单交互）
    page.evaluate("""() => {
        document.querySelectorAll('.layui-layer-shade, .letpub_popup_notify_window').forEach(s => s.remove());
        document.querySelectorAll('.layui-layer-close').forEach(c => c.click());
    }""")
    time.sleep(1)

    page.evaluate("""
    () => {
        var f = document.querySelector("#searchform_advanced");
        f.querySelector('input[name="person"]').value = "刘玉身";
        f.querySelector('input[name="company"]').value = "清华大学";
        var s = f.querySelector('select[name="startTime"]');
        if (s) s.selectedIndex = s.options.length - 1;
    }
    """)
    page.evaluate('() => { checksubmit("advanced","list",1); }')

    for i in range(15):
        time.sleep(1)
        if ajax:
            break

    if ajax:
        html = ajax[0]
        print(f"AJAX response length: {len(html)}")
        # 搜索记录数
        m = re.search(r"匹配[：:]\s*<b>(\d+)</b>条", html)
        if m:
            print(f"匹配记录数: {m.group(1)}")

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="keyword-datalist")
        print(f"Table #keyword-datalist found: {table is not None}")

        if table:
            rows = table.find_all("tr")
            print(f"Total tr: {len(rows)}")
            ths = table.find_all("th")
            if ths:
                print(f"Headers: {[th.get_text(strip=True) for th in ths[:10]]}")
            # 找第一个数据行
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 5:
                    texts = [td.get_text(strip=True)[:25] for td in tds[:8]]
                    print(f"First data row ({len(tds)} cols): {texts}")
                    break
        else:
            # 找所有表格
            tables = soup.find_all("table")
            print(f"Tables found: {len(tables)}")
            for i, t in enumerate(tables[:5]):
                trs = t.find_all("tr")
                tid = t.get("id", "")
                cls = t.get("class", "")
                print(f"  Table {i}: id={tid} class={cls} rows={len(trs)}")
                if trs:
                    first = trs[0]
                    ths = first.find_all("th")
                    tds = first.find_all("td")
                    if ths:
                        print(f"    headers: {[th.get_text(strip=True)[:20] for th in ths[:8]]}")
                    elif tds:
                        print(f"    first row: {[td.get_text(strip=True)[:20] for td in tds[:8]]}")
    else:
        print("No AJAX response received")

    ctx.close()
    browser.close()
