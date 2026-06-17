"""
考研论坛 bbs.kaoyan.com 深度探测 — 搜索机制诊断
================================================
目标: 定位搜索返回 0 结果的根因
策略:
  1. 抓取搜索表单页 → 提取 searchid / formhash
  2. 尝试 POST 搜索
  3. 检查搜索是否需要特定 header (X-Requested-With 等)
  4. 查看页面是否有 JS 动态搜索机制
  5. 尝试访问已知帖子 tid 验证详情页可读性
  6. 检查 robots.txt 和 sitemap
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import sys
import io
from urllib.parse import quote

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "http://bbs.kaoyan.com"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
})


def get(url: str, **kw):
    defaults = {"timeout": 15}
    defaults.update(kw)
    resp = SESSION.get(url, **defaults)
    ct = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([\w-]+)", ct)
    if m:
        resp.encoding = m.group(1)
    else:
        m2 = re.search(rb'charset=([\w-]+)', resp.content[:2048])
        if m2:
            resp.encoding = m2.group(1).decode("ascii")
        else:
            resp.encoding = "utf-8"
    return resp


def wait(s=1.5):
    time.sleep(s)


# ═════════════════════════════════════════════════════════════
#  1. 获取搜索表单页，提取隐藏参数
# ═════════════════════════════════════════════════════════════

print("=" * 60)
print("  1. 搜索表单结构分析")
print("=" * 60)

resp = get(f"{BASE}/search.php")
soup = BeautifulSoup(resp.text, "html.parser")

# 提取所有 form 和隐藏字段
forms_info = []
for form in soup.select("form"):
    action = form.get("action", "")
    method = form.get("method", "get")
    hidden_inputs = []
    for inp in form.select("input[type=hidden]"):
        hidden_inputs.append({
            "name": inp.get("name", ""),
            "value": inp.get("value", ""),
        })
    forms_info.append({
        "action": action,
        "method": method,
        "hidden_fields": hidden_inputs,
    })

print(f"\n  发现 {len(forms_info)} 个搜索表单:")
for i, f in enumerate(forms_info):
    print(f"\n  表单 #{i+1}: {f['method'].upper()} → {f['action']}")
    for h in f["hidden_fields"]:
        print(f"    hidden: {h['name']} = {h['value'][:60]}")

# 提取 formhash
formhash_match = re.search(r'formhash["\']?\s*[=:]\s*["\']([a-f0-9]+)', resp.text, re.I)
if not formhash_match:
    formhash_match = re.search(r'name="formhash"\s+value="([^"]+)"', resp.text, re.I)
print(f"\n  formhash: {formhash_match.group(1) if formhash_match else '未找到'}")

# 提取可能的 searchid
searchid_patterns = [
    r'name="searchid"\s+value="([^"]+)"',
    r"searchid['\"]?\s*[:=]\s*['\"]([^'\"]+)",
    r"var\s+searchid\s*=\s*['\"]([^'\"]+)",
]
for p in searchid_patterns:
    m = re.search(p, resp.text, re.I)
    if m:
        print(f"  searchid (pattern): {m.group(1)[:80]}")

wait(1)

# ═════════════════════════════════════════════════════════════
#  2. 尝试 POST 搜索
# ═════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  2. POST 搜索尝试")
print("=" * 60)

# 先访问一次搜索页获取可能的 formhash
resp = get(f"{BASE}/search.php")
soup = BeautifulSoup(resp.text, "html.parser")
formhash = ""
m = re.search(r'name="formhash"\s+value="([^"]+)"', resp.text)
if m:
    formhash = m.group(1)

# 尝试不同的搜索方式
test_cases = [
    # 方式1: 标准 Discuz! GET 搜索 (已失败)
    # 方式2: POST 搜索
    {
        "label": "POST 标准表单",
        "method": "POST",
        "url": f"{BASE}/search.php?mod=forum",
        "data": {"searchsubmit": "yes", "srchtxt": "导师".encode("gbk"),
                 "formhash": formhash},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
    },
    # 方式3: POST + formhash + searchid
    {
        "label": "POST + formhash + 附加参数",
        "method": "POST",
        "url": f"{BASE}/search.php?mod=forum&searchsubmit=yes",
        "data": {"srchtxt": "导师".encode("gbk"), "formhash": formhash,
                 "searchsubmit": "true", "srchtype": "title",
                 "srchfrom": "0", "searchtime": str(int(time.time())),
                 "orderby": "lastpost", "ascdesc": "desc"},
    },
    # 方式4: 带 XHR header 的 GET
    {
        "label": "GET + Ajax XHR header",
        "method": "GET",
        "url": f"{BASE}/search.php?mod=forum&searchsubmit=yes&srchtxt={quote('导师', encoding='gbk')}",
        "headers": {"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/search.php"},
    },
    # 方式5: 使用 UTF-8 编码的 POST
    {
        "label": "POST UTF-8 编码",
        "method": "POST",
        "url": f"{BASE}/search.php?mod=forum&searchsubmit=yes",
        "data": {"srchtxt": "导师", "formhash": formhash, "searchsubmit": "true",
                 "srchtype": "fulltext"},
    },
    # 方式6: 先 GET search.php 获取 Cookie，再 GET 搜索
    {
        "label": "两步 GET (先访问搜索页获取Cookie)",
        "method": "GET",
        "url": f"{BASE}/search.php?mod=forum&searchsubmit=yes&srchtxt=导师",
        "pre_url": f"{BASE}/search.php",
    },
]

for tc in test_cases:
    wait(2)
    print(f"\n  [{tc['label']}]")
    headers = tc.get("headers", {})
    h = dict(SESSION.headers)
    h.update(headers)

    # 预处理步骤
    if "pre_url" in tc:
        SESSION.get(tc["pre_url"], timeout=15)

    try:
        if tc["method"] == "POST":
            data = tc.get("data", {})
            # 对 data 值进行编码
            encoded_data = {}
            for k, v in data.items():
                if isinstance(v, bytes):
                    encoded_data[k] = v
                else:
                    encoded_data[k] = str(v)
            resp = SESSION.post(tc["url"], data=encoded_data, headers=h, timeout=15, allow_redirects=True)
        else:
            resp = SESSION.get(tc["url"], headers=h, timeout=15, allow_redirects=True)

        resp.encoding = "utf-8"
        text = resp.text

        # 检测结果
        count = 0
        for p in [r"找到.*?(\d+)\s*个", r"共\s*(\d+)\s*", r"(\d+)\s*个相关"]:
            m = re.search(p, text)
            if m and int(m.group(1)) > 0:
                count = int(m.group(1))
                break

        # 检查返回页面是否有搜索框（说明可能跳回了搜索页而不是结果页）
        has_search_form = "<form" in text[:2000] and "search" in text[:2000].lower()
        has_results = count > 0

        status = "✅" if has_results else ("🔄 跳回搜索页" if has_search_form else "❌ 空结果")
        size_kb = round(len(text) / 1024, 1)
        print(f"  HTTP {resp.status_code} | {size_kb}KB | {count} 结果 | {status}")

        # 如果页面较小，打印关键部分
        if size_kb < 50 and not has_results:
            # 诊断：检查是否有错误提示
            soup = BeautifulSoup(resp.text, "html.parser")
            error_text = soup.get_text()[:500].strip()
            if error_text:
                print(f"  页面内容: {error_text[:300]}")

    except Exception as e:
        print(f"  ❌ {e}")

wait(1)

# ═════════════════════════════════════════════════════════════
#  3. 尝试 site: 搜索引擎方式
# ═════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  3. 论坛首页结构 — 找版块列表")
print("=" * 60)

resp = get(f"{BASE}/forum.php")
soup = BeautifulSoup(resp.text, "html.parser")

# 查找版块链接
board_links = []
for link in soup.select("a[href]"):
    href = link.get("href", "")
    text = link.get_text(strip=True)

    # 版块链接模式: forumdisplay&fid=X 或 forum-X-1.html
    m = re.search(r"(?:fid=|forum-)(\d+)", href)
    if m and text and len(text) > 1:
        board_links.append({
            "name": text,
            "fid": m.group(1),
            "href": href if href.startswith("http") else f"{BASE}/{href}",
        })

# 去重
seen = set()
unique_boards = []
for b in board_links:
    key = b["fid"]
    if key not in seen:
        seen.add(key)
        unique_boards.append(b)

print(f"\n  找到 {len(unique_boards)} 个版块:\n")
relevant_kw = ["考研", "导师", "考博", "复试", "调剂", "经验", "院校", "交流", "材料", "笔记", "公共课", "专业课"]

for b in unique_boards[:40]:
    tag = ""
    if any(kw in b["name"] for kw in relevant_kw):
        tag = " 🔥 导师相关"
    print(f"  [{b['fid']}] {b['name']}{tag}")

# 尝试按版块直接浏览帖子列表
if unique_boards:
    # 找最相关的版块
    relevant_boards = [b for b in unique_boards if any(kw in b["name"] for kw in relevant_kw)]
    if relevant_boards:
        test_board = relevant_boards[0]
        print(f"\n  测试版块 [{test_board['fid']}] {test_board['name']} 的帖子列表...")
        wait(1)
        resp = get(f"{BASE}/forum.php?mod=forumdisplay&fid={test_board['fid']}")
        soup2 = BeautifulSoup(resp.text, "html.parser")

        # 解析帖子
        thread_items = soup2.select("tbody[id^=normalthread_]")
        if not thread_items:
            thread_items = soup2.select("[id^=thread_]") or soup2.select(".sptable tr")

        print(f"  版块帖子条目: {len(thread_items)} 个")

        tids_found = []
        for item in thread_items[:10]:
            title_el = (
                item.select_one("a.xst") or item.select_one("a.s") or
                item.select_one("th a") or item.select_one("a[href*='tid=']")
            )
            if title_el:
                href = title_el.get("href", "")
                m = re.search(r"tid=(\d+)", href)
                if m:
                    tids_found.append(m.group(1))
                    title = title_el.get_text(strip=True)[:60]
                    print(f"    tid={m.group(1)} | {title}")

        if tids_found:
            # 测试读取任意一个帖子详情
            test_tid = tids_found[0]
            print(f"\n  测试帖子详情 tid={test_tid}...")
            wait(1)
            resp3 = get(f"{BASE}/forum.php?mod=viewthread&tid={test_tid}")
            soup3 = BeautifulSoup(resp3.text, "html.parser")

            main = ""
            for sel in ["td.t_f", "#post_0 .t_f", "div.t_f", ".postmessage"]:
                el = soup3.select_one(sel)
                if el:
                    main = el.get_text(" ", strip=True)
                    break

            login_wall = "登录" in resp3.text[:2000] and "才能" in resp3.text[:2000]
            replies = len(soup3.select("[id^=post_]"))

            print(f"  HTTP {resp3.status_code} | {round(len(resp3.text)/1024,1)}KB | "
                  f"{replies} 回复 | 登录墙: {login_wall}")
            print(f"  正文预览: {main[:200] if main else '(空)'}")

wait(1)

# ═════════════════════════════════════════════════════════════
#  4. 检查搜索引擎收录
# ═════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  4. robots.txt 和爬虫友好度")
print("=" * 60)

resp = get(f"{BASE}/robots.txt", timeout=10)
if resp.status_code == 200:
    print(f"  robots.txt 存在 ({len(resp.text)}B):")
    for line in resp.text.strip().split("\n")[:15]:
        if line.strip():
            print(f"    {line.strip()}")
else:
    print(f"  robots.txt: HTTP {resp.status_code} (不存在或禁止)")

# 检查 sitemap
wait(0.5)
resp = get(f"{BASE}/sitemap.xml", timeout=10)
print(f"  sitemap.xml: HTTP {resp.status_code}")

# ═════════════════════════════════════════════════════════════
#  5. 总结
# ═════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  5. 深度诊断总结")
print("=" * 60)

can_search = False
can_browse_boards = len(unique_boards) > 0
can_read_threads = False
if 'tids_found' in dir() and tids_found:
    can_read_threads = True

print(f"""
  ┌─────────────────────────────────────────────┐
  │  搜索接口状态                                │
  │    直连 GET:      ❌ 全 0 结果                │
  │    直连 POST:     见上方诊断                  │
  │    Ajax XHR:     见上方诊断                   │
  │  版块列表浏览:     {'✅' if can_browse_boards else '❌'}                        │
  │  帖子详情读取:     {'✅' if can_read_threads else '⚠️ 待验证'}                        │
  │  反爬力度:        🟢 低 (首页 10/10 通过)     │
  │  Cookie 需求:     🟢 低 (自动 Set-Cookie)     │
  │  CMS 版本:        Discuz! X3.2               │
  │                                                 │
  │  推荐策略:                                     │
  │  → 绕过自建搜索，通过版块列表+帖子内容匹配    │
  │  → 或使用外部搜索引擎 site: 限定              │
  └─────────────────────────────────────────────┘
""")

print("探测完成。")
