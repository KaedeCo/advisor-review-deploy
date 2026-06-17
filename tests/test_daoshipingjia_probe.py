"""
导师评价网 daoshipingjia.net 爬虫可行性探测

架构特点：
  - 树状导航: /schools → /schools/{学校} → /schools/{学校}/{院系} → /teacher/{id}
  - 全SSR渲染，无JS依赖，无需登录
  - 评价内容为会员专享（付费），可获取AI总结+评分
"""

import sys
import io
import re
import time
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup

BASE = "https://daoshipingjia.net"
S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
})

# ═══════════════════════════════════════════════════════════════
#  通用解析
# ═══════════════════════════════════════════════════════════════

def extract_cards(soup: BeautifulSoup) -> list[dict]:
    """提取学校/院系/导师卡片：名称、评分、链接"""
    # 尝试多种选择器
    cards = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not href:
            continue
        # 找评分（通常在同一卡片内）
        parent = link.parent
        for _ in range(5):
            parent = parent.parent if parent else None
            if parent is None:
                break
            # 查找数字评分
            score_text = parent.get_text(" ", strip=True)
            score_m = re.search(r"(\d+\.\d+)", score_text)
            if score_m:
                name = link.get_text(strip=True)
                if len(name) > 1 and len(name) < 60:
                    cards.append({
                        "name": name,
                        "score": float(score_m.group(1)),
                        "url": href if href.startswith("http") else BASE + href,
                    })
                    break
    return cards


def deduplicate_cards(cards: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for c in cards:
        key = c["name"] + "|" + str(c["score"])
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


# ═══════════════════════════════════════════════════════════════
#  测试
# ═══════════════════════════════════════════════════════════════

def test_level1_schools():
    """测试一级：获取所有学校列表"""
    print("=" * 60)
    print("[层级1] /schools — 学校列表")
    try:
        r = S.get(f"{BASE}/schools", timeout=15)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"  HTTP {r.status_code} | {len(r.text):,} bytes")

        cards = extract_cards(soup)
        cards = deduplicate_cards(cards)
        print(f"  解析到 {len(cards)} 所学校")
        for c in cards[:10]:
            print(f"    {c['name']:8s} {c['score']:4.1f}  → {c['url'][:60]}")
        return cards
    except Exception as e:
        print(f"  ❌ {e}")
        return []


def test_level2_departments(school_name: str, school_url: str):
    """测试二级：获取某校院系列表"""
    print(f"\n{'='*60}")
    print(f"[层级2] {school_url}")
    try:
        r = S.get(school_url, timeout=15)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"  HTTP {r.status_code} | {len(r.text):,} bytes")

        cards = extract_cards(soup)
        cards = deduplicate_cards(cards)
        print(f"  {school_name}: {len(cards)} 个院系")
        for c in cards[:8]:
            print(f"    {c['name']:20s} {c['score']:4.1f}  → {c['url'][:80]}")
        return cards
    except Exception as e:
        print(f"  ❌ {e}")
        return []


def test_level3_advisors(dept_name: str, dept_url: str):
    """测试三级：获取某院系导师列表"""
    print(f"\n{'='*60}")
    print(f"[层级3] {dept_url}")
    try:
        r = S.get(dept_url, timeout=15)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"  HTTP {r.status_code} | {len(r.text):,} bytes")

        # 提取导师：链接包含 /teacher/{id}
        advisors = []
        for link in soup.select("a[href*='/teacher/']"):
            href = link.get("href", "")
            name = link.get_text(strip=True)
            if len(name) < 2 or name in ("升级会员查看完整评价", "访问链接", "查看详情"):
                continue

            tid = re.search(r"/teacher/(\d+)", href)
            tid = tid.group(1) if tid else "?"

            # 尝试提取评分
            parent = link.parent
            score = None
            for _ in range(5):
                parent = parent.parent if parent else None
                if parent is None:
                    break
                score_m = re.search(r"(\d+\.\d+)", parent.get_text(" ", strip=True))
                if score_m:
                    score = float(score_m.group(1))
                    break

            advisors.append({
                "name": name,
                "teacher_id": tid,
                "score": score,
                "url": f"{BASE}/teacher/{tid}",
            })

        print(f"  {dept_name}: {len(advisors)} 位导师")
        for a in advisors[:8]:
            print(f"    {a['name']:10s} {str(a['score']):>5s}  → id={a['teacher_id']}")
        # 检查是否有高分导师（≥4.0）
        score_known = [a for a in advisors if a['score'] is not None]
        hidden = len(advisors) - len(score_known)
        if hidden > 0:
            print(f"  ⚠️  {hidden} 位低分导师姓名被隐藏（需会员）")
        return advisors
    except Exception as e:
        print(f"  ❌ {e}")
        return []


def test_teacher_detail(teacher_id: str):
    """测试四级：导师详情页"""
    print(f"\n{'='*60}")
    print(f"[层级4] /teacher/{teacher_id}")
    try:
        r = S.get(f"{BASE}/teacher/{teacher_id}", timeout=15)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"  HTTP {r.status_code} | {len(r.text):,} bytes")

        # 姓名
        name_el = soup.select_one("h1, h2, .teacher-name")
        name = name_el.get_text(strip=True) if name_el else "?"

        # 评分
        score_el = soup.select_one("[class*='score'], [class*='rating']")
        score = score_el.get_text(strip=True) if score_el else "?"

        # 评价数
        review_text = soup.get_text(" ", strip=True)
        review_m = re.search(r"(\d+)\s*条评价", review_text)
        reviews = review_m.group(1) if review_m else "?"

        # AI总结
        ai_summary = ""
        ai_el = soup.select_one("[class*='ai'], [class*='summary'], [class*='conclusion']")
        if ai_el:
            ai_summary = ai_el.get_text(strip=True)[:200]

        # 会员限制
        has_member_wall = any(
            kw in review_text for kw in
            ["升级会员", "会员专享", "需会员", "付费查看"]
        )

        print(f"  导师: {name}")
        print(f"  评分: {score} | 评价数: {reviews}")
        print(f"  AI总结: {ai_summary[:120]}")
        print(f"  评价原文需会员: {'是' if has_member_wall else '否'}")
        print(f"  无需登录可浏览: 是")

        return {
            "name": name, "score": score, "reviews": reviews,
            "ai_summary": ai_summary, "member_wall": has_member_wall,
        }
    except Exception as e:
        print(f"  ❌ {e}")
        return {}


def test_rate_limiting():
    """反爬压力测试"""
    print(f"\n{'='*60}")
    print("[反爬测试] 连续 8 次请求 /schools (间隔 1s)")
    success = 0
    sizes = []
    for i in range(8):
        try:
            r = S.get(f"{BASE}/schools", timeout=10)
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

    # 检查响应大小一致性（反爬可能返回不同页面）
    if len(set(sizes)) == 1:
        print(f"  ✅ {success}/8 成功 | 响应一致 | 无反爬触发")
    else:
        print(f"  ⚠️  {success}/8 成功 | 响应大小不一致 → {set(sizes)}")
    print()


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   导师评价网 daoshipingjia.net 爬虫可行性探测           ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 层级1: 学校
    schools = test_level1_schools()
    time.sleep(2)

    # 层级2: 清华大学院系
    tsinghua = next((s for s in schools if "清华" in s["name"]), None)
    if tsinghua:
        depts = test_level2_departments(tsinghua["name"], tsinghua["url"])
        time.sleep(2)

        # 层级3: 第一个院系的导师
        if depts:
            first_dept = depts[0]
            advisors = test_level3_advisors(first_dept["name"], first_dept["url"])
            time.sleep(2)

            # 层级4: 第一位导师详情
            if advisors:
                first_advisor = advisors[0]
                test_teacher_detail(first_advisor["teacher_id"])

    # 反爬测试
    test_rate_limiting()

    print("=" * 60)
    print("探测完成")
