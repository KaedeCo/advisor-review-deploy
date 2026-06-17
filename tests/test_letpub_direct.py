"""直接用 requests POST nsfcfund_search.php — 绕过 Playwright"""
import requests
from bs4 import BeautifulSoup
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PHPSESSID = "0qhq7gqfs39sc0kli3c923t275"
ADVISOR = "刘玉身"
UNIVERSITY = "清华大学"

BASE = "https://www.letpub.com.cn"
SEARCH_URL = f"{BASE}/index.php?page=grant"
AJAX_URL = f"{BASE}/nsfcfund_search.php"

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": SEARCH_URL,
    "X-Requested-With": "XMLHttpRequest",
})

# 1. 先访问搜索页获取初始 Cookie
print("[1] 访问搜索页...")
r = sess.get(SEARCH_URL, cookies={"PHPSESSID": PHPSESSID}, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")

# 检查登录状态
if "退出" in r.text or "个人中心" in r.text:
    print("   登录状态: 已登录")
else:
    print("   登录状态: 未登录")

# 2. 直接 POST 搜索
print(f"\n[2] POST nsfcfund_search.php...")
data = {
    "page": "",
    "name": "",
    "person": ADVISOR,
    "no": "",
    "company": UNIVERSITY,
    "addcomment_s1": "",
    "addcomment_s2": "",
    "addcomment_s3": "",
    "addcomment_s4": "",
    "money1": "",
    "money2": "",
    "startTime": "1997",
    "endTime": "2023",
    "subcategory": "",
    "province_main": "",
    "searchsubmit": "true",
}

r = sess.post(
    f"{AJAX_URL}?mode=advanced&datakind=list&currentpage=1",
    data=data,
    cookies={"PHPSESSID": PHPSESSID},
    timeout=15,
)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")

# 检查记录数
m = re.search(r"匹配[：:]\s*<b>(\d+)</b>条", r.text)
if m:
    print(f"   匹配记录数: {m.group(1)}")

# 解析表格
soup = BeautifulSoup(r.text, "lxml")
table = soup.find("table", id="keyword-datalist")
print(f"   Table found: {table is not None}")

if table:
    rows = table.find_all("tr")
    print(f"   总行数: {len(rows)}")

    # 表头
    ths = table.find_all("th")
    if ths:
        headers = [th.get_text(strip=True) for th in ths]
        print(f"   表头: {headers}")

    # 数据行
    data_rows = [row for row in rows if row.find_all("td") and not row.find_all("th")]
    print(f"   数据行: {len(data_rows)}")

    for i, row in enumerate(data_rows[:5]):
        tds = row.find_all("td")
        texts = [td.get_text(strip=True)[:30] for td in tds]
        print(f"   行{i+1}: {texts}")
else:
    # 找所有表格
    tables = soup.find_all("table")
    print(f"   其他表格: {len(tables)}")
    for t in tables[:3]:
        print(f"     id={t.get('id','')} rows={len(t.find_all('tr'))}")

    # 打印响应片段
    print(f"\n   响应前500字: {r.text[:500]}")
