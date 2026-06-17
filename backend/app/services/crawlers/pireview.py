"""
PI Review pi-review.com 爬虫 — SSR 传统架构，评价全公开

检索:
  /search/?q={name} → 导师列表 (10条/页)
  /pis/{id}          → 导师详情 + 五维评分 + 完整评价内容

特点: 免登录/无验证码/无Cloudflare/评价原文全公开
"""

import re
import time
import random
import logging
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("pireview")

BASE_URL = "https://pi-review.com"


class PIReviewScraper:
    """PI Review 爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self._last_request = 0.0

    # ═══════════════════════════════════════════════════════════
    #  主接口
    # ═══════════════════════════════════════════════════════════

    def search(self, advisor_name: str, university: str = "",
               department: str = "") -> list[dict]:
        """搜索导师 → 拉取详情 → 返回 AdisorResult 格式"""
        pis = self._search_pis(advisor_name)
        if not pis:
            return []

        # 按学校筛选（如有）
        if university:
            filtered = []
            for pi in pis:
                if university.lower() in pi.get("university", "").lower():
                    filtered.append(pi)
            if filtered:
                pis = filtered
            # 不强求匹配 — 搜索足够精确时仍返回

        results = []
        for pi in pis[:5]:
            detail = self._fetch_detail(pi["pi_id"])
            pi.update(detail)

        return [self._to_result(p) for p in pis[:3]]

    def search_with_detail(self, advisor_name: str, university: str = "",
                           fetch_details: bool = True, max_threads: int = 5) -> list[dict]:
        return self.search(advisor_name, university)

    # ═══════════════════════════════════════════════════════════
    #  搜索
    # ═══════════════════════════════════════════════════════════

    def _search_pis(self, name: str) -> list[dict]:
        """搜索导师列表"""
        self._rate_limit()
        try:
            r = self.session.get(
                f"{BASE_URL}/search/?q={quote(name)}", timeout=15
            )
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            pis = []
            for a in soup.find_all("a", href=re.compile(r"/pis/\d+$")):
                href = a["href"]
                pi_id = re.search(r"/pis/(\d+)", href).group(1)
                raw_text = a.get_text(" ", strip=True).strip()

                # 跳过非导师链接
                if len(raw_text) < 3:
                    continue

                # 提取父级中的学校名和评分
                parent = a.parent
                university = ""
                score = None
                review_count = 0

                for _ in range(6):
                    parent = parent.parent if parent else None
                    if parent is None:
                        break
                    ptext = parent.get_text(" ", strip=True)

                    # 评分
                    sm = re.search(r"(\d+\.\d+)\s*/\s*5", ptext)
                    if sm and score is None:
                        score = float(sm.group(1))

                    # 评价数
                    rm = re.search(r"(\d+)\s*人评价", ptext)
                    if rm:
                        review_count = int(rm.group(1))

                    # 学校名
                    if not university:
                        um = re.search(
                            r"([A-Z][\w\s&\-.,()]+(?:University|College|Institute|School)[^<]*)",
                            ptext
                        )
                        if um:
                            university = um.group(1).strip()[:80]

                pis.append({
                    "pi_id": pi_id,
                    "name": raw_text,
                    "university": university,
                    "score": score,
                    "review_count": review_count,
                })

            # 去重
            seen = set()
            unique = []
            for p in pis:
                if p["pi_id"] not in seen:
                    seen.add(p["pi_id"])
                    unique.append(p)

            logger.info("搜索 %s → %d 位导师", name, len(unique))
            return unique

        except requests.RequestException as e:
            logger.warning("搜索请求失败: %s", e)
            return []

    # ═══════════════════════════════════════════════════════════
    #  详情
    # ═══════════════════════════════════════════════════════════

    def _fetch_detail(self, pi_id: str) -> dict:
        """拉取导师详情页 → 评分 + 评价列表"""
        self._rate_limit()
        try:
            r = self.session.get(f"{BASE_URL}/pis/{pi_id}", timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)

            # 姓名
            name_m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*(?:\([^)]+\))?", text)
            name = name_m.group(1).strip() if name_m else ""

            # 评分
            score_m = re.search(r"(\d+\.\d+)\s*/\s*5", text)
            score = float(score_m.group(1)) if score_m else None

            # 评价数
            review_count = 0
            for pat in [r"(\d+)\s*人评价", r"(\d+)\s*(?:条评价|reviews?|点评)"]:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    review_count = int(m.group(1))
                    break

            # 学校
            school = ""
            um = re.search(r"([A-Z][\w\s&\-.,()]+(?:University|College|Institute)[^<,]{2,40})", text)
            if um:
                school = um.group(1).strip()

            # 解析评价列表 — 查找 Markdown 格式的评价内容块
            reviews = []
            # 评价通常以 "发布于:" 或 "##" 开头
            review_sections = re.split(
                r"(?:匿名|发表于|发布于|##\s+Advisor|##\s+导师)",
                text,
                flags=re.IGNORECASE,
            )

            for section in review_sections[1:]:  # 跳过第一个（页面头部）
                section = section.strip()
                if len(section) < 30:
                    continue

                # 提取评分标签
                rating_label = ""
                rm = re.match(r"(优秀|合格|不合格|Excellent|Good|Poor)", section)
                if rm:
                    rating_label = rm.group(1)
                    section = section[rm.end():].strip()

                # 提取日期
                date = ""
                dm = re.search(r"(\d{4}-\d{2}-\d{2})", section)
                if dm:
                    date = dm.group(1)

                # 清理文本: 去除残留的日期/元数据行
                content = re.sub(r"^[:\s]*\d{4}-\d{2}-\d{2}T[\d:Z]+\s*", "", section)
                content = re.sub(r"本院校邮箱|EDU\s*邮箱验证|查看原文.*", "", content)
                content = content.strip()

                if len(content) > 20:
                    reviews.append({
                        "author": f"匿名{(' ' + rating_label) if rating_label else ''}",
                        "content": content[:2000],
                        "date": date,
                        "source": "pi-review.com",
                        "source_url": f"{BASE_URL}/pis/{pi_id}",
                    })

            return {
                "name": name,
                "score": score,
                "review_count": review_count,
                "university": school,
                "reviews": reviews,
            }

        except requests.RequestException as e:
            logger.warning("详情请求失败 id=%s: %s", pi_id, e)
            return {"name": "", "score": None, "review_count": 0,
                    "university": "", "reviews": []}

    # ═══════════════════════════════════════════════════════════
    #  AdisorResult 格式
    # ═══════════════════════════════════════════════════════════

    def _to_result(self, pi: dict) -> dict:
        score = pi.get("score")
        overall_score = (score * 2) if score else None  # 5→10分制

        return {
            "name": pi.get("name", ""),
            "university": pi.get("university", ""),
            "department": "",
            "overall_score": overall_score,
            "review_count": pi.get("review_count", 0),
            "reviews": pi.get("reviews", []),
            "source": "pi-review.com",
            "detail_url": f"{BASE_URL}/pis/{pi.get('pi_id', '')}",
        }

    # ═══════════════════════════════════════════════════════════
    #  辅助
    # ═══════════════════════════════════════════════════════════

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < 0.8:
            time.sleep(0.8 - elapsed + random.uniform(0, 0.3))
        self._last_request = time.time()
