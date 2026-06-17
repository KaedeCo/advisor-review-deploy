"""
导师评价网 daoshipingjia.net 爬虫 — 树状导航按需查找

流程（每次搜索约 4 次 HTTP 请求）:
  1. /schools → 匹配学校名 → 学校URL
  2. /schools/{学校} → 匹配院系名 → 院系URL
  3. /schools/{学校}/{院系} → 匹配导师名 → /teacher/{id}
  4. /teacher/{id} → 评分 + AI总结

特点: 无验证码/无Cookie/无登录/全SSR
限制: 低分导师(≤3.8)姓名隐藏，评价原文需会员
"""

import re
import time
import random
import logging
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("daoshipingjia")

BASE_URL = "https://daoshipingjia.net"


class DaoshiPingjiaScraper:
    """导师评价网爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self._last_request = 0.0

    # ═══════════════════════════════════════════════════════════
    #  主接口 — 返回 AdvisorResult 格式
    # ═══════════════════════════════════════════════════════════

    def search(self, advisor_name: str, university: str = "",
               department: str = "") -> list[dict]:
        """
        按需查找导师
        返回 list[dict] 与 gradchoice/eeban 格式兼容
        """
        results = []

        # Step 1: 匹配学校
        school_url = self._match_school(university) if university else None
        if university and not school_url:
            logger.info("未匹配到学校: %s", university)
            return []

        # Step 2: 匹配院系 + 导师
        advisors = []

        if school_url and department:
            # 有院系：直接定位
            dept_url = self._match_department(school_url, department)
            if dept_url:
                advisors = self._match_advisors(dept_url, advisor_name)
            else:
                logger.info("未匹配到院系: %s", department)
                return []

        elif school_url:
            # 无院系：遍历学校所有院系查找导师（取前 10 个）
            logger.info("无院系信息，遍历学校院系查找: %s", advisor_name)
            dept_urls = self._list_departments(school_url)
            for dept_url in dept_urls[:10]:
                advs = self._match_advisors(dept_url, advisor_name)
                if advs:
                    advisors = advs
                    break

        else:
            # 无学校 → 无法查找
            return []

        if not advisors:
            logger.info("未精确匹配到导师: %s", advisor_name)
            return []

        # Step 4: 拉取详情
        for adv in advisors[:5]:
            detail = self._fetch_teacher_detail(adv["teacher_id"])
            adv.update(detail)

        return [self._to_result(adv) for adv in advisors[:3]]

    # ═══════════════════════════════════════════════════════════
    #  search_with_detail — 兼容路由层调度
    # ═══════════════════════════════════════════════════════════

    def search_with_detail(self, advisor_name: str, university: str = "",
                           fetch_details: bool = True, max_threads: int = 5,
                           department: str = "") -> list[dict]:
        return self.search(advisor_name, university, department)

    # ═══════════════════════════════════════════════════════════
    #  Step 1: 匹配学校
    # ═══════════════════════════════════════════════════════════

    def _match_school(self, university: str) -> Optional[str]:
        """从 /schools 中匹配学校名 → /schools/{编码名}"""
        self._rate_limit()
        try:
            r = self.session.get(f"{BASE_URL}/schools", timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a", href=re.compile(r"^/schools/[^/]+$"))
            # 排除页脚链接（隐私政策等）
            school_candidates = []
            for a in links:
                name = a.get_text(strip=True)
                href = a["href"]
                if len(name) < 3 or name in ("隐私政策", "用户协议", "免责声明"):
                    continue
                school_candidates.append((name, href))

            # 精确匹配 → 模糊匹配
            for name, href in school_candidates:
                if name == university:
                    logger.info("学校精确匹配: %s → %s", name, href)
                    return BASE_URL + href
            for name, href in school_candidates:
                if university in name or name in university:
                    logger.info("学校模糊匹配: %s ≈ %s → %s", university, name, href)
                    return BASE_URL + href

            logger.info("学校列表: %s", [n for n, _ in school_candidates])
            return None

        except requests.RequestException as e:
            logger.warning("学校页面请求失败: %s", e)
            return None

    # ═══════════════════════════════════════════════════════════
    #  Step 2: 匹配院系
    # ═══════════════════════════════════════════════════════════

    def _match_department(self, school_url: str, department: str) -> Optional[str]:
        """从学校页面中匹配院系名 → /schools/{学校}/{院系}"""
        self._rate_limit()
        try:
            r = self.session.get(school_url, timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            # 院系链接: /schools/{学校}/{院系}（比学校链接多一层）
            dept_links = []
            for a in soup.find_all("a", href=re.compile(r"/schools/[^/]+/[^/]+")):
                name = a.get_text(strip=True)
                href = a["href"]
                if len(name) > 1:
                    dept_links.append((name, href))

            # 去重
            seen = set()
            unique = []
            for n, h in dept_links:
                if n not in seen:
                    seen.add(n)
                    unique.append((n, h))
            dept_links = unique

            # 匹配
            for name, href in dept_links:
                if department in name or name in department:
                    logger.info("院系匹配: %s ≈ %s → %s", department, name, href)
                    return BASE_URL + href

            logger.info("院系列表(%d): %s", len(dept_links),
                         [n for n, _ in dept_links[:10]])
            return None

        except requests.RequestException as e:
            logger.warning("院系页面请求失败: %s", e)
            return None

    def _list_departments(self, school_url: str) -> list[str]:
        """从学校页面获取所有院系 URL（不去重）"""
        self._rate_limit()
        try:
            r = self.session.get(school_url, timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            urls = []
            for a in soup.find_all("a", href=re.compile(r"/schools/[^/]+/[^/]+")):
                href = a["href"]
                full = BASE_URL + href
                if full not in urls:
                    urls.append(full)
            logger.info("获取到 %d 个院系", len(urls))
            return urls
        except requests.RequestException as e:
            logger.warning("获取院系列表失败: %s", e)
            return []

    # ═══════════════════════════════════════════════════════════
    #  Step 3: 匹配导师
    # ═══════════════════════════════════════════════════════════

    def _match_advisors(self, page_url: str, advisor_name: str) -> list[dict]:
        """从院系(或学校)页面匹配导师名 → teacher_id 列表"""
        self._rate_limit()
        try:
            r = self.session.get(page_url, timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            candidates = []
            for a in soup.find_all("a", href=re.compile(r"/teacher/\d+")):
                raw_name = a.get_text(strip=True)
                href = a["href"]
                # 清理：去除评分、updated等数字杂讯
                name = re.sub(r"[\d.]+|updated:|[\d]{4}\.[\d]{2}", "", raw_name).strip()
                if len(name) < 2:
                    continue

                tid_match = re.search(r"/teacher/(\d+)", href)
                tid = tid_match.group(1) if tid_match else ""

                # 提取评分
                score = self._extract_nearby_score(a)

                candidates.append({
                    "name": name,
                    "teacher_id": tid,
                    "score": score,
                })

            # 匹配（链接文本含校名/院系名，用 in 匹配）
            matched = []
            for c in candidates:
                if advisor_name in c["name"] or c["name"] in advisor_name:
                    matched.append(c)

            if matched:
                logger.info("导师匹配: %d 位", len(matched))
            else:
                logger.info("导师列表(%d): %s", len(candidates),
                             [c["name"] for c in candidates[:15]])
            return matched

        except requests.RequestException as e:
            logger.warning("导师列表请求失败: %s", e)
            return []

    @staticmethod
    def _extract_nearby_score(link) -> Optional[float]:
        """从导师链接附近提取评分"""
        parent = link
        for _ in range(5):
            parent = parent.parent if parent else None
            if parent is None:
                break
            text = parent.get_text(" ", strip=True)
            m = re.search(r"\b(\d+\.\d+)\b", text)
            if m:
                score = float(m.group(1))
                if 0.5 <= score <= 5.0:  # 合理范围
                    return score
        return None

    # ═══════════════════════════════════════════════════════════
    #  Step 4: 导师详情
    # ═══════════════════════════════════════════════════════════

    def _fetch_teacher_detail(self, teacher_id: str) -> dict:
        """拉取导师详情页 → 评分 + AI总结 + 评价数"""
        self._rate_limit()
        try:
            r = self.session.get(f"{BASE_URL}/teacher/{teacher_id}", timeout=15)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)

            # 评分
            score = None
            score_m = re.search(r"(\d+\.?\d*)\s*/\s*5", text)
            if score_m:
                score = float(score_m.group(1))

            # 评价数 — 多条模式
            review_count = 0
            for pat in [r"(\d+)\s*条评价", r"共\s*(\d+)\s*人评价",
                         r"(\d+)\s*reviews?", r"(\d+)\s*人参与"]:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    review_count = int(m.group(1))
                    break

            # AI总结 — 找包含多个评价关键词的较长文本块
            ai_summary = ""
            best_len = 0
            for el in soup.find_all(["div", "p", "section", "span"]):
                t = el.get_text(" ", strip=True)
                if 30 < len(t) < 600:
                    kw_hits = sum(1 for kw in
                        ["老师", "指导", "导师", "实验室", "沟通",
                         "氛围", "毕业", "研究", "方向"]
                        if kw in t)
                    if kw_hits >= 2 and len(t) > best_len:
                        ai_summary = t
                        best_len = len(t)

            # 会员墙
            has_member_wall = any(kw in text for kw in
                ["升级会员", "会员专享", "需会员", "付费查看"])

            return {
                "score": score,
                "review_count": review_count,
                "ai_summary": ai_summary,
                "member_wall": has_member_wall,
            }

        except requests.RequestException as e:
            logger.warning("导师详情请求失败 id=%s: %s", teacher_id, e)
            return {"score": None, "review_count": 0, "ai_summary": "", "member_wall": True}

    # ═══════════════════════════════════════════════════════════
    #  转换为 AdvisorResult 格式
    # ═══════════════════════════════════════════════════════════

    def _to_result(self, adv: dict) -> dict:
        # 从含校名/院系的 raw_name 中提取纯导师名（中国姓名 2-3 字）
        raw_name = adv.get("name", "")
        clean_name = re.match(r"^([\u4e00-\u9fff]{2,3})", raw_name)
        name = clean_name.group(1) if clean_name else raw_name

        score = adv.get("score")
        # 映射到 1-10 分体系（原站 1-5）
        overall_score = (score * 2) if score else None

        reviews = []
        ai_summary = adv.get("ai_summary", "")
        if ai_summary:
            reviews.append({
                "author": "AI评价总结",
                "content": ai_summary,
                "date": "",
                "source": "daoshipingjia.net",
                "source_url": f"{BASE_URL}/teacher/{adv['teacher_id']}",
            })
        if adv.get("member_wall"):
            reviews.append({
                "author": "系统提示",
                "content": f"该导师共有 {adv.get('review_count', '?')} 条评价，原文需升级会员查看",
                "date": "",
                "source": "daoshipingjia.net",
                "source_url": f"{BASE_URL}/teacher/{adv['teacher_id']}",
            })

        return {
            "name": name,
            "university": "",
            "department": "",
            "overall_score": overall_score,
            "review_count": adv.get("review_count", 0),
            "reviews": reviews,
            "source": "daoshipingjia.net",
            "detail_url": f"{BASE_URL}/teacher/{adv['teacher_id']}",
        }

    # ═══════════════════════════════════════════════════════════
    #  辅助
    # ═══════════════════════════════════════════════════════════

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed + random.uniform(0, 0.5))
        self._last_request = time.time()
