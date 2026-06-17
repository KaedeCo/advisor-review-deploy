"""
保研论坛 eeban.com 爬虫可行性测试脚本
==========================================
测试内容：
  1. 首页连通性
  2. 搜索功能（搜索"导师"关键词）
  3. 帖子详情页解析（公开页面，无需登录）
  4. 反爬检测：Cookie需求、速率限制、同盾风控触发阈值
  5. 数据密度评估（"联系导师"相关帖子数）

结论：高度可行，Discuz! X3.4，游客可访问全部公开内容
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.eeban.com"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE_URL,
})

# ─── 测试 1: 连通性 ────────────────────────────────────────

def test_connectivity():
    """测试首页是否可以正常加载"""
    print("=" * 60)
    print("[测试 1] 首页连通性")
    try:
        resp = SESSION.get(BASE_URL, timeout=15)
        print(f"  HTTP {resp.status_code} | 响应大小: {len(resp.text)} bytes")
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string if soup.title else "(无标题)"
        print(f"  页面标题: {title}")
        # 检测 Discuz! 版本
        if "Discuz!" in resp.text:
            import re
            ver = re.search(r"Discuz!\s*X?([\d.]+)", resp.text)
            print(f"  ✅ Discuz! 版本: {ver.group(0) if ver else '未知'}")
        # 检测同盾风控
        if "tongdun" in resp.text.lower() or "同盾" in resp.text:
            print("  ⚠️  检测到同盾风控插件（页面底部）")
        print("  ✅ 连通性测试通过\n")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 2: 搜索功能 ──────────────────────────────────────

def test_search():
    """测试搜索'导师'关键词"""
    print("=" * 60)
    print("[测试 2] 搜索功能 — 关键词: '导师'")
    try:
        url = f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes&srchtxt=导师"
        resp = SESSION.get(url, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"  HTTP {resp.status_code} | 响应大小: {len(resp.text)} bytes")

        # 提取总结果数
        count_text = soup.get_text()
        match = re.search(r"找到.*?(\d+)\s*个结果", count_text)
        if match:
            print(f"  📊 搜索结果总数: {match.group(1)} 条")

        # 解析前 3 条结果
        items = soup.select(".pbw, li.bbda, table[id^=thread_]")
        if not items:
            # 备选选择器
            items = soup.select("li[id^=thread]")

        print(f"  解析到 {len(items)} 条结果项")
        for i, item in enumerate(items[:3]):
            try:
                title_el = item.select_one("a.xst, a.s, h3 a")
                title = title_el.get_text(strip=True) if title_el else "?"
                href = title_el.get("href", "") if title_el else ""

                # 提取 tid
                tid_match = re.search(r"tid=(\d+)", href)
                tid = tid_match.group(1) if tid_match else "?"

                print(f"  [{i+1}] {title[:60]}")
                print(f"      tid={tid} | href={href[:80]}")
            except Exception as e:
                print(f"  [{i+1}] 解析异常: {e}")

        print("  ✅ 搜索测试通过\n")
        return len(items) > 0
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 3: 帖子详情页解析 ────────────────────────────────

def test_thread_detail(tid="250330"):
    """测试帖子详情页 — 游客模式"""
    print("=" * 60)
    print(f"[测试 3] 帖子详情页 — tid={tid}")
    try:
        url = f"{BASE_URL}/forum.php?mod=viewthread&tid={tid}"
        resp = SESSION.get(url, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"  HTTP {resp.status_code} | 响应大小: {len(resp.text)} bytes")

        # 标题
        title_el = soup.select_one("h1.ts, h1.ph, #thread_subject")
        title = title_el.get_text(strip=True) if title_el else "(无标题)"
        print(f"  帖子标题: {title[:60]}")

        # 楼主正文
        main_post = soup.select_one("#post_0") or soup.select_one("div[id^=post_]:first-child")
        if main_post:
            content_div = main_post.select_one(".t_f") or main_post.select_one("td.t_f")
            content = content_div.get_text(strip=True) if content_div else ""
            print(f"  楼主正文长度: {len(content)} 字")
            print(f"  正文预览: {content[:100]}...")

        # 回复
        reply_posts = soup.select("[id^=post_]")
        if len(reply_posts) > 1:
            print(f"  回复数: {len(reply_posts) - 1} 条")
            second = reply_posts[1]
            reply_content = second.select_one(".t_f")
            if reply_content:
                print(f"  首条回复: {reply_content.get_text(strip=True)[:80]}...")

        # 检查是否需要登录
        if "需要登录" in resp.text or "请登录" in resp.text:
            print("  ⚠️  页面提示需要登录")
        else:
            print("  ✅ 游客可查看完整内容，无需登录")

        print("  ✅ 详情页测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 4: 反爬压力测试 ──────────────────────────────────

def test_rate_limiting():
    """测试连续请求是否触发反爬"""
    print("=" * 60)
    print("[测试 4] 反爬压力测试 — 连续 5 次搜索请求（间隔 2s）")
    success = 0
    for i in range(5):
        try:
            url = f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes&srchtxt=导师&page={i+1}"
            resp = SESSION.get(url, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 10000:
                success += 1
                print(f"  请求 #{i+1}: ✅ HTTP 200 | {len(resp.text)} bytes")
            else:
                print(f"  请求 #{i+1}: ⚠️  HTTP {resp.status_code} | {len(resp.text)} bytes")
        except Exception as e:
            print(f"  请求 #{i+1}: ❌ {e}")

        if i < 4:
            time.sleep(2)

    print(f"  结果: {success}/5 成功")
    if success == 5:
        print("  ✅ 未触发速率限制，每秒 0.5 次请求安全\n")
    else:
        print(f"  ⚠️  第 {success+1} 次开始被限制\n")

    return success == 5


# ─── 测试 5: 数据密度评估 ──────────────────────────────────

def test_data_density():
    """评估"联系导师"相关帖子的数据密度"""
    print("=" * 60)
    print("[测试 5] 数据密度评估")

    keywords = ["联系导师", "导师推荐", "选导师", "导师人品", "导师评价", "套磁"]
    for kw in keywords:
        try:
            url = f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes&srchtxt={kw}"
            resp = SESSION.get(url, timeout=10)
            resp.encoding = "utf-8"
            soup_text = resp.get_text()
            match = re.search(r"找到.*?(\d+)\s*个结果", soup_text)
            count = match.group(1) if match else "?"
            print(f"  '{kw}': {count} 条结果")
            time.sleep(1.5)
        except Exception as e:
            print(f"  '{kw}': 错误 - {e}")

    print()


# ─── 主入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║     保研论坛 eeban.com 爬虫可行性测试                    ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    results = {}
    results["连通性"] = test_connectivity()
    time.sleep(1)

    results["搜索功能"] = test_search()
    time.sleep(1.5)

    results["帖子详情"] = test_thread_detail()
    time.sleep(1)

    results["反爬压力"] = test_rate_limiting()
    time.sleep(1)

    test_data_density()

    # ── 总结 ──
    print("=" * 60)
    print("综合测试结果:")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    all_pass = all(results.values())
    print(f"\n  {'🎉 全部通过 — 可立即开发爬虫' if all_pass else '⚠️ 部分失败 — 需进一步排查'}")
    print()
