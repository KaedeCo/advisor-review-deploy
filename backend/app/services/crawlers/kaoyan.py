"""
考研论坛 bbs.kaoyan.com 爬虫 — Discuz! X3.2，游客模式

搜索机制（非标准 DZ）:
  - POST 搜索 (非 GET)
  - 需要 formhash (从 /search.php 页面提取)
  - 编码: UTF-8 (GBK 会导致 0 结果)
  - 多词空格分隔 → AND 精确匹配 (通常 0 结果)
  → 策略: 单关键词搜索 → 本地按导师姓名/院校标题过滤

帖子URL: /forum.php?mod=viewthread&tid={tid}
内容选择器: td.t_f
反爬: 极低，无验证码，无频率限制
"""

import time
import random
import re
import logging
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("kaoyan")

BASE_URL = "http://bbs.kaoyan.com"
SEARCH_EXTRA_KW = ["导师", "推荐", "选择", "联系", "评价", "面试"]


class KaoyanScraper:
    """考研论坛爬虫 — 无需登录/无验证码"""

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
        self._formhash_cache: tuple[str, float] = ("", 0)  # (value, timestamp)

    # ═══════════════════════════════════════════════════════════
    #  formhash 管理
    # ═══════════════════════════════════════════════════════════

    def _get_formhash(self) -> str:
        """获取 formhash，带 60 秒缓存"""
        now = time.time()
        if self._formhash_cache[0] and (now - self._formhash_cache[1]) < 60:
            return self._formhash_cache[0]

        try:
            resp = self.session.get(f"{BASE_URL}/search.php", timeout=15)
            resp.encoding = "utf-8"
            m = re.search(r'name="formhash"\s+value="([^"]+)"', resp.text)
            if m:
                self._formhash_cache = (m.group(1), now)
                return m.group(1)
        except requests.RequestException as e:
            logger.warning("[formhash] 获取失败: %s", e)

        return ""

    # ═══════════════════════════════════════════════════════════
    #  主搜索入口
    # ═══════════════════════════════════════════════════════════

    def search(self, advisor_name: str, university: str = "") -> list[dict]:
        """
        搜索与导师相关的帖子

        考研论坛多词搜索返回 0 结果，所以策略是:
          1. 用 advisor_name 单关键词搜索
          2. 附加"导师"关键词搜索
          3. 在本地按 university 过滤标题
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

            if len(all_results) >= 25:
                break
            time.sleep(random.uniform(1.5, 2.5))

        logger.info("考研论坛搜索完成: %s (%s) → %d 条 (%d 组查询)",
                     advisor_name, university, len(all_results), len(queries))
        return all_results

    def _build_queries(self, name: str, university: str) -> list[str]:
        """构建搜索关键词列表（全部为单关键词）"""
        queries = [name]
        # 附加扩展关键词形成新查询（单关键词）
        for kw in SEARCH_EXTRA_KW:
            # 每轮只用一个扩展词
            queries.append(kw)
        return queries

    # ═══════════════════════════════════════════════════════════
    #  搜索帖子列表
    # ═══════════════════════════════════════════════════════════

    def _search_threads(self, keyword: str, page: int = 1) -> list[dict]:
        """
        POST 搜索单个关键词

        搜索端点: /search.php?mod=forum&searchsubmit=yes
        参数: formhash, srchtxt, searchsubmit=true, srchtype=title
        """
        self._rate_limit()

        formhash = self._get_formhash()
        if not formhash:
            logger.warning("[search] 无 formhash，跳过")
            return []

        data = {
            "formhash": formhash,
            "srchtxt": keyword,
            "searchsubmit": "true",
            "srchtype": "title",
        }
        if page > 1:
            data["page"] = str(page)

        try:
            resp = self.session.post(
                f"{BASE_URL}/search.php?mod=forum&searchsubmit=yes",
                data=data, timeout=15,
            )
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                logger.warning("[search] HTTP %d for '%s'", resp.status_code, keyword)
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_search_results(soup, keyword)

        except requests.RequestException as e:
            logger.warning("[search] 请求异常 '%s': %s", keyword, e)
            return []

    @staticmethod
    def _parse_search_results(soup: BeautifulSoup, keyword: str) -> list[dict]:
        """解析搜索结果页 — 标准 Discuz! 选择器"""
        items = soup.select(".pbw, li.bbda, li[id^=thread], dl.bbm, li.pbw")
        if not items:
            return []

        results = []
        for item in items:
            try:
                title_el = (
                    item.select_one("a.xst") or
                    item.select_one("a.s") or
                    item.select_one("h3 a") or
                    item.select_one("a[href*='tid=']")
                )
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if len(title) < 3:
                    continue

                href = title_el.get("href", "")
                tid_match = re.search(r"tid=(\d+)", href)
                if not tid_match:
                    continue
                tid = tid_match.group(1)

                # 版块
                board_el = (
                    item.select_one("a[href*='forumdisplay']") or
                    item.select_one(".xi1 a")
                )
                board = board_el.get_text(strip=True) if board_el else ""

                # 作者
                author_el = (
                    item.select_one("cite a") or
                    item.select_one(".authi a") or
                    item.select_one(".by a")
                )
                author = author_el.get_text(strip=True) if author_el else "匿名"

                # 时间
                date_el = (
                    item.select_one("em span") or
                    item.select_one(".authi em") or
                    item.select_one(".xg1 span")
                )
                date = date_el.get_text(strip=True) if date_el else ""

                # 片段
                snippet_el = (
                    item.select_one("dd") or
                    item.select_one("p.xg1") or
                    item.select_one(".p_content")
                )
                snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""

                # 回复/查看数
                reply_count, view_count = _extract_counts(item)

                detail_url = f"{BASE_URL}/forum.php?mod=viewthread&tid={tid}"

                results.append({
                    "title": title,
                    "tid": tid,
                    "author": author,
                    "date": date,
                    "board": board,
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

    def fetch_detail(self, tid: str, max_replies: int = 30, max_retries: int = 2) -> dict:
        self._rate_limit()

        url = f"{BASE_URL}/forum.php?mod=viewthread&tid={tid}"
        for attempt in range(max_retries + 1):
            try:
                resp = self.session.get(url, timeout=15)
                resp.encoding = "utf-8"

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    return self._parse_thread_detail(soup, tid, max_replies)

                # 5xx 临时错误 → 重试
                if 500 <= resp.status_code < 600 and attempt < max_retries:
                    logger.info("[detail] HTTP %d tid=%s, 重试 %d/%d",
                                resp.status_code, tid, attempt + 1, max_retries)
                    time.sleep(2)
                    continue

                logger.warning("[detail] HTTP %d for tid=%s", resp.status_code, tid)
                return {"reviews": [], "main_content": "", "total_replies": 0}

            except requests.RequestException as e:
                if attempt < max_retries:
                    logger.info("[detail] 请求异常 tid=%s, 重试 %d/%d: %s",
                                tid, attempt + 1, max_retries, e)
                    time.sleep(2)
                    continue
                logger.warning("[detail] 请求异常 tid=%s: %s", tid, e)
                return {"reviews": [], "main_content": "", "total_replies": 0}

    @staticmethod
    def _parse_thread_detail(soup: BeautifulSoup, tid: str, max_replies: int) -> dict:
        """解析帖子详情 — td.t_f 定位正文"""
        t_f_cells = soup.select("td.t_f")
        if not t_f_cells:
            return {"reviews": [], "main_content": "", "total_replies": 0}

        # 第1个 td.t_f = 主帖正文
        main_content = t_f_cells[0].get_text(" ", strip=True)

        # 其余 = 回复
        reviews = []
        for cell in t_f_cells[1:max_replies + 1]:
            content = cell.get_text(" ", strip=True)
            if len(content) < 10:
                continue

            # 定位作者：往上找父级中的 .authi 用户链接
            author = "匿名"
            parent = cell
            for _ in range(10):
                parent = parent.parent
                if parent is None:
                    break
                authi = parent.select_one(".authi")
                if authi:
                    user_link = authi.select_one("a.xw1")
                    if user_link and "只看" not in user_link.get_text():
                        author = user_link.get_text(strip=True)
                    break

            reviews.append({
                "author": author,
                "content": content[:1500],
                "date": "",
                "source": "bbs.kaoyan.com",
                "source_url": f"http://bbs.kaoyan.com/forum.php?mod=viewthread&tid={tid}",
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
                           fetch_details: bool = True, max_threads: int = 10) -> list[dict]:
        """
        组合搜索+详情，返回 AdvisorResult 兼容格式

        策略:
          1. 搜索 advisor_name 本身
          2. 如果结果不足，搜索"导师"扩大范围
          3. 本地过滤: 标题/版块含 university 关键词 → 保留
          4. 获取详情页内容
        """
        threads = self.search(advisor_name, university)
        results = []

        # 本地过滤: 按院校名称过滤
        if university:
            filtered = []
            for t in threads:
                title_and_board = (t.get("title", "") + " " + t.get("board", "")).lower()
                univ_parts = university.strip().split()
                # 只要匹配到院校名中任意关键词即保留
                if any(part in title_and_board for part in univ_parts):
                    filtered.append(t)
            # 如果过滤后太少，保留原始结果
            if len(filtered) >= 3:
                threads = filtered
            else:
                logger.info("[kaoyan] 院校过滤后仅 %d 条，保留全部 %d 条原始结果",
                            len(filtered), len(threads))

        for t in threads[:max_threads]:
            tid = t.get("tid", "")
            detail = {}
            if fetch_details and tid:
                detail = self.fetch_detail(tid)
                time.sleep(random.uniform(0.8, 1.5))

            all_reviews = detail.get("reviews", [])
            main_content = detail.get("main_content", "")
            if len(main_content) > 20:
                all_reviews.insert(0, {
                    "author": t.get("author", "匿名"),
                    "content": main_content[:2000],
                    "date": t.get("date", ""),
                    "source": "bbs.kaoyan.com",
                    "source_url": t.get("detail_url", ""),
                })

            results.append({
                "name": advisor_name,
                "university": university or "",
                "department": "",
                "overall_score": None,
                "review_count": len(all_reviews),
                "reviews": all_reviews,
                "source": "kaoyan_" + t.get("search_keyword", ""),
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


def _extract_counts(item) -> tuple[int, int]:
    """从搜索结果条目文本中提取回复数/浏览数"""
    text = item.get_text(" ", strip=True)
    reply = view = 0
    rm = re.search(r"(\d+)\s*回复", text)
    if rm:
        reply = int(rm.group(1))
    vm = re.search(r"(\d+)\s*查看", text)
    if vm:
        view = int(vm.group(1))
    return reply, view
