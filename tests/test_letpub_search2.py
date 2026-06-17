"""测试 LetPub 搜索 - 带 searchsubmit=true"""
import requests
from bs4 import BeautifulSoup
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "https://www.letpub.com.cn"
sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": f"{BASE}/index.php?page=grant",
})

# 先访问搜索页
sess.get(f"{BASE}/index.php?page=grant", timeout=15)

# 搜索参数（模拟表单提交）
params = {
    "page": "grant",
    "name": "张三",
    "person": "张三",
    "searchsubmit": "true",
}

print("[1] GET 搜索 with searchsubmit=true")
r = sess.get(f"{BASE}/index.php", params=params, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")
soup = BeautifulSoup(r.text, "html.parser")
table = soup.find("table", id="keyword-datalist")
if table:
    rows = table.select("tbody tr")
    print(f"   表格行: {len(rows)}")
    for row in rows[:3]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        print(f"     {cells[:6]}")
else:
    print("   无 keyword-datalist 表格")

# 2. 检查是否需要登录
print("\n[2] 检查登录状态")
if "请先登录" in r.text or "您尚未登录" in r.text:
    print("   ⚠️ 需要登录")
elif "onlinecheck" in r.text:
    print("   含 onlinecheck（登录检查）")

# 3. 测试一个真实有基金的人（如知名的）
print("\n[3] 搜索知名导师")
for name in ["施一公", "饶毅", "曹雪涛"]:
    params["person"] = name
    params["name"] = name
    r = sess.get(f"{BASE}/index.php", params=params, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", id="keyword-datalist")
    rows = table.select("tbody tr") if table else []
    print(f"   {name}: {len(rows)} 行 | {len(r.text)} bytes")
    if rows:
        for row in rows[:2]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            print(f"     {cells[:5]}")
        break

# 4. 检查是否有 content/index.php?action=onlinecheck 这个端点
print("\n[4] 测试 onlinecheck 端点")
r = sess.get(f"{BASE}/content/index.php?action=onlinecheck", timeout=10)
print(f"   HTTP {r.status_code} | {r.text[:200]}")
