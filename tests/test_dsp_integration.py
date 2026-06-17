"""导师评价网集成测试"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')
from app.services.crawlers.daoshipingjia import DaoshiPingjiaScraper

s = DaoshiPingjiaScraper()
start = time.time()

# 测试1: 精确查找
print("=== 测试1: 孙立峰 + 清华大学 + 计算机科学与技术系 ===")
r = s.search("孙立峰", "清华大学", "计算机科学与技术系")
print(f"结果: {len(r)} 条")
for x in r:
    print(f"  {x['name']} | 评分: {x['overall_score']} | 评价: {x['review_count']}")
    for rev in x['reviews']:
        print(f"    [{rev['author'][:12]}] {rev['content'][:100]}")

# 测试2: 模糊院系名
print(f"\n=== 测试2: 孙立峰 + 清华大学 + 计算机（模糊）===")
s2 = DaoshiPingjiaScraper()
r2 = s2.search("孙立峰", "清华大学", "计算机")
print(f"结果: {len(r2)} 条")
for x in r2:
    print(f"  {x['name']} | 评分: {x['overall_score']}")

# 测试3: 不存在的人
print(f"\n=== 测试3: 不存在的人 + 清华大学 ===")
r3 = s.search("不存在的导师名", "清华大学", "计算机科学与技术系")
print(f"结果: {len(r3)} 条 (预期 0)")

elapsed = time.time() - start
print(f"\n耗时: {elapsed:.1f}s")
