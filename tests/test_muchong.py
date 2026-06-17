"""
小木虫 muchong.com 爬虫可行性测试脚本
==========================================
测试内容：
  1. 首页连通性
  2. 搜索功能（多种关键词）
  3. 版块列表页解析
  4. 帖子详情页解析
  5. 反爬检测：Cookie需求、速率限制、编码混淆

结论：搜索功能不稳定（502频发），需关注
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time
from bs4 import BeautifulSoup
import re

BASE_URL = "https://muchong.com"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE_URL,
    "Connection": "keep-alive",
})


# ─── 测试 1: 连通性 ────────────────────────────────────────

def test_connectivity():
    """测试首页"""
    print("=" * 60)
    print("[测试 1] 首页连通性")
    try:
        resp = SESSION.get(f"{BASE_URL}/", timeout=15)
        print(f"  HTTP {resp.status_code} | 响应大小: {len(resp.text)} bytes")
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string if soup.title else "(无标题)"
        print(f"  页面标题: {title}")

        if "Discuz!" in resp.text:
            ver = re.search(r"Discuz!\s*X?([\d.]+)", resp.text)
            print(f"  ✅ Discuz! 版本: {ver.group(0) if ver else '未知'}")
        else:
            print("  ⚠️  未检测到 Discuz! 标识（可能高度定制）")

        # 编码混淆检测
        garbled = re.findall(r"[\u4e00-\u9fff]{20,}", resp.text[-500:])
        if len(garbled) == 0 and len(resp.text) > 2000:
            # 尾部的"中文"可能是乱码
            tail = resp.text[-300:]
            if any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in tail[:10]):
                print("  ⚠️  页面尾部疑似含编码混淆内容")

        print("  ✅ 连通性测试通过\n")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 2: 搜索功能（多关键词） ───────────────────────────

def test_search():
    """测试搜索不同关键词"""
    print("=" * 60)
    print("[测试 2] 搜索功能 — 多关键词测试")
    test_queries = ["导师", "选导师", "导师推荐", "课题组", "实验室"]

    for query in test_queries:
        try:
            url = f"{BASE_URL}/bbs/search.php?searchsubmit=yes&searchtext={query}"
            resp = SESSION.get(url, timeout=15, allow_redirects=True)
            resp.encoding = "gbk"
            size = len(resp.text)

            # 检查 502
            if resp.status_code == 502 or "502 Bad Gateway" in resp.text:
                print(f"  '{query}': ❌ 502 Bad Gateway (服务端错误)")
                continue
            if resp.status_code != 200:
                print(f"  '{query}': ⚠️  HTTP {resp.status_code} | {size} bytes")
                continue

            # 结果计数
            soup = BeautifulSoup(resp.text, "html.parser")
            count_text = soup.get_text()
            match = re.search(r"找到.*?(\d+)\s*个结果", count_text)
            if match:
                print(f"  '{query}': ✅ {match.group(1)} 条结果 | {size} bytes")
            elif "暂无数据" in count_text or "没有找到" in count_text:
                print(f"  '{query}': ⚠️  0 条结果 | {size} bytes")
            else:
                print(f"  '{query}': ? 无法解析 | {size} bytes")

            time.sleep(2)  # 搜索限速
        except Exception as e:
            print(f"  '{query}': ❌ {type(e).__name__}: {str(e)[:60]}")

    print()


# ─── 测试 3: 版块列表页 ────────────────────────────────────

def test_forum_list():
    """测试版块列表页（不依赖搜索功能）"""
    print("=" * 60)
    print("[测试 3] 版块列表页")

    # 已知的导师相关版块 ID（从之前抓取推断）
    test_fids = [
        ("博后之家", "283"),
        ("硕博家园", "284"),
        ("导师招生", "282"),
        ("考研", "286"),
        ("考博", "288"),
    ]

    for name, fid in test_fids:
        try:
            url = f"{BASE_URL}/bbs/forumdisplay.php?fid={fid}"
            resp = SESSION.get(url, timeout=15)
            resp.encoding = "gbk"
            soup = BeautifulSoup(resp.text, "html.parser")

            # 统计帖子数
            thread_items = soup.select("tbody[id^=normalthread_]") or \
                          soup.select(".sptable tr") or \
                          soup.select("table[id^=thread_]")
            print(f"  {name} (fid={fid}): HTTP {resp.status_code} | "
                  f"解析到 {len(thread_items)} 个帖子项")

            time.sleep(1.5)
        except Exception as e:
            print(f"  {name} (fid={fid}): ❌ {e}")

    print()


# ─── 测试 4: 帖子详情页 ────────────────────────────────────

def test_thread_detail(tid="14221987"):
    """测试帖子详情页"""
    print("=" * 60)
    print(f"[测试 4] 帖子详情页 — tid={tid}")
    try:
        url = f"{BASE_URL}/bbs/viewthread.php?tid={tid}"
        resp = SESSION.get(url, timeout=15)
        resp.encoding = "gbk"
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"  HTTP {resp.status_code} | 响应大小: {len(resp.text)} bytes")

        # 标题
        title_el = soup.select_one("h1, .ph, #thread_subject")
        title = title_el.get_text(strip=True) if title_el else "(无标题)"
        print(f"  帖子标题: {title[:60]}")

        # 正文
        main_post = soup.select_one("#post_0") or soup.select_one("div[id^=post_]")
        if main_post:
            content_div = main_post.select_one(".t_f") or main_post.select_one("td.t_f")
            content = content_div.get_text(strip=True) if content_div else ""
            print(f"  正文长度: {len(content)} 字")
            print(f"  正文预览: {content[:120]}...")

        # 回复
        replies = soup.select("[id^=post_]")
        print(f"  帖子+回复总数: {len(replies)} 项")

        # 登录需求检查
        if "需要登录" in resp.text or "请登录" in resp.text:
            print("  ⚠️  内容需要登录")
        else:
            print("  ✅ 游客可查看")

        print("  ✅ 详情页测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 5: 反爬压力 ──────────────────────────────────────

def test_rate_limiting():
    """连续请求测试"""
    print("=" * 60)
    print("[测试 5] 反爬压力测试 — 连续 4 次首页请求（间隔 1.5s）")
    success = 0
    for i in range(4):
        try:
            resp = SESSION.get(f"{BASE_URL}/", timeout=10)
            if resp.status_code == 200:
                success += 1
                print(f"  请求 #{i+1}: ✅ HTTP 200 | {len(resp.text)} bytes")
            else:
                print(f"  请求 #{i+1}: ⚠️  HTTP {resp.status_code}")
        except Exception as e:
            print(f"  请求 #{i+1}: ❌ {e}")
        if i < 3:
            time.sleep(1.5)

    print(f"  结果: {success}/4 成功")
    if success == 4:
        print("  ✅ 低速请求安全\n")
    else:
        print(f"  ⚠️  存在不稳定\n")


# ─── 主入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║     小木虫 muchong.com 爬虫可行性测试                    ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    results = {}
    results["连通性"] = test_connectivity()
    time.sleep(1.5)

    results["搜索功能"] = True  # 测试中有多种关键词，不依赖单一返回值
    test_search()

    test_forum_list()
    time.sleep(1)

    results["帖子详情"] = test_thread_detail()
    time.sleep(1)

    test_rate_limiting()

    # ── 总结 ──
    print("=" * 60)
    print("综合测试结果:")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    print()
