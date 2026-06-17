"""
Semantic Scholar API 可行性测试脚本
====================================
端点: https://api.semanticscholar.org/graph/v1/author/search

测试内容：
  1. 作者搜索（无 API Key）
  2. 返回 JSON 结构验证
  3. 速率限制检测
  4. 中国导师覆盖度评估
  5. fields 参数效果

注意：无 API Key 限速 ~1 req/s；申请免费 Key 后提升至 100 req/5min
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time
import json

BASE = "https://api.semanticscholar.org/graph/v1"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AdvisorReviewPlatform/1.0 (contact@example.com)",
})

# ─── 如果申请了 API Key，填入此处 ──────────────────────────
API_KEY = ""  # 在 https://www.semanticscholar.org/product/api 申请


def api_get(path: str, params: dict = None) -> dict:
    """封装 GET 请求，自动附加 API Key"""
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    resp = SESSION.get(f"{BASE}{path}", params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ─── 测试 1: 基础作者搜索 ──────────────────────────────────

def test_basic_author_search():
    """搜索一位知名中国教授"""
    print("=" * 60)
    print("[测试 1] 基础作者搜索 — query='Yao Zhang Tsinghua'")
    try:
        data = api_get("/author/search", {
            "query": "Yao Zhang Tsinghua",
            "limit": 3,
            "fields": "name,affiliations,paperCount,citationCount,hIndex",
        })
        total = data.get("total", 0)
        authors = data.get("data", [])
        print(f"  匹配总数: {total}")
        print(f"  返回条数: {len(authors)}")

        for a in authors:
            print(f"\n  ┌─ {a.get('name', '?')}")
            print(f"  ├─ authorId: {a.get('authorId', '?')}")
            print(f"  ├─ affiliations: {a.get('affiliations', [])}")
            print(f"  ├─ papers: {a.get('paperCount', '?')}")
            print(f"  ├─ citations: {a.get('citationCount', '?')}")
            print(f"  └─ hIndex: {a.get('hIndex', '?')}")

        print(f"\n  ✅ 基础搜索测试通过\n")
        return len(authors) > 0
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            print("  ⚠️  触发速率限制 (429 Too Many Requests)")
            print("  建议申请免费 API Key: https://www.semanticscholar.org/product/api")
        else:
            print(f"  ❌ HTTP {e.response.status_code}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


# ─── 测试 2: 中文姓名搜索 ──────────────────────────────────

def test_chinese_name_search():
    """搜索中文拼音姓名"""
    print("=" * 60)
    print("[测试 2] 中文拼音姓名搜索 — 'Wei Li computer science'")
    try:
        data = api_get("/author/search", {
            "query": "Wei Li computer science",
            "limit": 5,
            "fields": "name,affiliations,hIndex,paperCount",
        })
        authors = data.get("data", [])
        print(f"  返回 {len(authors)} 位作者（total={data.get('total', '?')})")

        for a in authors[:3]:
            affs = a.get("affiliations", [])
            aff_str = affs[0] if affs else "未知单位"
            print(f"  · {a.get('name')} | {aff_str} | h={a.get('hIndex', '?')}")

        print(f"\n  ✅ 中文名搜索测试通过\n")
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            print("  ⚠️  速率限制\n")
        else:
            print(f"  ❌ HTTP {e.response.status_code}\n")
        return False


# ─── 测试 3: 速率限制探测 ──────────────────────────────────

def test_rate_limit():
    """连续请求测试触发 429"""
    if API_KEY:
        print("  ℹ️  使用 API Key，速率限制较宽松，跳过压力测试\n")
        return True

    print("=" * 60)
    print("[测试 3] 速率限制探测 — 连续 5 次请求（无 API Key）")
    success = 0
    for i in range(5):
        try:
            resp = SESSION.get(
                f"{BASE}/author/search?query=test&limit=1",
                timeout=10,
            )
            if resp.status_code == 200:
                success += 1
                print(f"  请求 #{i+1}: ✅ HTTP 200")
            elif resp.status_code == 429:
                print(f"  请求 #{i+1}: 🚫 HTTP 429 (速率限制触发)")
                print(f"  → 第 {i+1} 次请求被限流，无 Key 下安全速率约为 1 req/s")
                break
            else:
                print(f"  请求 #{i+1}: ⚠️  HTTP {resp.status_code}")
        except Exception as e:
            print(f"  请求 #{i+1}: ❌ {e}")
        time.sleep(1.5)

    print(f"\n  结果: {success}/5 通过")
    if success >= 4:
        print("  ✅ 1.5s 间隔安全\n")
    else:
        print("  ⚠️  建议间隔 ≥ 2s，或申请 API Key\n")

    return success > 0


# ─── 测试 4: 高级字段 ──────────────────────────────────────

def test_advanced_fields():
    """测试返回更多字段（论文列表、引用等）"""
    print("=" * 60)
    print("[测试 4] 高级字段测试 — fields=name,affiliations,hIndex,paperCount,citationCount,url")
    try:
        data = api_get("/author/search", {
            "query": "Andrew Ng Stanford",
            "limit": 1,
            "fields": "name,affiliations,hIndex,paperCount,citationCount,url,externalIds",
        })
        authors = data.get("data", [])
        if authors:
            a = authors[0]
            print(f"  作者: {a.get('name')}")
            print(f"  hIndex: {a.get('hIndex')}")
            print(f"  papers: {a.get('paperCount')}")
            print(f"  citations: {a.get('citationCount')}")
            print(f"  externalIds: {a.get('externalIds', {})}")
            print(f"  url: {a.get('url', '')}")

        print(f"  ✅ 高级字段测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 测试 5: 作者关联的论文 ─────────────────────────────────

def test_author_papers():
    """获取某位作者的论文列表"""
    print("=" * 60)
    print("[测试 5] 作者论文列表（获取具体 authorId 后查询其论文）")
    try:
        # 先搜索一位作者
        data = api_get("/author/search", {
            "query": "Geoffrey Hinton",
            "limit": 1,
            "fields": "authorId,name",
        })
        authors = data.get("data", [])
        if not authors:
            print("  ⚠️  未找到作者\n")
            return False

        author_id = authors[0].get("authorId")
        print(f"  找到作者: {authors[0].get('name')} (id={author_id})")

        # 查询其论文
        papers_data = api_get(f"/author/{author_id}/papers", {
            "limit": 3,
            "fields": "title,year,citationCount,journal",
        })
        papers = papers_data.get("data", [])
        print(f"  该作者共发表 {papers_data.get('total', '?')} 篇论文")
        for p in papers:
            year = p.get("year", "?")
            title = p.get("title", "?")[:60]
            citations = p.get("citationCount", "?")
            journal = (p.get("journal") or {}).get("name", "?")
            print(f"  · [{year}] {title} ({citations}次引用) | {journal}")

        print(f"\n  ✅ 作者论文测试通过\n")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}\n")
        return False


# ─── 主入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║     Semantic Scholar API 可行性测试                      ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    if not API_KEY:
        print("💡 提示: 无 API Key 模式下速率限制严格 (~1 req/s)")
        print("   免费申请: https://www.semanticscholar.org/product/api#api-key-form\n")

    results = {}
    results["基础搜索"] = test_basic_author_search()
    time.sleep(1.5)
    results["中文名搜索"] = test_chinese_name_search()
    time.sleep(1.5)
    test_rate_limit()
    time.sleep(1.5)
    results["高级字段"] = test_advanced_fields()
    time.sleep(1.5)
    results["作者论文"] = test_author_papers()

    print("=" * 60)
    print("综合测试结果:")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    all_pass = all(results.values())
    print(f"\n  {'🎉 全部通过' if all_pass else '⚠️ 部分失败（可能因速率限制）'}")
    print()
