"""调试搜索结果的版块链接"""
import sys, io, requests, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

r = requests.get(
    "https://www.eeban.com/search.php?mod=forum&searchsubmit=yes&srchtxt=苏州大学",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
    timeout=15,
)
soup = BeautifulSoup(r.text, "html.parser")

# 找到第一个结果项
items = soup.select("li[id^=thread]") or soup.select("li.pbw")
print(f"结果项数: {len(items)}")

if items:
    first = items[0]
    # 打印所有链接
    all_links = first.select("a")
    print(f"\n第一个结果中的链接 ({len(all_links)} 个):")
    for link in all_links:
        href = link.get("href", "")
        text = link.get_text(strip=True)[:30]
        if not href:
            continue
        # 分类
        if "tid=" in href:
            kind = "帖子链接"
        elif "fid=" in href or "forumdisplay" in href:
            kind = ">>> 版块链接 <<<"
        elif "uid=" in href or "space" in href:
            kind = "用户链接"
        else:
            kind = "其他"
        print(f"  [{kind}] {text:15s} → {href[:80]}")

    # 打印完整 HTML 片段（截取）
    print(f"\n完整HTML片段 (前600字):")
    print(first.prettify()[:600])
