"""调试 daoshipingjia 导师名提取"""
import sys, io, requests, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

r = requests.get(
    "https://daoshipingjia.net/schools/%E6%B8%85%E5%8D%8E%E5%A4%A7%E5%AD%A6/%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%A7%91%E5%AD%A6%E4%B8%8E%E6%8A%80%E6%9C%AF%E7%B3%BB",
    headers={"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"},
    timeout=15,
)
soup = BeautifulSoup(r.text, "html.parser")

print("=== /teacher/ 链接 ===")
for a in soup.find_all("a", href=re.compile(r"/teacher/\d+")):
    raw = a.get_text(strip=True)
    href = a["href"]
    tid = re.search(r"/teacher/(\d+)", href).group(1)
    # 展示原始和清理后
    cleaned = re.sub(r"[\d.]+|updated:|[\d]{4}\.[\d]{2}", "", raw).strip()
    print(f"  raw='{raw[:80]}'")
    print(f"  cleaned='{cleaned}'")
    print(f"  tid={tid}")
    if cleaned != raw and len(cleaned) < 2:
        print(f"  ❌ 被过度清理!")
    print()
