"""测试：requests + Cookie 直接搜索 LetPub NSFC"""
import requests
from bs4 import BeautifulSoup
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "https://www.letpub.com.cn"
SEARCH_URL = f"{BASE}/index.php?page=grant"

# 模拟浏览器
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": SEARCH_URL,
}

# 创建 Session
sess = requests.Session()
sess.headers.update(headers)

# 1. 先访问首页（获取 PHPSESSID）
print("[1] 访问首页获取 Cookie")
r = sess.get(BASE, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")
cookies = sess.cookies.get_dict()
print(f"   Cookies: {list(cookies.keys())}")
phpsessid = cookies.get("PHPSESSID", "")
print(f"   PHPSESSID: {phpsessid}")

# 2. 访问搜索页
print("\n[2] 访问搜索页")
r = sess.get(SEARCH_URL, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")
print(f"   Title: ", end="")
soup = BeautifulSoup(r.text, "html.parser")
print(soup.title.string if soup.title else "N/A")

# 检查页面是否有搜索表单
has_person = 'name="person"' in r.text
has_checksubmit = 'checksubmit' in r.text
print(f"   搜索表单: {has_person}")
print(f"   checksubmit函数: {has_checksubmit}")

# 3. 尝试直接构造搜索请求
# LetPub 搜索通过 JS 调用 checksubmit('advanced', 'list', 1)
# 这个函数实际发送的请求是什么？
# 从页面源码找 checksubmit 函数定义
m = re.search(r'function\s+checksubmit\s*\([^)]*\)\s*\{([^}]+)\}', r.text)
if m:
    print(f"\n[3] checksubmit 函数体: {m.group(1)[:300]}")
else:
    # 找其他 JS 中的提交逻辑
    print("\n[3] 未找到 checksubmit 函数定义，尝试分析表单 action")
    forms = soup.find_all("form")
    for i, form in enumerate(forms):
        action = form.get("action", "")
        method = form.get("method", "")
        inputs = form.find_all("input")
        visible_inputs = [inp for inp in inputs if inp.get("name")]
        if visible_inputs:
            print(f"   Form #{i}: {method} -> {action}")
            for inp in visible_inputs[:8]:
                print(f"     {inp.get('name')} = {inp.get('value', '')[:30]}")

# 4. 直接尝试 GET 搜索
print("\n[4] 直接 GET 搜索 (person=张三)")
params = {"page": "grant", "name": "张三", "person": "张三"}
r = sess.get(f"{BASE}/index.php", params=params, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")
has_datalist = "keyword-datalist" in r.text
has_rows = r.text.count("<tr") > 5
print(f"   含 keyword-datalist: {has_datalist}")
print(f"   含表格行: {has_rows}")

# 5. 尝试 POST 搜索
print("\n[5] POST 搜索 (person=张三)")
data = {"person": "张三", "name": "张三", "Search": "Search"}
r = sess.post(f"{BASE}/index.php?page=grant", data=data, timeout=15)
print(f"   HTTP {r.status_code} | {len(r.text)} bytes")
has_datalist = "keyword-datalist" in r.text
print(f"   含 keyword-datalist: {has_datalist}")
# 检查是否有数据行
soup = BeautifulSoup(r.text, "html.parser")
table = soup.find("table", id="keyword-datalist")
if table:
    rows = table.select("tbody tr")
    print(f"   表格数据行: {len(rows)}")
    for row in rows[:3]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        print(f"     {cells[:5]}")
else:
    # 检查是否需要登录
    if "登录" in r.text and "注册" in r.text:
        print("   ⚠️ 页面显示登录/注册提示，可能需要登录")
    # 搜索是否有错误提示
    errors = soup.select(".error, .alert, .msg, [class*='error']")
    for e in errors[:3]:
        print(f"   错误: {e.get_text(strip=True)[:100]}")

print("\n[6] 尝试分析 checksubmit 实际提交的 URL")
# 搜索 JS 代码中的 ajax 或 submit
js_blocks = re.findall(r'(?:ajax|submit|fetch|XMLHttp)[^;]{0,200}', r.text[:50000], re.I)
for j in js_blocks[:5]:
    print(f"   JS: {j[:150]}")
