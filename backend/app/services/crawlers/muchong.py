"""
小木虫 muchong.com 爬虫 — Discuz! 高度定制版，游客模式

搜索参数: wd (非 searchtext), fid, order
帖子URL: /t-{tid}-{page} (非 viewthread.php)
编码: gbk
无需 Cookie

降级策略（与保研论坛一致）:
  精确搜索导师姓名 → 0结果 → 降级为搜索校名（全局）
"""

import time
import random
import re
import logging
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("muchong")

BASE_URL = "https://muchong.com"
SEARCH_EXTRA_KW = ["联系", "推荐", "选择", "面试", "评价", "导师"]


class MuchongScraper:
    """小木虫爬虫 — 无登录/无验证码/无Cookie"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": BASE_URL,
        })
        self._last_request = 0.0

    # ═══════════════════════════════════════════════════════════
    #  搜索接口
    # ═══════════════════════════════════════════════════════════

    def search(self, advisor_name: str, university: str = "") -> list[dict]:
        """
        搜索小木虫中与导师相关的帖子
        小木虫不支持版块限定搜索（fid 在 wd 搜索中无效），所以走全局搜索
        """
        queries = self._build_queries(advisor_name, university)
        all_results: list[dict] = []
        seen_tids: set[str] = set()

        for query in queries[:6]:
            results = self._search_threads(query)
            for r in results:
                tid = r.get("tid", "")
                if tid and tid not in seen_tids:
                    seen_tids.add(tid)
                    all_results.append(r)

            if len(all_results) >= 20:
                break
            time.sleep(random.uniform(1.5, 2.5))

        logger.info("小木虫搜索完成: %s → %d 条 (%d 组查询)",
                     advisor_name, len(all_results), len(queries))
        return all_results

    def _build_queries(self, name: str, university: str) -> list[str]:
        queries = [name]
        if university:
            queries.append(f"{name} {university}")
        for kw in SEARCH_EXTRA_KW:
            q = f"{name} {kw}"
            if university:
                q = f"{name} {university} {kw}"
            queries.append(q)
        return queries

    # ═══════════════════════════════════════════════════════════
    #  搜索帖子列表
    # ═══════════════════════════════════════════════════════════

    def _search_threads(self, keyword: str) -> list[dict]:
        self._rate_limit()

        url = (f"{BASE_URL}/bbs/search.php"
               f"?searchsubmit=yes&wd={quote(keyword)}&fid=0&order=2")
        try:
            resp = self.session.get(url, timeout=20)
            resp.encoding = "gbk"

            if resp.status_code != 200:
                logger.warning("搜索请求失败 HTTP %d", resp.status_code)
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_search_results(soup, keyword)

        except requests.RequestException as e:
            logger.warning("搜索请求异常: %s", e)
            return []

    @staticmethod
    def _parse_search_results(soup: BeautifulSoup, keyword: str) -> list[dict]:
        """解析搜索结果 — 提取 /t-{tid}-{page} 格式链接"""
        t_links = soup.find_all("a", href=re.compile(r"/t-\d+-\d+"))
        if not t_links:
            return []

        results = []
        for a in t_links:
            try:
                text = a.get_text(strip=True)
                if len(text) < 3:
                    continue  # 跳过"清除COOKIES"等干扰链接

                href = a["href"]
                m = re.search(r"/t-(\d+)-(\d+)", href)
                if not m:
                    continue
                tid, page = m.group(1), m.group(2)

                # 尝试提取父级的回复/查看信息
                parent = a.parent
                snippet = ""
                reply_count = 0
                view_count = 0
                for _ in range(3):
                    parent = parent.parent if parent else None
                    if parent is None:
                        break
                    # 查找计数信息
                    parent_text = parent.get_text(" ", strip=True)
                    rm = re.search(r"(\d+)\s*/\s*(\d+)", parent_text)
                    if rm:
                        view_count = int(rm.group(1))
                        reply_count = int(rm.group(2))
                        break

                detail_url = f"{BASE_URL}/t-{tid}-1"

                results.append({
                    "title": text,
                    "tid": tid,
                    "author": "",
                    "date": "",
                    "reply_count": reply_count,
                    "view_count": view_count,
                    "snippet": snippet,
                    "detail_url": detail_url,
                    "search_keyword": keyword,
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["reply_count"], reverse=True)
        return results

    # ═══════════════════════════════════════════════════════════
    #  帖子详情页
    # ═══════════════════════════════════════════════════════════

    def fetch_detail(self, tid: str, max_replies: int = 30) -> dict:
        self._rate_limit()

        url = f"{BASE_URL}/t-{tid}-1"
        try:
            resp = self.session.get(url, timeout=20)
            resp.encoding = "gbk"

            if resp.status_code != 200:
                logger.warning("详情页请求失败 HTTP %d tid=%s", resp.status_code, tid)
                return {"reviews": [], "main_content": ""}

            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_thread_detail(soup, tid, max_replies)

        except requests.RequestException as e:
            logger.warning("详情页请求异常 tid=%s: %s", tid, e)
            return {"reviews": [], "main_content": ""}

    @staticmethod
    def _parse_thread_detail(soup: BeautifulSoup, tid: str, max_replies: int) -> dict:
        """解析帖子详情页 — div[class*='t_f'] 定位所有正文"""
        t_f_cells = soup.select("div[class*='t_f']")
        if not t_f_cells:
            return {"reviews": [], "main_content": "", "total_replies": 0}

        # 第1个 div.t_f = 主帖正文
        main_content = t_f_cells[0].get_text(" ", strip=True)

        # 其余 = 回复
        reviews = []
        for cell in t_f_cells[1:max_replies + 1]:
            content = cell.get_text(" ", strip=True)
            if len(content) < 10:
                continue

            # 定位作者：往上找父级中的用户链接
            author = "匿名"
            parent = cell
            for _ in range(10):
                parent = parent.parent
                if parent is None:
                    break
                user_link = parent.select_one("a[href*='space-uid'], a[onclick*='space']")
                if user_link:
                    author = user_link.get_text(strip=True)
                    break

            reviews.append({
                "author": author,
                "content": content[:1500],
                "date": "",
                "source": "muchong.com",
                "source_url": f"https://muchong.com/t-{tid}-1",
            })

        return {
            "reviews": reviews,
            "main_content": main_content,
            "total_replies": max(len(t_f_cells) - 1, 0),
        }

    # ═══════════════════════════════════════════════════════════
    #  搜索 + 详情 → AdvisorResult
    # ═══════════════════════════════════════════════════════════

    def search_with_detail(self, advisor_name: str, university: str = "",
                           fetch_details: bool = True, max_threads: int = 8) -> list[dict]:
        threads = self.search(advisor_name, university)
        results = []
        for t in threads[:max_threads]:
            tid = t.get("tid", "")
            detail = {}
            if fetch_details and tid:
                detail = self.fetch_detail(tid)

            all_reviews = detail.get("reviews", [])
            main_content = detail.get("main_content", "")
            if len(main_content) > 20:
                all_reviews.insert(0, {
                    "author": t.get("author", "匿名"),
                    "content": main_content[:2000],
                    "date": t.get("date", ""),
                    "source": "muchong.com",
                    "source_url": t.get("detail_url", ""),
                })

            results.append({
                "name": advisor_name,
                "university": university or "",
                "department": "",
                "overall_score": None,
                "review_count": len(all_reviews),
                "reviews": all_reviews,
                "source": "muchong_" + t.get("search_keyword", ""),
                "detail_url": t.get("detail_url", ""),
                "title": t.get("title", ""),
            })
        return results

    # ═══════════════════════════════════════════════════════════
    #  辅助
    # ═══════════════════════════════════════════════════════════

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed + random.uniform(0, 1))
        self._last_request = time.time()
