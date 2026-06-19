""""
GradChoice (gradchoice.org) 爬虫实现 — 双策略：HTML 解析 + SPA API 自动探测
"""

import time
import random
import re
import logging
import json as json_mod
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ...config import get_platform_cookie

logger = logging.getLogger("gradchoice")


class GradChoiceScraper:
    """研选 GradChoice 爬虫"""

    BASE_URL = "https://gradchoice.org"
    # SPA 空壳判断阈值（小于此值的 HTML 响应视为 JS 渲染框架）
    SPA_SHELL_THRESHOLD = 5000

    def __init__(self, access_token: str = ""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.BASE_URL,
        })
        self._auth_mode = "none"
        auth_value = access_token or get_platform_cookie("gradchoice")
        if auth_value:
            auth_value = auth_value.strip()
            jwt_token = self._extract_raw_jwt(auth_value)
            if jwt_token:
                self.session.headers["Authorization"] = f"Bearer {jwt_token}"
                self._auth_mode = "jwt"
                logger.info("认证模式: JWT Bearer Token (前10位: %s...)", jwt_token[:10])
            else:
                for item in auth_value.split(";"):
                    item = item.strip()
                    if "=" in item:
                        k, v = item.split("=", 1)
                        self.session.cookies.set(k.strip(), v.strip())
                self._auth_mode = "cookie"
                logger.info("认证模式: 传统 Cookie")
        else:
            logger.warning("未配置认证信息，将以游客模式请求")

    # ═══════════════════════════════════════════════════════════
    #  Token 验证
    # ═══════════════════════════════════════════════════════════

    def verify_token(self) -> dict:
        """验证 Access Token 是否有效"""
        test_url = f"{self.BASE_URL}/search"
        test_params = {"keyword": "test_verify_only", "school": ""}
        logger.info("[验证] %s params=%s", test_url, test_params)

        try:
            resp = self.session.get(test_url, params=test_params, timeout=15, allow_redirects=False)
            resp.encoding = "utf-8"
            status, content_len = resp.status_code, len(resp.text)
            logger.info("[验证] HTTP %d | %d bytes", status, content_len)

            if status == 401 or status == 403:
                return {"valid": False, "status_code": status,
                        "detail": f"Token 无效或已过期 (HTTP {status})", "url": test_url}
            if status != 200:
                return {"valid": False, "status_code": status,
                        "detail": f"服务器返回异常状态码: {status}", "url": test_url}

            text_lower = resp.text.lower()
            for kw in ['login', 'signin', '登录', '请先登录']:
                if kw in text_lower:
                    return {"valid": False, "status_code": status,
                            "detail": "Token 未生效，服务器返回了登录页面", "url": test_url}

            logger.info("[验证] Token 有效")
            return {"valid": True, "status_code": status,
                    "detail": f"Token 有效 (HTTP {status}, {content_len} bytes)", "url": test_url}

        except requests.ConnectionError as e:
            return {"valid": False, "status_code": 0,
                    "detail": f"无法连接: {e}", "url": test_url}
        except requests.Timeout:
            return {"valid": False, "status_code": 0,
                    "detail": "请求超时", "url": test_url}
        except Exception as e:
            logger.error("[验证] 错误: %s", e)
            return {"valid": False, "status_code": 0,
                    "detail": f"验证出错: {e}", "url": test_url}

    # ═══════════════════════════════════════════════════════════
    #  搜索 — 双策略路由
    # ═══════════════════════════════════════════════════════════

    def search(self, name: str, university: str = "") -> list[dict]:
        """搜索导师评价 — 自动检测 SPA 空壳并切换到 API 策略"""
        url = f"{self.BASE_URL}/search"
        params = {"keyword": name}
        if university:
            params["school"] = university
        logger.info("[搜索] %s params=%s | auth=%s", url, params, self._auth_mode)

        try:
            resp = self.session.get(url, params=params, timeout=15, allow_redirects=False)
            resp.encoding = "utf-8"
            status, content_len = resp.status_code, len(resp.text)
            logger.info("[搜索] HTTP %d | %d bytes", status, content_len)

            if status != 200:
                logger.warning("[搜索] 非200: %d", status)
                return []

            # ─── 判断是否为 SPA 空壳 ───
            is_spa = content_len < self.SPA_SHELL_THRESHOLD and not self._html_has_data(resp.text)
            if is_spa:
                logger.info("[搜索] SPA空壳 (%d bytes)，切换到 API 策略", content_len)

                # 1) 尝试从 HTML 提取嵌入数据 (SSR/SSG)
                embedded = self._try_extract_embedded(resp.text)
                if embedded:
                    logger.info("[搜索] 嵌入数据命中: %d 条", len(embedded))
                    return embedded

                # 2) 自动探测 API 端点
                api_hints = self._find_api_hints(resp.text)
                logger.info("[搜索] HTML中API候选: %s", api_hints[:6] if api_hints else "无")

                results = self._search_api_auto(name, university, api_hints)
                if results:
                    logger.info("[搜索] API 命中: %d 条", len(results))
                    return results

                logger.warning("[搜索] 所有策略失败。请浏览器打开 gradchoice.org → F12 Network → 搜索'%s' → 查看数据API URL", name)
                return []

            # ─── 传统 HTML 解析 ───
            results = self._parse_html_search(resp.text)
            time.sleep(random.uniform(1.5, 3))
            return results

        except requests.RequestException as e:
            logger.error("[搜索] 请求异常: %s", e)
            return []
        except Exception:
            logger.exception("[搜索] 未捕获异常")
            return []

    # ═══════════════════════════════════════════════════════════
    #  策略: 传统 HTML 解析
    # ═══════════════════════════════════════════════════════════

    def _parse_html_search(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        cards = (
            soup.select(".advisor-card")
            or soup.select(".result-item")
            or soup.select(".list-item")
            or soup.select(".card")
            or soup.select("article")
        )
        if not cards:
            cards = soup.select(".search-result-item, .item, [class*='result'], [class*='card']")

        logger.info("[HTML] %d 候选卡片", len(cards))
        if len(cards) == 0:
            title = soup.title.get_text(strip=True) if soup.title else "N/A"
            logger.warning("[HTML] 无卡片。标题: %s", title)
            body = soup.body.get_text(" ", strip=True)[:400] if soup.body else "(无 body)"
            logger.info("[HTML] 正文: %s", body)
            return []

        results = []
        for card in cards:
            try:
                r = {
                    "name": self._extract_text(card, [".name", ".title", "h3", "h2", "a"]),
                    "university": self._extract_text(card, [".school", ".university", ".uni", "[class*='school']"]),
                    "department": self._extract_text(card, [".dept", ".department", "[class*='dept']"]),
                    "overall_score": self._extract_score(card),
                    "review_count": self._extract_count(card),
                    "source": "gradchoice.org",
                    "detail_url": self._extract_url(card),
                    "reviews": [],
                }
                if r["name"] and len(r["name"]) >= 2:
                    if r["detail_url"]:
                        r["reviews"] = self._fetch_reviews(r["detail_url"], "")
                        r["review_count"] = len(r["reviews"])
                    results.append(r)
                    logger.info("[HTML] ✓ name=%s uni=%s score=%s reviews=%d",
                                r["name"], r["university"], r["overall_score"], r["review_count"])
            except Exception:
                continue

        logger.info("[HTML] 共 %d 条结果", len(results))
        return results

    # ═══════════════════════════════════════════════════════════
    #  策略: API 自动探测
    # ═══════════════════════════════════════════════════════════

    def _find_api_hints(self, html: str) -> list[str]:
        """从 HTML 中查找可能的 API 端点"""
        patterns = [
            r'(/api(?:/v\d+)?/[\w/-]+)',
            r'baseURL\s*[:=]\s*["\']([^"\']+)["\']',
            r'axios\.(?:get|post)\s*\(\s*["\']([^"\']+)["\']',
            r'fetch\(\s*["\']([^"\']+)["\']',
        ]
        urls = set()
        for pat in patterns:
            for m in re.finditer(pat, html, re.IGNORECASE):
                candidate = m.group(1)
                if "/api/" in candidate or candidate.startswith("http"):
                    urls.add(candidate)
        return sorted(urls)

    def _search_api_auto(self, name: str, university: str,
                         api_hints: list[str]) -> list[dict]:
        """自动探测 API 端点"""
        original_accept = self.session.headers.get("Accept")
        self.session.headers["Accept"] = "application/json, text/plain, */*"

        candidates = []

        # 如果有从 HTML 中提取的 base URL，优先尝试
        for hint in api_hints[:3]:
            base = hint if hint.startswith("http") else f"{self.BASE_URL}{hint}"
            candidates.append((f"{base}/search", {"keyword": name, "school": university}))
            candidates.append((base, {"keyword": name, "school": university}))

        # 通用候选（含已验证 GradChoice API）
        candidates += [
            # GradChoice 搜索 API（已验证）
            (f"{self.BASE_URL}/api/supervisors/search", {"q": name, "school": university, "page_size": 20}),
            # GradChoice 评论 API（已验证）
            (f"{self.BASE_URL}/api/comments/supervisor", {}),
            # 其他通用模式
            (f"{self.BASE_URL}/api/search", {"keyword": name, "school": university}),
            (f"{self.BASE_URL}/api/advisors", {"search": name, "school": university}),
            (f"{self.BASE_URL}/api/v1/search", {"q": name, "school": university}),
            (f"{self.BASE_URL}/api/advisors/search", {"name": name, "university": university}),
            (f"{self.BASE_URL}/api/v1/advisors", {"search": name, "school": university}),
        ]

        seen = set()
        for api_url, api_params in candidates:
            key = f"{api_url}|{api_params}"
            if key in seen:
                continue
            seen.add(key)

            try:
                logger.info("[API探测] %s params=%s", api_url, api_params)
                resp = self.session.get(api_url, params=api_params, timeout=15)
                logger.info("[API探测] HTTP %d %d bytes", resp.status_code, len(resp.text))

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        logger.info("[API探测] JSON结构: %s",
                                   list(data.keys()) if isinstance(data, dict) else f"list({len(data)})")
                        parsed = self._parse_api_json(data)
                        if parsed:
                            return parsed
                    except Exception:
                        pass

                elif resp.status_code in (401, 403):
                    logger.info("[API探测] 无此API权限")
                elif resp.status_code == 404:
                    continue
                else:
                    logger.info("[API探测] HTTP %d", resp.status_code)

                time.sleep(0.3)  # 礼貌延迟
            except requests.RequestException as e:
                logger.info("[API探测] 请求失败: %s", e)
                continue
            except Exception as e:
                logger.info("[API探测] 解析失败: %s", e)
                continue

        # 恢复 Accept header
        if original_accept:
            self.session.headers["Accept"] = original_accept
        else:
            self.session.headers.pop("Accept", None)
        return []

    def _parse_api_json(self, data) -> list[dict]:
        """将 JSON 响应转为标准化结果"""
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("data", "results", "items", "advisors", "supervisors", "list", "records", "content"):
                v = data.get(key)
                if isinstance(v, list):
                    items = v
                    break
                elif isinstance(v, dict):
                    items = list(v.values())

        if not isinstance(items, list):
            return []

        results = []
        for item in items:
            if not isinstance(item, dict):
                continue

            advisor_id = str(item.get("id") or "")
            detail_url = (str(item.get("url") or item.get("detail_url") or item.get("link") or "")
                          or (f"/supervisor/{advisor_id}" if advisor_id else ""))

            r = {
                "name": str(item.get("name") or item.get("advisor_name") or item.get("title", "")),
                "university": str(item.get("university") or item.get("school") or item.get("college", "")),
                "department": str(item.get("department") or item.get("dept") or ""),
                "overall_score": self._safe_float(item.get("score") or item.get("rating")
                                                  or item.get("overall_score") or item.get("average_score")),
                "review_count": int(item.get("review_count") or item.get("reviews_count")
                                    or item.get("comment_count") or item.get("count") or 0),
                "source": "gradchoice.org",
                "detail_url": detail_url,
                "reviews": [],
                "_id": advisor_id,  # 内部用
            }
            if r["name"] and len(r["name"]) >= 2:
                # 尝试获取评价详情
                reviews = self._fetch_reviews(r["detail_url"], advisor_id)
                r["reviews"] = reviews
                r["review_count"] = len(reviews) or r["review_count"]
                results.append(r)
                logger.info("[API解析] name=%s uni=%s score=%s reviews=%d",
                           r["name"], r["university"], r["overall_score"], r["review_count"])
        return results

    # ═══════════════════════════════════════════════════════════
    #  策略: 嵌入数据提取 (SSR/SSG)
    # ═══════════════════════════════════════════════════════════

    def _try_extract_embedded(self, html: str) -> list[dict]:
        patterns = [
            r'__NEXT_DATA__\s*=\s*({.+?});\s*</script>',
            r'__NUXT__\s*=\s*({.+?});\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__DATA__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    data = json_mod.loads(m.group(1))
                    items = self._find_list(data)
                    if items:
                        return self._parse_api_json(items)
                except Exception:
                    continue
        return []

    @staticmethod
    def _find_list(obj, depth=0):
        if depth > 8:
            return None
        if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
            return obj
        if isinstance(obj, dict):
            for key in ("data", "results", "items", "advisors", "list", "records"):
                v = obj.get(key)
                if isinstance(v, (list, dict)):
                    found = GradChoiceScraper._find_list(v, depth + 1)
                    if found:
                        return found
        return None

    # ═══════════════════════════════════════════════════════════
    #  辅助: SPA 检测
    # ═══════════════════════════════════════════════════════════

    def _html_has_data(self, html: str) -> bool:
        """判断 HTML 是否包含实质性数据（而非 SPA 空壳）"""
        # 移除所有元数据标签（title/meta/link/script/style）
        cleaned = re.sub(r'<(?:title|meta|link)[^>]*>.*?</(?:title|meta|link)>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<(?:script|style|noscript)[^>]*>.*?</(?:script|style|noscript)>', '', cleaned, flags=re.DOTALL)
        markers = ['advisor-card', 'result-item', 'review-card', '评分', '评价']
        return sum(1 for m in markers if m in cleaned.lower()) > 0

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            return f if 1 <= f <= 10 else None
        except (ValueError, TypeError):
            return None

    # ═══════════════════════════════════════════════════════════
    #  详情页抓取
    # ═══════════════════════════════════════════════════════════

    def _fetch_reviews(self, detail_url: str, advisor_id: str = "",
                       max_reviews: int = 20) -> list[dict]:
        """获取评价 — API 优先，HTML 兜底"""
        # ── 策略 A: API ──
        if advisor_id:
            # GradChoice 评论 API（已验证）
            api_url = f"{self.BASE_URL}/api/comments/supervisor/{advisor_id}?page_size={max_reviews}"
            try:
                logger.info("[评价API] %s", api_url)
                resp = self.session.get(api_url, timeout=10, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        items = (data if isinstance(data, list)
                                 else data.get("items") or data.get("data")
                                 or data.get("comments") or data.get("results") or [])
                        if isinstance(items, list) and items:
                            reviews = []
                            for rv in items[:max_reviews]:
                                if not isinstance(rv, dict):
                                    continue
                                author_info = rv.get("author") or {}
                                author_name = (rv.get("author") if isinstance(rv.get("author"), str)
                                               else author_info.get("display_name", "")) if isinstance(author_info, dict) else "匿名"
                                reviews.append({
                                    "author": str(author_name)[:20] or "匿名",
                                    "rating": self._safe_float(rv.get("rating") or rv.get("score")),
                                    "date": str(rv.get("created_at") or rv.get("date") or rv.get("created", "")),
                                    "content": str(rv.get("content") or rv.get("text") or rv.get("body", "")),
                                    "source": "gradchoice.org",
                                })
                            if reviews:
                                logger.info("[评价API] %d 条评价", len(reviews))
                                return reviews
                    except Exception:
                        pass
            except Exception as e:
                logger.info("[评价API] 失败: %s", e)

        # ── 策略 B: HTML ──
        if not detail_url:
            return []
        full = detail_url if detail_url.startswith("http") else f"{self.BASE_URL}{detail_url}"
        try:
            resp = self.session.get(full, timeout=10)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            items = (
                soup.select(".review-item")
                or soup.select(".comment")
                or soup.select("[class*='review']")
                or soup.select("[class*='comment']")
            )
            reviews = []
            for item in items[:max_reviews]:
                try:
                    rv = {
                        "author": self._extract_text(item, [".author", ".user", ".name"], default="匿名")[:20],
                        "rating": self._extract_rating(item),
                        "date": self._extract_text(item, [".date", ".time", "[class*='date']"]),
                        "content": self._extract_text(item, [".content", ".text", ".body", "p"], default=""),
                        "source": "gradchoice.org",
                    }
                    if rv["content"]:
                        reviews.append(rv)
                except Exception:
                    continue
            return reviews
        except Exception as e:
            logger.info("[详情] 失败: %s", e)
            return []

    # ═══════════════════════════════════════════════════════════
    #  静态提取工具
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _extract_text(element, selectors: list[str], default: str = "") -> str:
        for sel in selectors:
            el = element.select_one(sel)
            if el:
                t = el.get_text(strip=True)
                if t:
                    return t[:200]
        return default

    @staticmethod
    def _extract_url(element) -> str:
        link = element.select_one("a[href]")
        if link and link.get("href"):
            h = link["href"]
            return h if h.startswith("http") else h
        return ""

    @staticmethod
    def _extract_score(element) -> Optional[float]:
        el = element.select_one(".score, .rating, .star-num, [class*='score']")
        if el:
            nums = re.findall(r"[\d.]+", el.get_text(strip=True))
            if nums:
                try:
                    v = float(nums[0])
                    return v if 1 <= v <= 10 else None
                except ValueError:
                    pass
        return None

    @staticmethod
    def _extract_count(element) -> int:
        el = element.select_one(".count, .review-count, .num, [class*='count']")
        if el:
            nums = re.findall(r"\d+", el.get_text(strip=True))
            if nums:
                try:
                    return int(nums[0])
                except ValueError:
                    pass
        return 0

    @staticmethod
    def _extract_rating(element) -> Optional[float]:
        el = element.select_one("[class*='star'], [class*='rating'], .stars")
        if el:
            cls = " ".join(el.get("class", []))
            m = re.search(r"(\d+)", cls)
            if m:
                try:
                    return float(m.group(1)) / 2
                except ValueError:
                    pass
        return None

    @staticmethod
    def _extract_raw_jwt(stored_value: str) -> str:
        if not stored_value:
            return ""
        stored_value = stored_value.strip()
        if stored_value.startswith("eyJ"):
            return stored_value
        m = re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', stored_value)
        return m.group(0) if m else ""
