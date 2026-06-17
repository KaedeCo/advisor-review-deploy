"""提取小木虫搜索结果中的帖子链接"""
import sys, io, requests, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

r = requests.get(
    "https://muchong.com/bbs/search.php?searchsubmit=yes&wd=导师&fid=0",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
    timeout=20
)
r.encoding = "gbk"
soup = BeautifulSoup(r.text, "html.parser")

# 提取所有包含 tid= 的链接
links = soup.find_all("a", href=re.compile("tid="))
print(f"含 tid= 的链接: {len(links)} 个\n")
for a in links[:15]:
    text = a.get_text(strip=True)
    if len(text) > 3:
        href = a["href"]
        # 可能是完整URL或相对路径
        if href.startswith("/"):
            href = "https://muchong.com" + href
        print(f"  [{text[:50]}]")
        print(f"    href={href[:80]}")
        # 显示父级标签信息
        parent = a.parent
        inner = ""
        if parent:
            inner = parent.get_text(" ", strip=True)[:60]
        print(f"    parent_info={inner}")
        print()

# 也找一下版块列表页的链接
print("\n=== 版块列表 fid=282 ===")
r2 = requests.get(
    "https://muchong.com/bbs/forumdisplay.php?fid=282",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
    timeout=20
)
r2.encoding = "gbk"
soup2 = BeautifulSoup(r2.text, "html.parser")
links2 = soup2.find_all("a", href=re.compile("tid="))
print(f"版块列表含 tid= 的链接: {len(links2)} 个")
for a in links2[:5]:
    text = a.get_text(strip=True)
    if len(text) > 5:
        print(f"  [{text[:60]}] → {a['href'][:80]}")
