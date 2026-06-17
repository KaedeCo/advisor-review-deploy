"""
保研论坛 eeban.com 爬虫 — Discuz! X3.4 架构，全游客模式

搜索策略（v2）：
  1. 有院校 → 先搜索校名定位版块 fid → 版块内精确搜索（不去全局降级）
  2. 无院校 → 全局搜索
  3. 均无结果 → 由 search.py 路由层降级
"""

import time
import random
import re
import logging
from collections import Counter
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("eeban")

BASE_URL = "https://www.eeban.com"
SEARCH_EXTRA_KW = ["联系", "推荐", "选择", "面试", "套磁"]


class EebanScraper:
    """保研论坛爬虫 — 无登录/无验证码/无Cookie"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": BASE_URL,
        })
        self._last_request = 0.0
        self._fid_cache: dict[str, str] = {}

    # ═══════════════════════════════════════════════════════════
    #  版块定位 ─ 搜索校名 → 从结果提取最频 fid
    # ═══════════════════════════════════════════════════════════

    def _find_board_fid(self, university: str) -> Optional[str]:
        """
        搜索校名，从搜索结果中提取最常出现的版块 fid
        例: 搜"清华大学" → 多数结果来自 fid=XXX → 返回 XXX
        """
        if university in self._fid_cache:
            return self._fid_cache[university]

        logger.info("[fid] 定位院校版块: %s", university)
        self._rate_limit()

        url = f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes&srchtxt={quote(university)}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            items = _find_result_items(soup)

            fid_counter: Counter = Counter()
            for item in items:
                # 版块链接格式: forum-{fid}-1.html 或 forum.php?mod=forumdisplay&fid={fid}
                board_link = item.select_one(
                    "a[href*='forum-'], a[href*='forumdisplay'], a[href*='fid='], .xi1"
                )
                if board_link:
                    href = board_link.get("href", "")
                    m = re.search(r"forum-(\d+)-\d+\.html", href) or re.search(r"fid=(\d+)", href)
                    if m:
                        fid_counter[m.group(1)] += 1

            if fid_counter:
                fid, count = fid_counter.most_common(1)[0]
                logger.info("[fid] %s → fid=%s (%d/20 帖子来自此版块)",
                            university, fid, count)
                self._fid_cache[university] = fid
                return fid

            logger.info("[fid] %s → 未找到独立版块", university)
            return None

        except requests.RequestException as e:
            logger.warning("[fid] 请求异常: %s", e)
            return None

    # ═══════════════════════════════════════════════════════════
    #  主搜索接口
    # ═══════════════════════════════════════════════════════════

    def search(self, advisor_name: str, university: str = "") -> list[dict]:
        """
        搜索导师相关帖子
        - 有院校 → 先定位版块 fid → 版块内搜索（不去全局降级）
        - 无院校 → 全局搜索
        """
        fid: Optional[str] = None
        if university:
            fid = self._find_board_fid(university)

        queries = self._build_queries(advisor_name, university)
        all_results: list[dict] = []
        seen_tids: set[str] = set()

        for query in queries[:6]:
            results = self._search_threads(query, fid=fid)
            for r in results:
                tid = r.get("tid", "")
                if tid and tid not in seen_tids:
                    seen_tids.add(tid)
                    all_results.append(r)

            if len(all_results) >= 20:
                break
            time.sleep(random.uniform(1.5, 2.5))

        scope = f"fid={fid}" if fid else "全局"
        logger.info("保研论坛搜索完成: %s (%s) → %d 条 (%d 组查询)",
                     advisor_name, scope, len(all_results), len(queries))
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
    #  搜索帖子列表（支持版块限定）
    # ═══════════════════════════════════════════════════════════

    def _search_threads(self, keyword: str, fid: Optional[str] = None) -> list[dict]:
        """
        :param keyword: 搜索关键词
        :param fid: 版块 ID，有值则限定在该版块内搜索
        """
        self._rate_limit()

        if fid:
            url = (f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes"
                   f"&srchtxt={quote(keyword)}&srchfid[]={fid}")
        else:
            url = f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes&srchtxt={quote(keyword)}"

        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"
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
        """解析搜索结果页"""
        items = _find_result_items(soup)
        if not items:
            return []

        results = []
        for item in items:
            try:
                title_el = item.select_one("a.xst, a.s, h3 a, dt a, a[href*='tid=']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                tid = _extract_tid(href)
                if not tid:
                    continue

                snippet_el = item.select_one("dd, p.xg1, .p_content")
                snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""

                reply_count, view_count = _extract_counts(item)

                author_el = item.select_one("cite a, .authi a, .by a")
                author = author_el.get_text(strip=True) if author_el else "匿名"

                date_el = item.select_one("em span, .authi em, .xg1 span")
                date = date_el.get_text(strip=True) if date_el else ""

                detail_url = f"{BASE_URL}/forum.php?mod=viewthread&tid={tid}"

                results.append({
                    "title": title, "tid": tid, "author": author, "date": date,
                    "reply_count": reply_count, "view_count": view_count,
                    "snippet": snippet, "detail_url": detail_url,
                    "search_keyword": keyword,
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["reply_count"], reverse=True)
        return results

    # ═══════════════════════════════════════════════════════════
    #  获取帖子详情 + 回复
    # ═══════════════════════════════════════════════════════════

    def fetch_detail(self, tid: str, max_replies: int = 30) -> dict:
        self._rate_limit()
        url = f"{BASE_URL}/forum.php?mod=viewthread&tid={tid}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                logger.warning("详情页请求失败 HTTP %d for tid=%s", resp.status_code, tid)
                return {"reviews": [], "main_content": ""}

            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_thread_detail(soup, tid, max_replies)
        except requests.RequestException as e:
            logger.warning("详情页请求异常 tid=%s: %s", tid, e)
            return {"reviews": [], "main_content": ""}

    @staticmethod
    def _parse_thread_detail(soup: BeautifulSoup, tid: str, max_replies: int) -> dict:
        t_f_cells = soup.select("td.t_f")
        if not t_f_cells:
            return {"reviews": [], "main_content": "", "total_replies": 0}

        main_content = t_f_cells[0].get_text(" ", strip=True)
        reviews = []
        for cell in t_f_cells[1:max_replies + 1]:
            content = cell.get_text(" ", strip=True)
            if len(content) < 10:
                continue

            author = "匿名"
            parent = cell
            for _ in range(10):
                parent = parent.parent
                if parent is None:
                    break
                pid = parent.get("id", "")
                if pid and re.match(r"post", str(pid)):
                    authi = parent.select_one(".authi")
                    if authi:
                        author_link = authi.select_one("a.xw1")
                        if author_link and "只看" not in author_link.get_text():
                            author = author_link.get_text(strip=True)
                    break

            reviews.append({
                "author": author, "content": content[:1500], "date": "",
                "source": "eeban.com",
                "source_url": f"https://www.eeban.com/forum.php?mod=viewthread&tid={tid}",
            })

        return {
            "reviews": reviews, "main_content": main_content,
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
                    "source": "eeban.com",
                    "source_url": t.get("detail_url", ""),
                })

            results.append({
                "name": advisor_name,
                "university": university or "",
                "department": "",
                "overall_score": None,
                "review_count": len(all_reviews),
                "reviews": all_reviews,
                "source": "eeban_" + t.get("search_keyword", ""),
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


# ═══════════════════════════════════════════════════════════════
#  静态解析辅助函数
# ═══════════════════════════════════════════════════════════════

def _find_result_items(soup: BeautifulSoup):
    for selector in [
        "li[id^=thread]", "li.pbw", "li.bbda",
        "table[id^=thread_]", "dl.bbm",
    ]:
        items = soup.select(selector)
        if items and len(items) >= 3:
            return items
    return soup.select("li[id^=thread]") or []


def _extract_tid(href: str) -> str:
    m = re.search(r"tid=(\d+)", href)
    return m.group(1) if m else ""


def _extract_counts(item) -> tuple[int, int]:
    reply = view = 0
    text = item.get_text(" ", strip=True)
    m = re.search(r"(\d+)\s*(?:回复|回帖|个回复)", text)
    if m:
        reply = int(m.group(1))
    m = re.search(r"(\d+)\s*(?:查看|次查看|次浏览|浏览)", text)
    if m:
        view = int(m.group(1))
    return reply, view
