"""
考研论坛爬虫集成测试
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.crawlers.kaoyan import KaoyanScraper


def main():
    scraper = KaoyanScraper()

    print('[1] search(daoshi)')
    threads = scraper.search("导师")
    print(f'  results: {len(threads)}')
    assert len(threads) > 0
    for t in threads[:3]:
        print(f'  tid={t["tid"]} | [{t.get("board", "")}] {t["title"][:60]}')

    print('\n[2] search(sun+lifeng, tsinghua)')
    threads2 = scraper.search("孙立峰", "清华大学")
    print(f'  results: {len(threads2)}')

    print('\n[3] fetch_detail')
    if threads:
        tid = threads[0]["tid"]
        detail = scraper.fetch_detail(tid)
        print(f'  tid={tid}')
        print(f'  content_len: {len(detail.get("main_content", ""))}')
        print(f'  replies: {detail.get("total_replies", 0)}')
        assert len(detail.get("main_content", "")) > 10

    print('\n[4] search_with_detail(daoshi, tsinghua)')
    results = scraper.search_with_detail("导师", "清华大学", max_threads=3)
    print(f'  results: {len(results)}')
    for r in results[:2]:
        print(f'  source={r["source"]} | reviews={r["review_count"]} | title={r.get("title", "")[:50]}')

    print('\nall tests passed!')

if __name__ == "__main__":
    main()
