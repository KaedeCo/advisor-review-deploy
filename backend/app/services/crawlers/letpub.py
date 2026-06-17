"""
LetPub (letpub.com.cn) 爬虫 — 国自然基金查询

纯 requests 实现，无需 Playwright。
搜索端点: POST /nsfcfund_search.php?mode=advanced&datakind=list&currentpage=1
认证方式: PHPSESSID Cookie
关键参数: startTime=1997, endTime=2023（默认 2023-2023 太窄）
"""

import asyncio
import json
import logging
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("letpub")


class LetPubScraper:
    BASE_URL = "https://www.letpub.com.cn"
    SEARCH_URL = f"{BASE_URL}/index.php?page=grant"
    AJAX_URL = f"{BASE_URL}/nsfcfund_search.php"

    def __init__(self):
        self._phpsessid = self._load_phpsessid()

    @staticmethod
    def _load_phpsessid() -> str:
        try:
            config_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("cookies", {}).get("letpub", "").strip()
        except Exception:
            pass
        return ""

    async def search(self, advisor_name: str, university: str = "", max_pages: int = 3) -> list[dict]:
        """异步搜索（在线程池中执行同步 requests）"""
        return await asyncio.to_thread(self._search_sync, advisor_name, university, max_pages)

    def _search_sync(self, advisor_name: str, university: str, max_pages: int) -> list[dict]:
        """同步搜索实现"""
        if not self._phpsessid:
            logger.warning("[LetPub] 未配置 PHPSESSID，搜索可能无结果")

        cookies = {"PHPSESSID": self._phpsessid}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.SEARCH_URL,
            "X-Requested-With": "XMLHttpRequest",
        }

        sess = requests.Session()
        sess.headers.update(headers)

        try:
            # 1. 先访问搜索页（维持会话）
            sess.get(self.SEARCH_URL, cookies=cookies, timeout=15)

            # 2. POST 搜索
            data = {
                "page": "",
                "name": "",
                "person": advisor_name,
                "no": "",
                "company": university,
                "addcomment_s1": "",
                "addcomment_s2": "",
                "addcomment_s3": "",
                "addcomment_s4": "",
                "money1": "",
                "money2": "",
                "startTime": "1997",
                "endTime": "2023",
                "subcategory": "",
                "province_main": "",
                "searchsubmit": "true",
            }

            logger.info("[LetPub] 搜索: %s (%s)", advisor_name, university)

            all_projects = []
            for pg in range(1, max_pages + 1):
                url = f"{self.AJAX_URL}?mode=advanced&datakind=list&currentpage={pg}"
                resp = sess.post(url, data=data, cookies=cookies, timeout=15)

                if resp.status_code != 200:
                    logger.warning("[LetPub] HTTP %d on page %d", resp.status_code, pg)
                    break

                projects = self._parse_response(resp.text)
                if not projects:
                    break

                all_projects.extend(projects)

                # 检查是否还有更多页
                total = self._extract_total_count(resp.text)
                if total <= pg * 10:
                    break

                # 翻页时更新 currentpage
                data["currentpage"] = str(pg + 1)

            if not all_projects:
                logger.info("[LetPub] 无基金数据")
                return []

            logger.info("[LetPub] %d 个基金项目", len(all_projects))
            return _format(all_projects, advisor_name, university)

        except Exception as e:
            logger.warning("[LetPub] 搜索异常: %s", e)
            return []

    @staticmethod
    def _extract_total_count(html: str) -> int:
        m = re.search(r"匹配[：:]\s*<b>(\d+)</b>条", html)
        if m:
            return int(m.group(1))
        return 0

    @staticmethod
    def _parse_response(html: str) -> list[dict]:
        """解析 AJAX 返回的 HTML 中的表格数据"""
        soup = BeautifulSoup(html, "lxml")

        # AJAX 返回的 HTML 中表格没有 id，找第一个有数据的 table
        table = soup.find("table", id="keyword-datalist")
        if not table:
            table = soup.find("table")
        if not table:
            return []

        # 提取表头
        headers = []
        ths = table.find_all("th")
        if ths:
            headers = [th.get_text(strip=True) for th in ths]

        projects = []
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) < 5:
                continue

            cols = [td.get_text(strip=True) for td in tds]
            if not any(cols):
                continue

            p = {}
            for i, h in enumerate(headers):
                if i >= len(cols):
                    break
                if "负责人" in h:
                    p["pi_name"] = cols[i]
                elif "单位" in h or "依托" in h:
                    p["org_name"] = cols[i]
                elif "金额" in h or "经费" in h or "资助" in h:
                    p["amount_text"] = cols[i]
                    m = re.search(r"([\d.]+)", cols[i])
                    p["amount_wan"] = float(m.group(1)) if m else 0.0
                elif "编号" in h or "批准号" in h:
                    p["project_code"] = cols[i]
                elif "类型" in h or "类别" in h:
                    p["category"] = cols[i]
                elif "年份" in h or "年度" in h or "时间" in h:
                    p["start_year"] = cols[i]

            if p:
                projects.append(p)

        return projects


# ── 结果格式化 ─────────────────────────────────────────

def _format(projects: list[dict], name: str, univ: str) -> list[dict]:
    if not projects:
        return []
    total = sum(p.get("amount_wan", 0) for p in projects)
    reviews = []
    for p in projects:
        reviews.append({
            "author": "NSFC",
            "rating": _score(total, len(projects)),
            "date": p.get("start_year", ""),
            "content": f"[{p.get('category', 'NSFC')}] {p.get('project_code', '')} | {p.get('amount_text', '')}万 | {p.get('org_name', '')}",
            "source": "LetPub",
            "source_url": LetPubScraper.SEARCH_URL,
        })
    return [{
        "name": name,
        "university": univ or projects[0].get("org_name", ""),
        "department": "",
        "overall_score": _score(total, len(projects)),
        "review_count": len(reviews),
        "reviews": reviews,
        "source": "letpub",
        "detail_url": LetPubScraper.SEARCH_URL,
    }]


def _score(total_wan: float, count: int) -> float:
    if total_wan > 500: return 9.0
    if total_wan > 200: return 7.5
    if total_wan > 100: return 6.0
    if total_wan > 50: return 4.5
    return 3.0 if count > 0 else 0
