"""
PI Review pi-review.com 爬虫探测

数据模型:
  - /search/?q={name}        → 搜索导师 (SSR, 免登录)
  - /pis/                    → 全量导师列表 (分页, 10条/页)
  - /pis/{id}                → 导师详情 (评分+评价)
  - /universities/           → 学校列表 (分页)
  - /universities/{id}       → 学校详情+导师列表
"""

import sys
import io
import re
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup

BASE = "https://pi-review.com"
S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
})


def test_search():
    """测试搜索: /search/?q=Zhang"""
    print("=" * 60)
    print("[测试1] 搜索 Zhang")
    r = S.get(f"{BASE}/search/?q=Zhang", timeout=15)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"  HTTP {r.status_code} | {len(r.text):,}B")

    # 总数
    text = soup.get_text(" ", strip=True)
    m = re.search(r"(\d+)\s*位导师", text)
    total = m.group(1) if m else "?"
    print(f"  匹配: {total} 位导师")

    # 解析导师卡片
    cards = soup.select("a[href*='/pis/']")
    pi_links = [a for a in cards if re.search(r"/pis/\d+$", a.get("href", ""))]
    deduped = []
    seen = set()
    for a in pi_links:
        href = a["href"]
        if href not in seen:
            seen.add(href)
            deduped.append(a)

    print(f"  导师链接: {len(deduped)} 条")
    for a in deduped[:5]:
        href = a["href"]
        pid = re.search(r"/pis/(\d+)", href).group(1)
        # 提取附近的数据
        parent = a.parent
        for _ in range(5):
            parent = parent.parent if parent else None
            if parent is None: break
            score_m = re.search(r"(\d+\.\d+)\s*/\s*5", parent.get_text(" ", strip=True))
            count_m = re.search(r"(\d+)\s*人评价", parent.get_text(" ", strip=True))
            school_m = re.search(r"([A-Z][a-zA-Z\s&.\-()]+(?:University|College|Institute)[^<]*)",
                                 parent.get_text(" ", strip=True))
            if score_m:
                print(f"    id={pid:6s} {a.get_text(strip=True):25s} "
                      f"{score_m.group(1):4s}/5  {count_m.group(1) if count_m else '?'}人评价  "
                      f"{school_m.group(1)[:30] if school_m else '?'}")
                break
    print()


def test_pi_detail():
    """测试导师详情页"""
    print("=" * 60)
    print("[测试2] 导师详情 /pis/12817")

    # 先看详情页有什么
    for pid in ["12817", "13385"]:
        try:
            r = S.get(f"{BASE}/pis/{pid}", timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)

            # 姓名
            name = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+).*\(.*?\)", text)
            name_str = name.group(0)[:40] if name else "?"

            # 评分
            score = re.search(r"(\d+\.\d+)\s*/\s*5", text)
            score_str = score.group(1) if score else "?"

            # 评价数
            reviews = re.search(r"(\d+)\s*(?:人评价|条评价|reviews?)", text)
            review_str = reviews.group(1) if reviews else "?"

            # 学校
            school = re.search(r"(?:University|College|Institute)[^,\n]{5,50}", text)
            school_str = school.group(0)[:40] if school else "?"

            # 评价内容可见？
            has_review_content = any(kw in text for kw in
                ["评价内容", "review", "点评", "comments", "评价列表"])

            print(f"  id={pid} HTTP {r.status_code} | "
                  f"name={name_str} | score={score_str} | reviews={review_str}")
            print(f"    学校={school_str} | 评价可见={has_review_content}")

            # 查找评价列表
            review_blocks = soup.select(".review, .comment, .rating-item, [class*='review']")
            if review_blocks:
                block = review_blocks[0]
                print(f"    评价样例: {block.get_text(strip=True)[:120]}")

            # 登录需求
            if "请登录" in text or "login" in text.lower():
                print(f"    ⚠️ 部分内容需登录")

            time.sleep(1)
        except Exception as e:
            print(f"  id={pid} ❌ {e}")
    print()


def test_rate_limiting():
    """反爬压力测试"""
    print("=" * 60)
    print("[测试3] 反爬 — 连续8次 /search/?q=test (间隔1s)")
    success = 0
    sizes = []
    for i in range(8):
        try:
            r = S.get(f"{BASE}/search/?q=test", timeout=10)
            sizes.append(len(r.text))
            if r.status_code == 200:
                success += 1
                print(f"  请求 #{i+1}: ✅ {len(r.text):,}B")
            else:
                print(f"  请求 #{i+1}: ⚠️ HTTP {r.status_code}")
        except Exception as e:
            print(f"  请求 #{i+1}: ❌ {e}")
        if i < 7:
            time.sleep(1)

    if len(set(sizes)) == 1:
        print(f"  ✅ {success}/8 成功 | 响应一致 | 无反爬触发")
    else:
        print(f"  ⚠️ {success}/8 成功 | 响应大小不一致 → {set(sizes)}")
    print()


def test_pagination():
    """测试分页"""
    print("=" * 60)
    print("[测试4] 分页机制")

    # 测试 /pis/?page=2
    for url in [f"{BASE}/pis/?page=2", f"{BASE}/search/?q=Zhang&page=2"]:
        try:
            r = S.get(url, timeout=10)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            page_m = re.search(r"第\s*(\d+)\s*页", text)
            print(f"  {url.split('?')[1]:30s} HTTP {r.status_code} | "
                  f"第{page_m.group(1) if page_m else '?'}页 | {len(r.text):,}B")
        except Exception as e:
            print(f"  {url:60s} ❌ {e}")
        time.sleep(1)
    print()


def test_university_detail():
    """测试学校详情页"""
    print("=" * 60)
    print("[测试5] 学校详情 /universities/257 (中科大)")

    try:
        r = S.get(f"{BASE}/universities/257", timeout=15)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # 学校名
        name_m = re.search(r"(University of Science and Technology of China)", text)
        print(f"  HTTP {r.status_code} | {len(r.text):,}B")
        print(f"  学校: {name_m.group(1) if name_m else '?'}")

        # 包含的导师链接
        pi_links = [a["href"] for a in soup.find_all("a", href=re.compile(r"/pis/\d+"))]
        print(f"  导师链接: {len(pi_links)} 条 (本页)")

        # 导师总数
        total_m = re.search(r"(\d+)\s*(?:位导师|PIs?)", text)
        print(f"  导师总数: {total_m.group(1) if total_m else '?'}")

        # 分页
        page_m = re.search(r"共\s*(\d+)\s*页", text)
        print(f"  总页数: {page_m.group(1) if page_m else '?'}")

    except Exception as e:
        print(f"  ❌ {e}")
    print()


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   PI Review pi-review.com 爬虫探测                      ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    test_search()
    time.sleep(1.5)
    test_pi_detail()
    test_rate_limiting()
    test_pagination()
    test_university_detail()

    print("=" * 60)
    print("探测完成")
