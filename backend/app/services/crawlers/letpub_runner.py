"""
LetPub 独立搜索脚本 — 由 letpub.py 通过 subprocess 调用
使用 sync_playwright + 直接拦截 AJAX 响应 HTML 解析数据

用法:
  python -m app.services.crawlers.letpub_runner <phpsessid> <advisor_name> <university>
输出: JSON 到 stdout
"""
import sys
import os
import json
import time
import re


def run_search(phpsessid: str, advisor_name: str, university: str):
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )

        if phpsessid:
            ctx.add_cookies([{
                "name": "PHPSESSID", "value": phpsessid,
                "domain": "www.letpub.com.cn", "path": "/",
            }])

        page = ctx.new_page()

        # 拦截 nsfcfund_search.php 的 AJAX 响应
        ajax_responses = []
        def on_response(resp):
            if 'nsfcfund_search' in resp.url:
                try:
                    ajax_responses.append(resp.text())
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            page.goto("https://www.letpub.com.cn/index.php?page=grant",
                      wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # 关闭弹窗
            page.evaluate("""() => {
                document.querySelectorAll('.layui-layer-shade, .letpub_popup_notify_window').forEach(s => s.remove());
                document.querySelectorAll('.layui-layer-close').forEach(c => c.click());
            }""")
            time.sleep(0.5)

            # 填入表单 + 设置年份范围 1997-2023
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
            """, {"name": advisor_name, "univ": university})

            # 触发搜索
            page.evaluate("""() => { checksubmit('advanced', 'list', 1); }""")

            # 等待 AJAX 响应
            for i in range(15):
                time.sleep(1)
                if ajax_responses:
                    break

            if not ajax_responses:
                print(json.dumps([]))
                return

            # 直接从 AJAX 响应 HTML 中解析数据
            html = ajax_responses[0]
            projects = _parse_ajax_html(html, advisor_name, university)

            # 翻页：如果有更多页，继续触发
            all_projects = list(projects)
            total_count = _extract_total_count(html)

            if total_count > 10:
                for pg in range(2, min(4, (total_count // 10) + 2)):
                    time.sleep(2)
                    ajax_responses.clear()
                    page.evaluate(f"""() => {{ checksubmit('advanced', 'list', {pg}); }}""")
                    for _ in range(10):
                        time.sleep(1)
                        if ajax_responses:
                            break
                    if ajax_responses:
                        more = _parse_ajax_html(ajax_responses[0], advisor_name, university)
                        if not more:
                            break
                        all_projects.extend(more)
                    else:
                        break

            print(json.dumps(all_projects, ensure_ascii=False))

        finally:
            ctx.close()
            browser.close()


def _extract_total_count(html: str) -> int:
    """从 AJAX 响应中提取总记录数"""
    m = re.search(r'匹配[：:]\s*<b>(\d+)</b>条', html)
    if m:
        return int(m.group(1))
    m = re.search(r'共(\d+)条', html)
    if m:
        return int(m.group(1))
    return 0


def _parse_ajax_html(html: str, advisor_name: str, university: str) -> list:
    """直接解析 AJAX 返回的 HTML 片段中的表格数据"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # AJAX 返回的 HTML 中包含完整的表格
    table = soup.find("table", id="keyword-datalist")
    if not table:
        # 尝试找任何包含数据的表格
        tables = soup.find_all("table")
        for t in tables:
            rows = t.find_all("tr")
            if len(rows) > 1:
                table = t
                break

    if not table:
        return []

    # 提取表头
    headers = []
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(strip=True) for th in thead.find_all("th")]
    else:
        # 第一行可能是表头
        first_row = table.find("tr")
        if first_row:
            ths = first_row.find_all("th")
            if ths:
                headers = [th.get_text(strip=True) for th in ths]

    projects = []
    rows = table.find_all("tr")

    for row in rows:
        # 跳过表头行
        ths = row.find_all("th")
        if ths:
            continue

        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        col_texts = [td.get_text(" ", strip=True) for td in cols]
        if not any(col_texts):
            continue

        p = {}
        for i, h in enumerate(headers):
            if i >= len(col_texts):
                break
            h_lower = h
            if "项目名称" in h_lower or "标题" in h_lower:
                p["project_name"] = col_texts[i]
            elif "批准号" in h_lower or "编号" in h_lower:
                p["project_code"] = col_texts[i]
            elif "负责人" in h_lower:
                p["pi_name"] = col_texts[i]
            elif "单位" in h_lower or "依托" in h_lower:
                p["org_name"] = col_texts[i]
            elif "金额" in h_lower or "经费" in h_lower or "资助" in h_lower:
                p["amount_text"] = col_texts[i]
                m = re.search(r"([\d.]+)", col_texts[i])
                p["amount_wan"] = float(m.group(1)) if m else 0.0
            elif "类别" in h_lower or "类型" in h_lower:
                p["category"] = col_texts[i]
            elif "年份" in h_lower or "时间" in h_lower or "年度" in h_lower or "批准" in h_lower:
                p["start_year"] = col_texts[i]

        # 如果没有匹配到表头，按位置回退
        if not p and len(col_texts) >= 5:
            p["project_name"] = col_texts[0]
            p["pi_name"] = col_texts[1] if len(col_texts) > 1 else ""
            p["org_name"] = col_texts[2] if len(col_texts) > 2 else ""
            p["amount_text"] = col_texts[3] if len(col_texts) > 3 else ""
            m = re.search(r"([\d.]+)", p.get("amount_text", ""))
            p["amount_wan"] = float(m.group(1)) if m else 0.0
            p["project_code"] = col_texts[4] if len(col_texts) > 4 else ""
            p["category"] = col_texts[5] if len(col_texts) > 5 else ""
            p["start_year"] = col_texts[6] if len(col_texts) > 6 else ""

        if p:
            projects.append(p)

    return projects


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: letpub_runner.py <phpsessid> <advisor_name> [university]"}))
        sys.exit(1)

    phpsessid = sys.argv[1]
    advisor_name = sys.argv[2]
    university = sys.argv[3] if len(sys.argv) > 3 else ""

    try:
        run_search(phpsessid, advisor_name, university)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
