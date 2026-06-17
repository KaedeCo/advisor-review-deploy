"""
考研论坛 bbs.kaoyan.com 端到端爬虫验证
========================================
验证: UTF-8 POST 搜索 → 解析结果 → 读取帖子详情
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

def wait(s=1.5):
    time.sleep(s)

def get(url):
    resp = SESSION.get(url, timeout=15)
    resp.encoding = "utf-8"
    return resp

def search(kw: str) -> tuple[int, list[dict]]:
    """UTF-8 POST 搜索"""
    # 先访问搜索页获取 formhash
    get(f"{BASE}/search.php")
    wait(0.5)
    text = get(f"{BASE}/search.php").text
    m = re.search(r'name="formhash"\s+value="([^"]+)"', text)
    formhash = m.group(1) if m else ""

    data = {
        "formhash": formhash,
        "srchtxt": kw,
        "searchsubmit": "true",
    }
    resp = SESSION.post(f"{BASE}/search.php?mod=forum&searchsubmit=yes",
                        data=data, timeout=15)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # 结果计数
    total = 0
    for p in [r"找到.*?(\d+)\s*个", r"共\s*(\d+)\s*", r"(\d+)\s*个相关"]:
        m = re.search(p, resp.text)
        if m and int(m.group(1)) > 0:
            total = int(m.group(1))
            break

    # 解析结果条目
    items = []
    for container in soup.select(".pbw, li.bbda, table[id^=thread_], li[id^=thread], dl.bbm, li.pbw"):
        try:
            title_el = (
                container.select_one("a.xst") or container.select_one("a.s") or
                container.select_one("h3 a") or container.select_one("a[href*='tid=']")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            m = re.search(r"tid=(\d+)", href)
            if not m:
                continue
            tid = m.group(1)

            # 提取版块/breadcrumb
            board_el = container.select_one("a[href*='forumdisplay']") or container.select_one(".xi1 a")
            board = board_el.get_text(strip=True) if board_el else ""

            # 提取片段
            snippet_el = container.select_one("dd, p.xg1, .p_content")
            snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""

            items.append({"title": title, "tid": tid, "board": board, "snippet": snippet})
        except:
            continue

    return total, items


def get_thread_detail(tid: str) -> dict:
    """获取帖子详情"""
    url = f"{BASE}/forum.php?mod=viewthread&tid={tid}"
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # 检测登录墙
    text_lower = resp.text[:3000].lower()
    login_indicators = ["需要登录", "请登录", "无权", "您所在的用户组", "登录后", "阅读权限"]
    is_login_wall = any(kw in resp.text for kw in login_indicators)

    # 标题
    title = ""
    for sel in ["h1.ts", "h1.ph", "#thread_subject", "h1"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)[:100]
            break

    # 正文
    main_content = ""
    for sel in ["td.t_f", "#post_0 .t_f", "div.t_f", ".postmessage", ".pct .pcb"]:
        el = soup.select_one(sel)
        if el:
            main_content = el.get_text(" ", strip=True)
            break

    # 回复
    reply_posts = soup.select("[id^=post_]")
    replies = []
    for post in reply_posts[1:11]:  # 最多10条回复
        for sel in ["td.t_f", ".t_f", ".postmessage"]:
            cel = post.select_one(sel)
            if cel:
                replies.append(cel.get_text(" ", strip=True)[:300])
                break

    return {
        "tid": tid, "title": title,
        "status": resp.status_code,
        "size_kb": round(len(resp.text) / 1024, 1),
        "login_wall": is_login_wall,
        "main_content": main_content[:500],
        "reply_count": len(reply_posts) - 1 if reply_posts else 0,
        "replies_sample": replies[:3],
    }


# ═════════════════════════════════════════════════════════════
#  主流程
# ═════════════════════════════════════════════════════════════

print("=" * 60)
print("  考研论坛 bbs.kaoyan.com — 端到端爬虫验证")
print("=" * 60)

# 测试关键词
test_queries = [
    "导师",
    "选导师",
    "联系导师",
    "导师推荐",
    "导师评价",
    "张老师",
    "经验",
]

all_tids = []
for q in test_queries:
    wait(2)
    total, items = search(q)
    tids = [i["tid"] for i in items]
    all_tids.extend(tids)
    print(f"\n[{q}] {total} 结果 | {len(items)} 条/页")
    for item in items[:3]:
        print(f"  tid={item['tid']} | [{item['board']}] {item['title'][:60]}")

# 去重
unique_tids = list(dict.fromkeys(all_tids))
print(f"\n  合计 {len(unique_tids)} 个唯一 tid")

# 测试帖子详情
if unique_tids:
    print("\n" + "=" * 60)
    print("  帖子详情访问测试 (前10个 tid)")
    print("=" * 60)

    detail_results = []
    for tid in unique_tids[:10]:
        wait(1.5)
        d = get_thread_detail(tid)
        detail_results.append(d)
        icon = "🚫登录墙" if d["login_wall"] else "✅"
        print(f"\n  {icon} tid={tid} | HTTP {d['status']} | {d['size_kb']}KB | {d['reply_count']}回复")
        print(f"  标题: {d['title'][:80]}")
        if d["main_content"]:
            print(f"  正文: {d['main_content'][:150]}...")
        if d["login_wall"]:
            print(f"  ⚠️ 需要登录才能查看")

    accessible = sum(1 for d in detail_results if not d["login_wall"])
    print(f"\n  详情可访问率: {accessible}/{len(detail_results)}")

# 测试翻页
print("\n" + "=" * 60)
print("  翻页测试")
print("=" * 60)

# 搜索一个有大量结果的词，测试翻页
wait(1)
total, page1 = search("考研")
print(f"\n  第1页: {len(page1)} 条 (总计 {total})")

wait(2)
# POST 翻页：多一个 page 参数
resp = get(f"{BASE}/search.php?mod=forum&searchsubmit=yes")
m = re.search(r'name="formhash"\s+value="([^"]+)"', resp.text)
formhash = m.group(1) if m else ""
data = {"formhash": formhash, "srchtxt": "考研", "searchsubmit": "true", "page": "2"}
resp2 = SESSION.post(f"{BASE}/search.php?mod=forum&searchsubmit=yes",
                     data=data, timeout=15)
resp2.encoding = "utf-8"
soup = BeautifulSoup(resp2.text, "html.parser")
page2 = []
for container in soup.select(".pbw, li.bbda, table[id^=thread_], li[id^=thread], dl.bbm, li.pbw"):
    try:
        a = container.select_one("a.xst, a.s, h3 a, a[href*='tid=']")
        if a:
            m2 = re.search(r"tid=(\d+)", a.get("href", ""))
            if m2:
                page2.append(m2.group(1))
    except:
        continue
print(f"  第2页: {len(page2)} 条")
print(f"  与第1页重复: {len(set(p2 for p2 in page2 if p2 in [i['tid'] for i in page1]))} 条")

# 目录访问尝试
print("\n" + "=" * 60)
print("  目录/导航页访问")
print("=" * 60)
for path in ["/forum.php", "/forum.php?gid=1", "/guide.php", "/misc.php?mod=stat"]:
    wait(1)
    try:
        r = get(f"{BASE}{path}")
        print(f"  {path}: HTTP {r.status_code} | {round(len(r.text)/1024,1)}KB")
    except Exception as e:
        print(f"  {path}: ❌ {e}")

print("\n" + "=" * 60)
print("  验证完成")
print("=" * 60)
