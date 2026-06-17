"""
考研论坛 bbs.kaoyan.com 爬虫可行性探测脚本
===============================================
目标: 评估 bbs.kaoyan.com（Discuz! X3.x）的反爬机制与数据可获取性
参照: test_eeban.py / test_muchong_probe.py 的测试模式

测试维度:
  1. 连通性 — 首页/论坛/门户是否可达
  2. CMS 版本 — Discuz! 版本号检测
  3. 搜索功能 — 多种关键词的搜索表现
  4. 帖子详情 — 游客能否浏览完整帖子
  5. 反爬矩阵 — 速率限制/登录墙/验证码/风控
  6. Cookie 行为 — Session vs 无 Cookie
  7. 数据密度 — 导师相关内容的搜索结果量
  8. 编码检测 — gbk/utf-8 自适应

URL 模式预判（Discuz! 标准）:
  - 搜索: /search.php?mod=forum&searchsubmit=yes&srchtxt={keyword}
  - 帖子: /forum.php?mod=viewthread&tid={tid}
  - 版块: /forum.php?mod=forumdisplay&fid={fid}
  - 首页: /forum.php
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import sys
import io
from collections import Counter
from urllib.parse import quote

# Windows 控制台 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 配置 ──────────────────────────────────────────────────
BASE_FORUM = "http://bbs.kaoyan.com"
BASE_PORTAL = "https://www.kaoyan.com"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": BASE_FORUM,
})

# 无 Cookie 独立 Session（用于对比）
SESSION_NOCOOKIE = requests.Session()
SESSION_NOCOOKIE.headers.update(dict(SESSION.headers))


# ── 辅助函数 ──────────────────────────────────────────────

def safe_get(url: str, session: requests.Session = SESSION, **kwargs) -> requests.Response:
    """带超时和异常保护的 GET 请求"""
    defaults = {"timeout": 15, "allow_redirects": True}
    defaults.update(kwargs)
    resp = session.get(url, **defaults)
    resp.encoding = _detect_encoding(resp)
    return resp


def _detect_encoding(resp: requests.Response) -> str:
    """从 Content-Type 或 HTML meta 标签推断编码"""
    ct = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([\w-]+)", ct, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # 从 HTML meta 推断
    m2 = re.search(rb'charset=["\']?([\w-]+)', resp.content[:2048], re.IGNORECASE)
    if m2:
        enc = m2.group(1).decode("ascii").lower()
        if enc in ("gbk", "gb2312", "gb18030"):
            return "gbk"
        return enc
    return "gbk"  # Discuz! 中文站默认 gbk


def wait(seconds: float = 1.5):
    time.sleep(seconds)


# ── 测试 1: 首页连通性 ────────────────────────────────────

def test_connectivity() -> dict:
    """测试 bbs.kaoyan.com 论坛首页和门户首页的连通性"""
    results = {}

    # 1.1 论坛首页
    print("\n[1.1] 论坛首页连通测试...")
    try:
        resp = safe_get(f"{BASE_FORUM}/forum.php")
        results["forum_home"] = {
            "status": resp.status_code,
            "size_kb": round(len(resp.text) / 1024, 1),
            "elapsed_s": round(resp.elapsed.total_seconds(), 2),
            "encoding": resp.encoding or "unknown",
            "title": "",
        }
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.title:
            results["forum_home"]["title"] = soup.title.get_text(strip=True)
        print(f"  状态: HTTP {resp.status_code} | {results['forum_home']['size_kb']}KB | "
              f"{results['forum_home']['elapsed_s']}s | 编码: {results['forum_home']['encoding']}")
        print(f"  标题: {results['forum_home']['title']}")
    except Exception as e:
        results["forum_home"] = {"error": str(e)}
        print(f"  ❌ 失败: {e}")

    wait(1.5)

    # 1.2 门户首页
    print("[1.2] 门户首页连通测试...")
    try:
        resp = safe_get(f"{BASE_PORTAL}/")
        results["portal_home"] = {
            "status": resp.status_code,
            "size_kb": round(len(resp.text) / 1024, 1),
            "elapsed_s": round(resp.elapsed.total_seconds(), 2),
        }
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.title:
            results["portal_home"]["title"] = soup.title.get_text(strip=True)
        print(f"  状态: HTTP {resp.status_code} | {results['portal_home']['size_kb']}KB | "
              f"{results['portal_home']['elapsed_s']}s")
        print(f"  标题: {results['portal_home'].get('title', 'N/A')}")
    except Exception as e:
        results["portal_home"] = {"error": str(e)}
        print(f"  ❌ 失败: {e}")

    return results


# ── 测试 2: CMS 版本检测 ──────────────────────────────────

def test_cms_version() -> dict:
    """从 HTML meta/注释中提取 Discuz! 版本号"""
    print("\n[2] CMS 版本检测...")
    try:
        resp = safe_get(f"{BASE_FORUM}/forum.php")
        text = resp.text

        # 多种 Discuz! 版本标识正则
        patterns = [
            (r'Discuz!\s*X([\d.]+)', "X版本"),
            (r'Discuz![\s]*([\d.]+)', "标准版本"),
            (r'Powered by\s*<a[^>]*>Discuz!</a>\s*[Xx]?([\d.]*)', "Powered by"),
            (r'<meta[^>]*generator[^>]*Discuz![\s]*X?([\d.]*)', "Meta生成器"),
        ]

        found_versions = {}
        for pattern, label in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                version = match.group(1).strip() if match.group(1) else "未知"
                found_versions[label] = version

        # 从 CSS/JS 文件路径中找版本号
        js_matches = re.findall(r'(?:css|js)[^"\'<>]*?(\d{4,6})', text)
        if js_matches:
            found_versions["CSS/JS日期码"] = js_matches[:3]

        if found_versions:
            for k, v in found_versions.items():
                print(f"  ✅ {k}: {v}")
        else:
            print("  ⚠️ 未检测到 Discuz! 版本标识")

        return {"found": bool(found_versions), "versions": found_versions}

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return {"found": False, "error": str(e)}


# ── 测试 3: 搜索功能 ──────────────────────────────────────

def test_search() -> dict:
    """多关键词搜索测试"""
    print("\n[3] 搜索功能测试...")

    keywords = [
        "导师",          # 核心关键词
        "选导师",        # 场景关键词
        "导师推荐",      # 推荐关键词
        "联系导师",      # 联系场景
        "导师评价",      # 评价类
        "考研 导师",     # 组合关键词
        "张老师",        # 通用称呼
        "计算机 导师",   # 专业+导师
    ]

    search_results = {}
    all_tids = []  # 收集所有 tid 用于后续详情测试

    for kw in keywords:
        wait(2)
        print(f"  搜索: \"{kw}\"...", end=" ")
        try:
            url = (f"{BASE_FORUM}/search.php?mod=forum"
                   f"&searchsubmit=yes&srchtxt={quote(kw, encoding='gbk')}")
            resp = safe_get(url)

            soup = BeautifulSoup(resp.text, "html.parser")
            total_count = _detect_result_count(resp.text)
            items = _parse_search_items(soup)

            # 收集 tid
            for item in items:
                tid = item.get("tid")
                if tid:
                    all_tids.append(tid)

            search_results[kw] = {
                "status": resp.status_code,
                "total_claimed": total_count,
                "items_on_page": len(items),
                "items": [{"title": i["title"], "tid": i.get("tid", "")} for i in items[:5]],
            }
            print(f"HTTP {resp.status_code} | 声称 {total_count} 条 | 本页 {len(items)} 条")

        except Exception as e:
            search_results[kw] = {"error": str(e)}
            print(f"❌ {e}")

    return search_results, list(set(all_tids))


def _detect_result_count(text: str) -> int:
    """从搜索页面文本中提取结果总数"""
    patterns = [
        r"找到.*?(\d+)\s*个?(?:结果|相关|帖子|主题)",
        r"共\s*(?:搜索到|有)?\s*(\d+)\s*(?:个|条)",
        r"(?:结果:|共)\s*(\d+)\s*(?:个|条)",
        r"(\d+)\s*个相关",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return 0


def _parse_search_items(soup: BeautifulSoup) -> list[dict]:
    """解析 Discuz! 搜索结果条目"""
    items = []
    # Discuz! 搜索结果常见选择器
    for container in soup.select(
        ".pbw, li.bbda, table[id^=thread_], "
        "li[id^=thread], dl.bbm, "
        "div[id^=thread_], li.pbw"
    ):
        try:
            title_el = (
                container.select_one("a.xst") or
                container.select_one("a.s") or
                container.select_one("h3 a") or
                container.select_one("a[href*='tid=']")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            tid_match = re.search(r"tid=(\d+)", href)
            tid = tid_match.group(1) if tid_match else ""

            items.append({"title": title, "tid": tid})
        except Exception:
            continue
    return items


# ── 测试 4: 帖子详情页 ────────────────────────────────────

def test_thread_detail(tids: list[str]) -> dict:
    """测试帖子详情页的游客可访问性"""
    print(f"\n[4] 帖子详情页测试 (共 {len(tids)} 个 tid)...")
    if not tids:
        print("  ⚠️ 无可用 tid，跳过")
        return {"tested": 0, "accessible": 0, "samples": []}

    results = []
    for tid in tids[:10]:  # 最多测 10 个
        wait(1.5)
        url = f"{BASE_FORUM}/forum.php?mod=viewthread&tid={tid}"
        try:
            resp = safe_get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 检测登录墙
            text = resp.text
            is_login_wall = any(kw in text for kw in ["需要登录", "请登录", "您所在的用户组无法", "无权访问"])

            # 提取正文
            main_content = ""
            for selector in ["#post_0 .t_f", "td.t_f", "div.t_f", ".postmessage", ".pct .pcb"]:
                el = soup.select_one(selector)
                if el:
                    main_content = el.get_text(" ", strip=True)[:200]
                    break

            # 统计回复
            reply_posts = soup.select("[id^=post_]")

            title = ""
            for sel in ["h1.ts", "h1.ph", "#thread_subject", "h1", ".ts"]:
                tel = soup.select_one(sel)
                if tel:
                    title = tel.get_text(strip=True)
                    break

            result = {
                "tid": tid,
                "status": resp.status_code,
                "title": title[:80],
                "content_preview": main_content[:150],
                "reply_count": len(reply_posts) - 1 if reply_posts else 0,
                "login_wall": is_login_wall,
                "size_kb": round(len(text) / 1024, 1),
            }
            results.append(result)

            status_str = "🚫登录墙" if is_login_wall else "✅"
            print(f"  {status_str} tid={tid} | HTTP {resp.status_code} | "
                  f"{result['size_kb']}KB | {len(reply_posts)-1}回复 | {title[:40]}")

        except Exception as e:
            print(f"  ❌ tid={tid}: {e}")
            results.append({"tid": tid, "error": str(e)})

    accessible = sum(1 for r in results if not r.get("login_wall") and not r.get("error"))
    return {
        "tested": len(results),
        "accessible": accessible,
        "login_walled": sum(1 for r in results if r.get("login_wall")),
        "samples": results,
    }


# ── 测试 5: 反爬矩阵 ──────────────────────────────────────

def test_anti_crawl() -> dict:
    """连续快速请求检测速率限制/风控"""
    print("\n[5] 反爬矩阵测试 (10 次连续请求, 间隔 1s)...")

    url = f"{BASE_FORUM}/forum.php"
    results = []
    sizes = []

    for i in range(10):
        try:
            resp = safe_get(url)
            size = len(resp.text)
            sizes.append(size)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 检测风控信号
            text = resp.text[:5000].lower()
            signals = {
                "被拦截": "被拦截" in text or "blocked" in text,
                "验证码": "captcha" in text or "验证码" in text or "verification" in text,
                "同盾": "tongdun" in text or "同盾" in text,
                "502": resp.status_code == 502,
                "503": resp.status_code == 503,
                "登录墙": "需要登录" in text or "请登录" in text,
                "重定向": resp.status_code in (301, 302) and "login" in str(resp.headers.get("Location", "")).lower(),
            }

            results.append({
                "req_num": i + 1,
                "status": resp.status_code,
                "size": size,
                "elapsed": round(resp.elapsed.total_seconds(), 2),
                "signals": {k: v for k, v in signals.items() if v},
            })

            status_icon = "✅" if resp.status_code == 200 else f"❌{resp.status_code}"
            print(f"  [{i+1}/10] {status_icon} {size}B | {resp.elapsed.total_seconds():.2f}s"
                  + (f" | 信号: {list(results[-1]['signals'].keys())}" if results[-1]["signals"] else ""))

        except Exception as e:
            print(f"  [{i+1}/10] ❌ 异常: {e}")
            results.append({"req_num": i + 1, "error": str(e)})

        wait(1.0)

    # 分析
    success = sum(1 for r in results if r.get("status") == 200 and not r.get("error"))
    sizes_unique = len(set(sizes)) if sizes else 0

    # 检查是否响应大小一致性（被拦截时通常返回固定大小错误页）
    size_consistency = sizes_unique == 1 if sizes else False

    ban_indicators = {
        "rate_limited": success < 8,
        "size_consistent": size_consistency and success < 8,  # 被拦时返回相同错误页
        "captcha_triggered": any(r.get("signals", {}).get("验证码") for r in results),
        "firewall_triggered": any(r.get("signals", {}).get("被拦截") for r in results),
    }

    print(f"\n  总结: {success}/10 成功 | 响应大小变化: {sizes_unique} 种")

    return {
        "success_rate": f"{success}/10",
        "avg_elapsed": round(sum(r.get("elapsed", 0) for r in results) / len(results), 2),
        "size_variation": sizes_unique,
        "indicators": ban_indicators,
        "raw_results": results,
    }


# ── 测试 6: Cookie/Session 行为 ────────────────────────────

def test_cookie_behavior() -> dict:
    """对比有 Cookie(Session) vs 无 Cookie 的访问结果"""
    print("\n[6] Cookie 行为对比...")

    results = []

    for label, sess in [("有Session(Cookie)", SESSION), ("无Cookie(裸请求)", SESSION_NOCOOKIE)]:
        wait(1)
        try:
            resp = sess.get(
                f"{BASE_FORUM}/search.php?mod=forum&searchsubmit=yes&srchtxt={quote('导师', encoding='gbk')}",
                timeout=15,
            )
            resp.encoding = _detect_encoding(resp)
            count = _detect_result_count(resp.text)
            soup = BeautifulSoup(resp.text, "html.parser")
            items = _parse_search_items(soup)

            # 检查 Cookie
            cookies = sess.cookies.get_dict()
            has_cookies = bool(cookies)

            r = {
                "label": label,
                "status": resp.status_code,
                "result_count": count,
                "items": len(items),
                "cookie_keys": list(cookies.keys()),
                "encoding": resp.encoding,
            }
            results.append(r)
            print(f"  {label}: HTTP {resp.status_code} | 结果 {count} | "
                  f"本页 {len(items)}条 | Cookie: {list(cookies.keys())[:5] if cookies else '无'}")

        except Exception as e:
            print(f"  {label}: ❌ {e}")
            results.append({"label": label, "error": str(e)})

    return results


# ── 测试 7: 数据密度评估 ──────────────────────────────────

def test_data_density(search_results: dict) -> dict:
    """评估导师相关内容的搜索数据密度"""
    print("\n[7] 数据密度评估...")

    density = {}
    for kw, data in search_results.items():
        if "error" in data:
            density[kw] = {"viable": False, "error": data["error"]}
            continue
        count = data.get("total_claimed", 0)
        items = data.get("items_on_page", 0)
        density[kw] = {
            "total_results": count,
            "per_page": items,
            "worth_crawling": count > 10 and items > 0,
            "data_level": "高" if count > 100 else ("中" if count > 20 else "低"),
        }

    # 汇总
    viable_keywords = [kw for kw, d in density.items() if d.get("worth_crawling")]
    print(f"  有效关键词: {len(viable_keywords)}/{len(density)}")
    for kw in viable_keywords[:10]:
        d = density[kw]
        print(f"  ✅ \"{kw}\": {d['total_results']} 结果 | {d['per_page']}条/页 | {d['data_level']}密度")

    return density


# ── 测试 8: 版块结构探查 ──────────────────────────────────

def test_board_structure() -> dict:
    """探查论坛版块结构，寻找导师相关的目标版块"""
    print("\n[8] 版块结构探查...")

    try:
        resp = safe_get(f"{BASE_FORUM}/forum.php")
        soup = BeautifulSoup(resp.text, "html.parser")

        # 找所有版块链接 (Discuz! 格式: forum-{fid}-1.html 或 forum.php?mod=forumdisplay&fid={fid})
        boards = []
        for link in soup.select("a[href*='forumdisplay'], a[href*='forum-'], dt a, .fl_icn a"):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if not text or len(text) < 2:
                continue

            # 提取 fid
            fid_match = re.search(r"fid=(\d+)", href) or re.search(r"forum-(\d+)-", href)
            if fid_match:
                boards.append({
                    "name": text,
                    "fid": fid_match.group(1),
                    "href": href,
                })

        # 去重
        seen_fids = set()
        unique_boards = []
        for b in boards:
            if b["fid"] not in seen_fids:
                seen_fids.add(b["fid"])
                unique_boards.append(b)

        # 识别导师相关版块
        advisor_kw = ["导师", "考研", "考博", "复试", "调剂", "院校", "研究生", "经验", "交流"]
        relevant = []
        for b in unique_boards:
            if any(kw in b["name"] for kw in advisor_kw):
                relevant.append(b)

        print(f"  发现版块: {len(unique_boards)} 个")
        print(f"  导师相关版块: {len(relevant)} 个")
        for b in relevant[:15]:
            print(f"    📂 [{b['fid']}] {b['name']}")

        return {
            "total_boards": len(unique_boards),
            "relevant_boards": len(relevant),
            "relevant_list": relevant[:20],
            "all_fids": [b["fid"] for b in unique_boards[:50]],
        }

    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return {"error": str(e)}


# ── 测试 9: 搜索参数变异测试 ──────────────────────────────

def test_search_variations() -> dict:
    """测试不同搜索参数组合的表现"""
    print("\n[9] 搜索参数变异测试...")

    variations = []

    # 不同编码
    for enc_label, enc in [("GBK", "gbk"), ("UTF-8", "utf-8")]:
        wait(2)
        try:
            q = quote("导师", encoding=enc)
            url = f"{BASE_FORUM}/search.php?mod=forum&searchsubmit=yes&srchtxt={q}"
            resp = safe_get(url)
            count = _detect_result_count(resp.text)
            items = len(_parse_search_items(BeautifulSoup(resp.text, "html.parser")))
            variations.append({"variation": f"编码={enc_label}", "status": resp.status_code,
                               "count": count, "items": items})
            print(f"  编码={enc_label}: HTTP {resp.status_code} | {count} 结果 | {items}条/页")
        except Exception as e:
            variations.append({"variation": f"编码={enc_label}", "error": str(e)})

    # 不同 mod 参数
    for mod_label, mod_val in [("forum", "forum"), ("blog", "blog"), ("portal", "portal")]:
        wait(2)
        try:
            url = f"{BASE_FORUM}/search.php?mod={mod_val}&searchsubmit=yes&srchtxt={quote('导师', encoding='gbk')}"
            resp = safe_get(url)
            count = _detect_result_count(resp.text)
            items = len(_parse_search_items(BeautifulSoup(resp.text, "html.parser")))
            variations.append({"variation": f"mod={mod_label}", "status": resp.status_code,
                               "count": count, "items": items})
            print(f"  mod={mod_label}: HTTP {resp.status_code} | {count} 结果 | {items}条/页")
        except Exception as e:
            variations.append({"variation": f"mod={mod_label}", "error": str(e)})

    return variations


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  考研论坛 bbs.kaoyan.com 爬虫可行性探测")
    print("  目标: http://bbs.kaoyan.com | 架构: Discuz! X3.x")
    print("=" * 60)

    all_results = {}

    # 1. 连通性
    all_results["connectivity"] = test_connectivity()
    wait(1)

    # 2. CMS版本
    all_results["cms_version"] = test_cms_version()
    wait(1)

    # 3. 搜索功能
    search_data, all_tids = test_search()
    all_results["search"] = search_data
    all_results["tids_found"] = len(all_tids)
    wait(1)

    # 4. 帖子详情
    all_results["thread_detail"] = test_thread_detail(all_tids)
    wait(1)

    # 5. 反爬矩阵
    all_results["anti_crawl"] = test_anti_crawl()
    wait(1)

    # 6. Cookie 行为
    all_results["cookie_behavior"] = test_cookie_behavior()
    wait(1)

    # 7. 数据密度
    all_results["data_density"] = test_data_density(search_data)
    wait(1)

    # 8. 版块结构
    all_results["board_structure"] = test_board_structure()
    wait(1)

    # 9. 搜索参数变异
    all_results["search_variations"] = test_search_variations()

    # ── 汇总报告 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("                    探测结果汇总")
    print("=" * 60)

    # 连通性
    conn = all_results.get("connectivity", {})
    forum_ok = conn.get("forum_home", {}).get("status") == 200
    print(f"\n  {'✅' if forum_ok else '❌'} 论坛连通性: HTTP {conn.get('forum_home', {}).get('status', 'N/A')}")

    # CMS
    cms = all_results.get("cms_version", {})
    print(f"  {'✅' if cms.get('found') else '⚠️'}  CMS版本: {cms.get('versions', '未检测到')}")

    # 搜索
    search_ok = any(
        isinstance(v, dict) and v.get("total_claimed", 0) > 0
        for v in all_results.get("search", {}).values()
    )
    print(f"  {'✅' if search_ok else '❌'} 搜索功能: "
          f"{sum(1 for v in all_results.get('search', {}).values() if isinstance(v, dict) and v.get('total_claimed', 0) > 0)} 个关键词有结果")

    # 帖子详情
    detail = all_results.get("thread_detail", {})
    print(f"  {'✅' if detail.get('accessible', 0) > 0 else '⚠️'} 帖子详情: "
          f"{detail.get('accessible', 0)}/{detail.get('tested', 0)} 可访问 | "
          f"{detail.get('login_walled', 0)} 个有登录墙")

    # 反爬
    ac = all_results.get("anti_crawl", {})
    print(f"  {'✅' if '10/10' == ac.get('success_rate', '') else '⚠️'} 速率限制: "
          f"{ac.get('success_rate', 'N/A')} 成功 | "
          f"响应大小 {ac.get('size_variation', '?')} 种")

    # Cookie
    cb = all_results.get("cookie_behavior", [])
    for r in cb:
        if isinstance(r, dict) and "error" not in r:
            print(f"  ℹ️  {r['label']}: {r.get('result_count', 0)} 结果 | Cookie: {r.get('cookie_keys', [])}")

    # 版块
    bs = all_results.get("board_structure", {})
    print(f"  ℹ️  版块结构: {bs.get('total_boards', 0)} 个版块 | "
          f"{bs.get('relevant_boards', 0)} 个导师相关")

    # 综合评估
    print("\n" + "─" * 40)
    print("  📊 综合可行性评估")
    print("─" * 40)

    score = 0
    checks = []
    if forum_ok:
        score += 1
        checks.append("连通 ✅")
    else:
        checks.append("连通 ❌")
    if search_ok:
        score += 2
        checks.append("搜索 ✅")
    else:
        checks.append("搜索 ❌")
    if detail.get("accessible", 0) > 0:
        score += 2
        checks.append("详情可读 ✅")
    else:
        checks.append("详情可读 ❌")
    if ac.get("success_rate") == "10/10":
        score += 1
        checks.append("无速率限制 ✅")
    elif ac.get("success_rate", "").startswith("9"):
        score += 0.5
        checks.append("轻度限制 ⚠️")
    else:
        checks.append("速率限制 ❌")
    if detail.get("login_walled", 0) == 0:
        score += 1
        checks.append("无登录墙 ✅")
    else:
        checks.append("部分登录墙 ⚠️")

    rating = score / 7 * 10  # 满分 7 分，换算为 10 分制
    print(f"  评分: {round(rating, 1)}/10 | " + " | ".join(checks))

    if rating >= 7:
        print(f"\n  🏆 结论: 高度可行，建议立即开发爬虫")
    elif rating >= 5:
        print(f"\n  ✅ 结论: 基本可行，注意反爬策略")
    elif rating >= 3:
        print(f"\n  ⚠️ 结论: 有一定难度，需要额外处理")
    else:
        print(f"\n  ❌ 结论: 目前不建议投入")

    print("=" * 60)


if __name__ == "__main__":
    main()
