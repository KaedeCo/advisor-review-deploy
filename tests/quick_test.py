"""快速测试保研论坛搜索特定姓名"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')

from app.services.crawlers.eeban import EebanScraper

s = EebanScraper()
r = s.search_with_detail('张三', '', fetch_details=True, max_threads=3)
print(f'结果数: {len(r)}')
for x in r:
    print(f'  title={x.get("title","")[:50]} reviews={x["review_count"]} source={x.get("source","")}')
