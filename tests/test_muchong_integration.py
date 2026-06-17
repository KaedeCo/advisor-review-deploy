"""小木虫集成测试"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')

from app.services.crawlers.muchong import MuchongScraper

s = MuchongScraper()

start = time.time()

# 测试1: 搜索+详情
print("=== 测试1: 搜索'导师评价' + 拉详情 (3条) ===")
r = s.search_with_detail("导师评价", "", fetch_details=True, max_threads=3)
print(f"结果: {len(r)} 条")
for x in r:
    print(f"  [{x['source']}] {x.get('title','')[:50]} | reviews={x['review_count']}")
    for rev in x['reviews'][:2]:
        print(f"    · {rev['author'][:10]} | {rev['content'][:80]}")

# 测试2: 单独详情页
print(f"\n=== 测试2: 详情页 t-16723080-1 ===")
d = s.fetch_detail("16723080", max_replies=5)
print(f"主帖: {d['main_content'][:100]}")
print(f"回复: {len(d['reviews'])} 条")
for rev in d['reviews'][:3]:
    print(f"  · {rev['author'][:10]} | {rev['content'][:80]}")

# 测试3: 降级场景
print(f"\n=== 测试3: 搜索不存在的名字'测试人' ===")
r3 = s.search("测试人不存在", "")
print(f"结果: {len(r3)} 条（预期 0）")

elapsed = time.time() - start
print(f"\n耗时: {elapsed:.1f}s")
