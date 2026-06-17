"""调试保研论坛帖子详情页 HTML 结构"""
import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://www.eeban.com/forum.php?mod=viewthread&tid=250330",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
)
soup = BeautifulSoup(r.text, "html.parser")

print("=== 主帖选择器探测 ===")
selectors = [
    "#post_0", "#post_0 .t_f", "#post_0 td.t_f",
    "div.t_f", "table[id^=post]", ".plc", "div[id^=post]",
    ".pct", ".pcb", "td.t_f", "#thread_subject",
    ".t_f", ".postmessage", ".message",
]
for s in selectors:
    items = soup.select(s)
    if items:
        print(f"  {s}: {len(items)} hits  sample={items[0].get_text()[:60]}")
    else:
        print(f"  {s}: 0 hits")

print("\n=== id 以 post 开头的元素 ===")
posts = [e for e in soup.select("[id]") if e["id"].startswith("post")]
print(f"  找到 {len(posts)} 个")
for p in posts[:3]:
    cls = p.get("class", [])
    print(f"  id={p['id']} class={cls} text_preview={p.get_text()[:80]}")

print("\n=== 查找包含 'Orca' 的元素 ===")
orca = soup.find_all(string=lambda t: t and "Orca" in t)
print(f"  找到 {len(orca)} 个")
for o in orca[:2]:
    parent = o.parent
    print(f"  text={o[:60]} parent_tag={parent.name} parent_class={parent.get('class','')}")

print("\n=== 任意 td 带 t_f 类 ===")
tfs = soup.select("td.t_f")
print(f"  找到 {len(tfs)} 个 td.t_f")
for tf in tfs[:3]:
    print(f"  text={tf.get_text()[:100]}")

print("\n=== 检查是否有登录拦截 ===")
if "需要登录" in r.text or "请登录" in r.text:
    print("  WARNING: 页面要求登录!")

print("\n=== 响应摘要 ===")
print(f"  HTTP {r.status_code} | {len(r.text)} bytes | charset={r.encoding}")
