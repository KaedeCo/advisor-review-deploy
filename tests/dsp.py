"""调试 daoshipingjia.net HTML 结构"""
import sys, io, requests, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

r = requests.get("https://daoshipingjia.net/schools",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
    timeout=15)
soup = BeautifulSoup(r.text, "html.parser")

# 保存HTML供分析
with open("c:/Users/32611/CodeBuddy/advisor-review-platform-main/tests/dsp_schools.html", "w", encoding="utf-8") as f:
    f.write(r.text)

# 查找所有链接
print("=== 学校链接 ===")
for a in soup.find_all("a", href=re.compile(r"/schools/")):
    href = a["href"]
    text = a.get_text(strip=True)
    if href.count("/") >= 2 and text and len(text) > 1 and len(text) < 20:
        # 可能包含评分的父级
        p = a.parent
        for _ in range(4):
            p = p.parent if p else None
            if not p: break
            score_m = re.search(r"(\d+\.\d+)", p.get_text(" ", strip=True))
            if score_m:
                print(f"  {text:15s} {score_m.group(1):>4s}  → {href}")
                break

print("\n=== 所有学校的href模式 ===")
school_hrefs = set()
for a in soup.find_all("a", href=re.compile(r"/schools/")):
    href = a["href"]
    if href.count("/") >= 2:
        school_hrefs.add(href)
for h in sorted(school_hrefs)[:20]:
    print(f"  {h}")

print(f"\n=== 页面总链接数: {len(soup.find_all('a'))} ===")
print(f"  含/schools/的: {len([a for a in soup.find_all('a', href=re.compile(r'/schools/'))])}")
print(f"  含/teacher/的: {len([a for a in soup.find_all('a', href=re.compile(r'/teacher/'))])}")
