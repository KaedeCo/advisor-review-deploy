"""查看小木虫搜索结果原始HTML"""
import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

r = requests.get(
    "https://muchong.com/bbs/search.php?searchsubmit=yes&wd=导师&fid=0",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
    timeout=20
)
r.encoding = "gbk"

# 保存原始HTML
with open("c:/Users/32611/CodeBuddy/advisor-review-platform-main/tests/muchong_search.html", "w", encoding="utf-8") as f:
    f.write(r.text)

# 查找所有链接模式
import re
all_hrefs = set()
for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text):
    href = m.group(1)
    if len(href) > 10:
        all_hrefs.add(href)

print(f"唯一链接数: {len(all_hrefs)}")
patterns = {}
for h in sorted(all_hrefs):
    # 分类
    if "viewthread" in h or "tid=" in h:
        k = "帖子详情"
    elif "forumdisplay" in h or "fid=" in h:
        k = "版块列表"
    elif "space" in h or "uid=" in h:
        k = "用户空间"
    elif "thread-" in h:
        k = "帖子(rewrite)"
    elif "forum-" in h:
        k = "版块(rewrite)"
    elif "http" in h and "muchong.com" in h:
        k = "本站URL"
    else:
        k = "其他"
    patterns.setdefault(k, []).append(h)

for k, urls in sorted(patterns.items()):
    print(f"\n{k} ({len(urls)}):")
    for u in urls[:5]:
        print(f"  {u[:100]}")

print(f"\n响应大小: {len(r.text)} bytes")
