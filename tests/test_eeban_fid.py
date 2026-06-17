"""测试版块限定搜索"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')

from app.services.crawlers.eeban import EebanScraper

s = EebanScraper()

# 测试1: fid 定位
print("=== 测试1: 搜索校名定位版块 fid ===")
fid = s._find_board_fid("苏州大学")
print(f"结果: fid={fid}")

# 测试2: 有院校的搜索
print("\n=== 测试2: 搜索'苏州大学 医学 辐射防护'（版块限定）===")
r = s.search_with_detail("医学", "苏州大学", fetch_details=False, max_threads=3)
print(f"结果: {len(r)} 条")
for x in r:
    print(f"  {x.get('title','')[:50]} | reviews={x['review_count']}")

# 测试3: 版块内直接搜索导师名
print("\n=== 测试3: 版块内搜'教授' ===")
if fid:
    threads = s._search_threads("教授", fid=fid)
    print(f"结果: {len(threads)} 条")
    for t in threads[:5]:
        print(f"  [{t['tid']}] {t['title'][:50]} | 回复:{t['reply_count']}")

print("\n=== 完成 ===")
