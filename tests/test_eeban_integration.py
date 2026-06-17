"""
保研论坛集成测试 — 端到端验证搜索 + 详情页
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import time
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.crawlers.eeban import EebanScraper


def test_search_only():
    print("=" * 50)
    print("[测试1] 纯搜索（不拉详情）")
    scraper = EebanScraper()
    threads = scraper.search("张三", "清华大学")
    print(f"搜索结果: {len(threads)} 条")
    for t in threads[:3]:
        print(f"  [{t['tid']}] {t['title'][:50]} | 回复:{t['reply_count']} 查看:{t['view_count']}")
    return len(threads) > 0


def test_search_with_detail():
    print("\n" + "=" * 50)
    print("[测试2] 搜索 + 拉详情页（限制 3 条）")
    scraper = EebanScraper()
    results = scraper.search_with_detail("导师", "计算机", fetch_details=True, max_threads=3)
    print(f"完整结果: {len(results)} 条")
    for i, r in enumerate(results):
        print(f"\n  --- 结果 #{i+1} ---")
        print(f"  标题: {r.get('title', '?')[:60]}")
        print(f"  评价数: {r['review_count']}")
        print(f"  来源: {r['source']}")
        for j, rev in enumerate(r['reviews'][:2]):
            print(f"    review[{j}]: {rev['author']} | {rev['content'][:100]}...")
    return any(r['review_count'] > 0 for r in results)


def test_detail_only():
    print("\n" + "=" * 50)
    print("[测试3] 指定 tid 拉详情页")
    scraper = EebanScraper()
    # 已知的有效 tid（从之前调研获取）
    detail = scraper.fetch_detail("250330", max_replies=5)
    print(f"主帖长度: {len(detail.get('main_content', ''))} 字")
    print(f"回复数: {detail.get('total_replies', 0)}")
    print(f"解析回复: {len(detail.get('reviews', []))} 条")
    for rev in detail.get('reviews', [])[:3]:
        print(f"  · {rev['author'][:10]} | {rev['content'][:80]}...")
    return len(detail.get('reviews', [])) > 0


if __name__ == "__main__":
    print("保研论坛 eeban.com 集成测试\n")
    start = time.time()

    # 只测一个关键用例，避免过多请求
    result = test_detail_only()
    time.sleep(1.5)
    result2 = test_search_with_detail()

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"耗时: {elapsed:.1f}s")
    print(f"详情页测试: {'PASS' if result else 'FAIL'}")
    print(f"搜索+详情测试: {'PASS' if result2 else 'FAIL'}")
