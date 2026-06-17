"""快速验证"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')
from app.services.crawlers.eeban import EebanScraper

s = EebanScraper()

# 验证1: fid定位
for uni in ["苏州大学", "武汉大学", "清华大学"]:
    fid = s._find_board_fid(uni)
    print(f"  {uni:8s} → fid={fid}")
    time.sleep(2)

# 验证2: 版块内搜索具体姓名
print("\n版块内搜索验证:")
r = s.search("孙嘉徽", "苏州大学")
print(f"  '孙嘉徽 苏州大学': {len(r)} 条")
for t in r[:3]:
    print(f"    [{t['tid']}] {t['title'][:50]}")
