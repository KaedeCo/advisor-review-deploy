"""探测小木虫搜索结果和版块列表的 HTML 结构"""
import sys, io, requests, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Accept": "text/html",
})

# ============ 搜索页 ============
print("=== 搜索页 HTML 结构 ===\n")

resp = S.get("https://muchong.com/bbs/search.php", params={
    "searchsubmit": "yes", "wd": "导师", "fid": "0", "order": "2"
}, timeout=15)
resp.encoding = "gbk"
soup = BeautifulSoup(resp.text, "html.parser")

# 查找所有可能的帖子容器
selectors = [
    "table[id^=thread_]", "tbody[id^=normalthread_]",
    "tr[id^=td_thread]", "[id^=thread]", ".tl tr",
    ".datatable tr", "table tr[class]",
    # 新版小木虫可能用的选择器
    "div.thread_item", "li.thread", ".post_list tr",
    "table[summary]", ".xst",  # Discuz! 经典
]
for sel in selectors:
    items = soup.select(sel)
    if items:
        sample = items[0].get_text(" ", strip=True)[:80]
        print(f"  {sel:30s} → {len(items)} 条 | 样本: {sample}")

# 手工搜索 "thread" 相关元素
print("\n--- 手工搜索 thread/tid 相关元素 ---")
for el in soup.select("[id*='thread'], [class*='thread'], a[href*='tid=']"):
    id_val = el.get("id", "")
    cls_val = " ".join(el.get("class", [])) if el.get("class") else ""
    href = el.get("href", "")
    text = el.get_text(strip=True)[:50]
    if "tid=" in href and len(text) > 3:
        print(f"  id={id_val:10s} class={cls_val:20s} text={text} → {href[:60]}")

# ============ 版块列表页 ============
print("\n\n=== 版块列表 HTML 结构 (fid=282 导师招生) ===\n")

resp2 = S.get("https://muchong.com/bbs/forumdisplay.php?fid=282", timeout=15)
resp2.encoding = "gbk"
soup2 = BeautifulSoup(resp2.text, "html.parser")

for sel in selectors:
    items = soup2.select(sel)
    if items:
        sample = items[0].get_text(" ", strip=True)[:80]
        print(f"  {sel:30s} → {len(items)} 条 | 样本: {sample}")

# 手工搜索
print("\n--- 手工搜索 thread/tid 相关元素 ---")
count = 0
for el in soup2.select("a[href*='tid=']"):
    text = el.get_text(strip=True)
    if len(text) > 5:
        href = el.get("href", "")
        print(f"  text={text[:60]} → {href[:80]}")
        count += 1
        if count >= 10:
            break

# ============ 帖子详情页 ============
print("\n\n=== 帖子详情页 (已知tid=14221987) ===\n")
resp3 = S.get("https://muchong.com/bbs/viewthread.php?tid=14221987", timeout=15)
resp3.encoding = "gbk"
soup3 = BeautifulSoup(resp3.text, "html.parser")

# 标题
title = soup3.select_one("h1, .ph, #thread_subject, .ts")
print(f"标题: {title.get_text(strip=True) if title else '?'}")

# 正文选择器
for sel in ["td.t_f", ".t_f", "#postlist .t_f", ".pct", ".pcb",
            "div[class*='content']", ".message", ".postmessage",
            "table td[class*='t_f']", "div[class*='t_f']"]:
    items = soup3.select(sel)
    if items:
        text = items[0].get_text(" ", strip=True)[:80]
        print(f"  正文选择器: {sel:30s} → {len(items)} 条 | {text}")

# 作者
for sel in [".authi a", ".xw1", "a[class*='xw']", "[class*='author'] a"]:
    items = soup3.select(sel)
    if items:
        print(f"  作者选择器: {sel:30s} → {len(items)} 条 | {items[0].get_text(strip=True)[:20]}")
