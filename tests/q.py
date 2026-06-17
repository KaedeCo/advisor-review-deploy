"""快速验证"""
import sys, io, requests, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"})

# 1. 搜索验证 - 获取帖子链接
print("=== 搜索'导师评价' ===")
r = S.get("https://muchong.com/bbs/search.php?searchsubmit=yes&wd=导师评价&fid=0&order=2", timeout=20)
r.encoding = "gbk"
soup = BeautifulSoup(r.text, "html.parser")

# 查找 t-XXX-X 格式链接
t_links = soup.find_all("a", href=re.compile(r"/t-\d+-\d+"))
print(f"t-tid-page 链接: {len(t_links)} 个")
for a in t_links[:5]:
    text = a.get_text(strip=True)
    if len(text) > 3:
        href = a["href"]
        m = re.search(r"/t-(\d+)-\d+", href)
        tid = m.group(1) if m else "?"
        # 全URL
        full = "https://muchong.com" + href if href.startswith("/") else href
        print(f"  t-{tid} [{text[:50]}]")
        print(f"    {full[:80]}")
        print()

# 2. 测试详情页
print("\n=== 测试详情页 t-14221987-1 ===")
try:
    r2 = S.get("https://muchong.com/t-14221987-1", timeout=20)
    r2.encoding = "gbk"
    soup2 = BeautifulSoup(r2.text, "html.parser")
    print(f"  HTTP {r2.status_code} | {len(r2.text)} bytes")

    # 标题
    for sel in ["h1", ".ph", "title", ".thread_subject"]:
        el = soup2.select_one(sel)
        if el:
            print(f"  标题({sel}): {el.get_text(strip=True)[:60]}")
            break

    # 正文
    for sel in ["td.t_f", ".t_f", ".pct", ".message", "div[class*='t_f']"]:
        items = soup2.select(sel)
        if items:
            text = items[0].get_text(" ", strip=True)[:120]
            print(f"  正文({sel}): {text}")

    # 总帖子数
    posts = soup2.select("[id^=pid]") or soup2.select("[id^=post_]")
    print(f"  帖子数: {len(posts)}")

except Exception as e:
    print(f"  ❌ {type(e).__name__}: {e}")

# 3. 版块列表 fid=282
print("\n=== 版块列表 fid=282 ===")
try:
    r3 = S.get("https://muchong.com/bbs/forumdisplay.php?fid=282", timeout=20)
    r3.encoding = "gbk"
    soup3 = BeautifulSoup(r3.text, "html.parser")
    t_links3 = soup3.find_all("a", href=re.compile(r"/t-\d+-\d+"))
    print(f"  t-link: {len(t_links3)} 个, 样本: {[a.get_text(strip=True)[:30] for a in t_links3[:3] if len(a.get_text(strip=True))>3]}")
except Exception as e:
    print(f"  ❌ {e}")
