"""
小木虫 muchong.com 搜索机制 + Cookie 探测脚本
================================================
使用方式（安全：不需要密码）:
  1. 用浏览器登录 https://muchong.com
  2. F12 → Application → Cookies → muchong.com
  3. 复制完整 Cookie 字符串（一条文本）
  4. 粘贴到下方 MUCHONG_COOKIE 变量
  5. 运行此脚本

未设置 Cookie 则以游客模式测试（预期搜索返回 0 结果）
"""

import sys
import io
import re
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
import json
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════════════════════
# 配置区：粘贴浏览器 Cookie 到此处
# ═══════════════════════════════════════════════════════════════

MUCHONG_COOKIE = ""  # ← 从浏览器 F12 粘贴到这里

# ═══════════════════════════════════════════════════════════════

BASE = "https://muchong.com/bbs"
S = requests.Session()
S.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://muchong.com/",
})

if MUCHONG_COOKIE.strip():
    for item in MUCHONG_COOKIE.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            S.cookies.set(k.strip(), v.strip())
    print("[Cookie] 已加载浏览器 Cookie (%d 项)\n" % len(MUCHONG_COOKIE.split(";")))
else:
    print("[Cookie] 无 Cookie，以游客模式测试\n")


def search(keyword: str, fid: str = "0") -> dict:
    """搜索并返回 (状态码, 结果数, HTML大小)"""
    params = {
        "searchsubmit": "yes",
        "wd": keyword,
        "fid": fid,
        "search_type": "",
        "order": "2",  # 相关度排序
    }
    url = f"{BASE}/search.php"
    # 编码问题：小木虫用 gbk，requests 默认会 URL-encode
    resp = S.get(url, params=params, timeout=15)
    resp.encoding = "gbk"

    # 搜索结果计数
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    # 多种匹配模式
    count = None
    for pat in [
        r"找到.*?(\d+)\s*个相关话题",
        r"共搜索到\s*(\d+)\s*个",
        r"(\d+)\s*个相关",
        r"相关话题\s*(\d+)",
    ]:
        m = re.search(pat, text)
        if m:
            count = int(m.group(1))
            break

    # 解析帖子条目数
    items = soup.select("tbody[id^=normalthread_]") or \
            soup.select(".tl tr") or \
            soup.select("table[id^=thread_]")

    return {
        "status": resp.status_code,
        "size": len(resp.text),
        "count": count,
        "threads_found": len(items),
        "has_login_prompt": "请登录" in text or "需要登录" in text,
        "text_preview": text[:200],
    }


def test_board_list():
    """测试版块列表页"""
    print("=" * 60)
    print("[探测] 版块列表页（不依赖搜索）")

    # 已知有效版块
    boards = [
        ("导师招生", "282"),
        ("硕博家园", "284"),
        ("博后之家", "283"),
        ("考研", "286"),
        ("考博", "288"),
    ]

    for name, fid in boards:
        try:
            url = f"{BASE}/forumdisplay.php?fid={fid}"
            resp = S.get(url, timeout=15)
            resp.encoding = "gbk"
            soup = BeautifulSoup(resp.text, "html.parser")

            # 解析帖子
            items = (soup.select("tbody[id^=normalthread_]") or
                     soup.select("tr[id^=td_thread]") or
                     soup.select("[id^=thread_]"))
            threads = len(items)

            # 提取标题样本
            titles = []
            for item in items[:3]:
                title_el = item.select_one("a[href*='tid='], a.s.xst, th a")
                if title_el:
                    titles.append(title_el.get_text(strip=True)[:50])

            print(f"  fid={fid} {name:8s} HTTP {resp.status_code} | "
                  f"帖子: {threads} 条 | 样本: {titles[:2]}")

        except Exception as e:
            print(f"  fid={fid} {name:8s} ❌ {e}")

        time.sleep(1.5)
    print()


def test_search_multi():
    """多关键词搜索测试"""
    print("=" * 60)
    print("[探测] 搜索功能 — 多关键词")

    keywords = [
        "导师",       # 中文短词
        "导师评价",    # 中文长词
        "test",       # 英文（对比）
        "985",        # 数字（对比）
        "张",         # 单字
    ]

    mode = "登录态" if MUCHONG_COOKIE.strip() else "游客"
    print(f"当前模式: {mode}\n")

    for kw in keywords:
        result = search(kw)
        icon = "✅" if result["count"] and result["count"] > 0 else "❌"
        if result["has_login_prompt"]:
            icon = "🔒"
        print(f"  {icon} '{kw:8s}' HTTP {result['status']} | "
              f"结果: {result['count']} 条 | "
              f"帖子项: {result['threads_found']} | "
              f"大小: {result['size']}B")
        time.sleep(2)
    print()


def test_search_with_params():
    """测试不同参数组合"""
    print("=" * 60)
    print("[探测] 搜索参数组合 — 关键词 '导师'")

    test_cases = [
        # (描述, 参数字典)
        ("GET wd", {"searchsubmit": "yes", "wd": "导师"}),
        ("GET wd+fid=0", {"searchsubmit": "yes", "wd": "导师", "fid": "0"}),
        ("GET no wd", {"searchsubmit": "yes", "fid": "0"}),
        ("GET gbk encoded", None),  # 手动 URL 编码
    ]

    for desc, params in test_cases:
        if params is None:
            # 手动 gbk 编码
            import urllib.parse
            encoded = urllib.parse.quote("导师", encoding="gbk")
            url = f"{BASE}/search.php?searchsubmit=yes&wd={encoded}"
            resp = S.get(url, timeout=15)
        else:
            resp = S.get(f"{BASE}/search.php", params=params, timeout=15)

        resp.encoding = "gbk"
        size = len(resp.text)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        has_count = any(re.findall(r"(\d+)\s*个相关", text))
        has_nodata = "暂无数据" in text or "没有找到" in text
        has_login = "请登录" in text

        status = "空页" if size < 5000 else \
                 ("无数据" if has_nodata else \
                  ("有结果" if has_count else \
                   ("需登录" if has_login else "未知")))

        print(f"  {desc:20s} HTTP {resp.status_code} | "
              f"{size}B | {status} | 登录提示: {has_login}")
        time.sleep(1.5)
    print()


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║    小木虫搜索机制探测                                  ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    test_board_list()
    test_search_multi()
    test_search_with_params()

    # Cookie 状态总结
    print("=" * 60)
    print("[总结] Cookie 状态:")
    if MUCHONG_COOKIE.strip():
        for c in S.cookies:
            print(f"  {c.name} = {c.value[:20]}..."
                  if len(c.value) > 20 else f"  {c.name} = {c.value}")
    else:
        print("  无 Cookie（游客模式）")

    print("\n💡 如果搜索返回 0 结果，请:")
    print("  1. 浏览器登录 muchong.com")
    print("  2. F12 → Application → Cookies → 复制 Cookie 文本")
    print("  3. 粘贴到本脚本 MUCHONG_COOKIE 变量")
    print("  4. 重新运行")
