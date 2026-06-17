import sys,io;sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8');sys.path.insert(0,'backend')
from app.services.crawlers.pireview import PIReviewScraper
s=PIReviewScraper()
r=s.search('Zhang Liang')
print(f'Results: {len(r)}')
for x in r:
    print(f'  {x["name"][:30]} score:{x["overall_score"]} reviews:{x["review_count"]} uni:{x["university"][:30]}')
    for rev in x["reviews"][:2]:
        print(f'    [{rev["author"][:15]}] {rev["content"][:100]}')
