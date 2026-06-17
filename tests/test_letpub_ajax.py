"""深挖 LetPub 搜索 AJAX 端点"""
import requests
from bs4 import BeautifulSoup
import re
import sys
import io
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "https://www.letpub.com.cn"
SEARCH_URL = f"{BASE}/index.php?page=grant"

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": SEARCH_URL,
})

# 访问搜索页
r = sess.get(SEARCH_URL, timeout=15)
html = r.text

# 1. 找所有 JS 文件
print("[1] JS 文件")
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
for j in js_files[:10]:
    print(f"   {j}")

# 2. 找 checksubmit 完整定义（跨行）
print("\n[2] checksubmit 完整定义")
# 用更宽松的正则
m = re.search(r'function\s+checksubmit\s*\([^)]*\)\s*\{(.*?)\n\}', html, re.S)
if m:
    print(m.group(1)[:800])
else:
    # 找所有包含 checksubmit 的行
    lines = html.split("\n")
    for i, line in enumerate(lines):
        if "checksubmit" in line and "function" in line:
            # 打印该行和后续 20 行
            print(f"Line {i}: {line.strip()[:200]}")
            for j in range(1, 25):
                if i + j < len(lines):
                    print(f"  +{j}: {lines[i+j].strip()[:200]}")
            break

# 3. 找 AJAX 调用
print("\n[3] AJAX 调用 (ajax/fetch)")
ajax_patterns = [
    r'\$\.ajax\s*\(\s*\{([^}]+)\}',
    r'\$\.post\s*\(([^)]+)\)',
    r'\$\.get\s*\(([^)]+)\)',
    r'fetch\s*\(([^)]+)\)',
]
for pat in ajax_patterns:
    matches = re.findall(pat, html, re.S)
    for m in matches[:3]:
        print(f"   {pat[:20]}: {m[:300]}")

# 4. 找搜索表单的隐藏字段和 action
print("\n[4] 搜索表单分析")
soup = BeautifulSoup(html, "html.parser")
# 找包含 person 输入框的表单
person_input = soup.find("input", {"name": "person"})
if person_input:
    form = person_input.find_parent("form")
    if form:
        print(f"   Form action: {form.get('action', 'N/A')}")
        print(f"   Form method: {form.get('method', 'N/A')}")
        print(f"   Form id: {form.get('id', 'N/A')}")
        # 所有输入字段
        for inp in form.find_all("input"):
            name = inp.get("name", "")
            val = inp.get("value", "")
            ty = inp.get("type", "")
            if name or ty == "submit":
                print(f"     {ty:8s} name={name:15s} value={val[:30]}")

# 5. 找 AJAX URL（可能在 JS 中是硬编码的）
print("\n[5] 可能的 AJAX URL")
url_patterns = re.findall(r'["\']([^"\']*(?:grant|search|list|query)[^"\']*)["\']', html, re.I)
for u in set(url_patterns[:15]):
    print(f"   {u}")

# 6. 直接测试一些可能的 AJAX 端点
print("\n[6] 测试可能的 AJAX 端点")
endpoints = [
    f"{BASE}/index.php?page=grant&name=张三&person=张三&first=1",
    f"{BASE}/index.php?page=grant&name=张三&person=张三&first=1&Search=",
    f"{BASE}/api/grant?name=张三",
    f"{BASE}/index.php?page=grant&search=1&name=张三",
]
for url in endpoints:
    try:
        r = sess.get(url, timeout=10)
        # 检查是否有实际数据行
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", id="keyword-datalist")
        rows = len(table.select("tbody tr")) if table else 0
        print(f"   {url[:80]}")
        print(f"     HTTP {r.status_code} | {len(r.text)}B | rows: {rows}")
    except Exception as e:
        print(f"   {url[:80]} → ERROR: {e}")
