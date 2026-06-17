"""
Tavily 多源搜索引擎 — 基于 Tavily Search API 的多站点并发搜索、结果融合排序
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger("search_engine")

# ── 延迟导入 ────────────────────────────────────────────────

_TAVILY_AVAILABLE = False
_TavilyClient = None
try:
    from tavily import TavilyClient as _TC
    _TavilyClient = _TC
    _TAVILY_AVAILABLE = True
except ImportError:
    pass

# ── 模块级全局缓存 ──────────────────────────────────────────

_CONNECTIVITY_OK: Optional[bool] = None
_CONNECTIVITY_DETAIL: str = "Not checked"


# ── 站点配置 ──────────────────────────────────────────────────

# Tier 1: 专业评价平台（include_domains 精确搜索）
TIER1_DOMAINS = [
    "gradchoice.org",
    "daoshipingjia.net",
    "daoshikoubei.net",
    "pi-review.com",
    "ratemysupervisor.net",
]

# Tier 2: 社交/UGC 平台
TIER2_DOMAINS = [
    "tieba.baidu.com",
    "zhihu.com",
    "1point3acres.com",
    "douban.com",
]

TIER2_KEYWORDS = [
    "导师 评价", "导师 避坑", "导师 体验",
]

# Tier 3: 学术辅助源
TIER3_DOMAINS = [
    "letpub.com.cn",
    "semanticscholar.org",
]


# ── 搜索引擎核心类 ────────────────────────────────────────────

class TavilySearchEngine:
    """基于 Tavily Search API 的多源搜索引擎"""

    def __init__(self, api_key: str = "", max_results: int = 10):
        self._api_key = api_key
        self.max_results = max_results
        self._client = None
        self._executor = ThreadPoolExecutor(max_workers=8)

    @property
    def available(self) -> bool:
        global _CONNECTIVITY_OK, _CONNECTIVITY_DETAIL
        if not _TAVILY_AVAILABLE:
            _CONNECTIVITY_DETAIL = "Package not installed"
            return False
        key = self._api_key
        if not key:
            from ..config import get_tavily_api_key
            key = get_tavily_api_key()
        if not key:
            _CONNECTIVITY_DETAIL = "API key not configured"
            return False
        if _CONNECTIVITY_OK is None:
            _CONNECTIVITY_OK, _CONNECTIVITY_DETAIL = self._probe()
        return _CONNECTIVITY_OK

    def _get_client(self):
        if self._client is None:
            key = self._api_key
            if not key:
                from ..config import get_tavily_api_key
                key = get_tavily_api_key()
            self._client = _TavilyClient(api_key=key)
        return self._client

    @staticmethod
    def reset_connectivity():
        global _CONNECTIVITY_OK, _CONNECTIVITY_DETAIL
        _CONNECTIVITY_OK = None
        _CONNECTIVITY_DETAIL = "Not checked"

    @staticmethod
    def get_connectivity_status() -> tuple[Optional[bool], str]:
        return _CONNECTIVITY_OK, _CONNECTIVITY_DETAIL

    def _probe(self) -> tuple[bool, str]:
        """Tavily API 连通性检测 — 不加域名限制，确保有结果返回"""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

        result = [False, ""]

        def _do():
            try:
                client = self._get_client()
                resp = client.search(
                    "Hello world",
                    max_results=1,
                    search_depth="basic",
                )
                if resp and resp.get("results"):
                    result[0] = True
                    result[1] = f"Connected ({resp.get('response_time', '?')}s)"
                else:
                    result[0] = False
                    result[1] = "No results (check API key or quota)"
            except Exception as ex:
                result[0] = False
                msg = str(ex)
                result[1] = msg[:150] if len(msg) > 150 else msg

        with ThreadPoolExecutor(max_workers=1) as ex:
            try:
                ex.submit(_do).result(timeout=10)
            except FutureTimeout:
                result[0] = False
                result[1] = "Timeout (>10s)"
            except Exception:
                pass

        logger.info("Tavily 连通性: %s", result[1])
        return result[0], result[1]

    # ── 单域搜索 ──────────────────────────────────────────

    def _search_domain(
        self, query: str, domains: list[str], site_name: str, weight: float,
        advisor_name: str = "", university: str = "",
        max_results: Optional[int] = None,
    ) -> list[dict]:
        limit = max_results or self.max_results
        try:
            client = self._get_client()
            resp = client.search(
                query,
                max_results=min(limit, 5),
                include_domains=domains,
                search_depth="advanced",
            )
        except Exception:
            return []

        results = []
        for r in resp.get("results", [])[:limit]:
            results.append({
                "name": advisor_name,
                "university": university,
                "department": "",
                "overall_score": None,
                "review_count": 1,
                "reviews": [{
                    "author": "",
                    "rating": None,
                    "date": "",
                    "content": (r.get("content") or "")[:300],
                    "source": site_name,
                    "source_url": r.get("url", ""),
                }],
                "source": site_name,
                "detail_url": r.get("url", ""),
            })
        return results

    def _search_tier2_keyword(
        self, advisor_name: str, university: str,
        domains: list[str], site_name: str, keyword: str,
    ) -> list[dict]:
        parts = [advisor_name, keyword]
        if university:
            parts.insert(1, university)
        query = " ".join(parts)

        try:
            client = self._get_client()
            resp = client.search(
                query,
                max_results=3,
                include_domains=domains,
                search_depth="advanced",
            )
        except Exception:
            return []

        results = []
        for r in resp.get("results", [])[:3]:
            results.append({
                "name": advisor_name,
                "university": university,
                "department": "",
                "overall_score": None,
                "review_count": 1,
                "reviews": [{
                    "author": "",
                    "rating": None,
                    "date": "",
                    "content": (r.get("content") or "")[:300],
                    "source": site_name,
                    "source_url": r.get("url", ""),
                }],
                "source": site_name,
                "detail_url": r.get("url", ""),
            })
        return results

    # ── 主入口 ──────────────────────────────────────────────

    def search(
        self,
        advisor_name: str,
        university: str = "",
    ) -> list[dict]:
        """多源并发搜索（同步接口）"""
        if not self.available:
            return []

        tasks = []

        # Tier 1
        for domain in TIER1_DOMAINS:
            query = f"{advisor_name} 导师"
            if university:
                query = f"{advisor_name} {university} 导师"
            tasks.append(("tier1", query, [domain], domain, domain.replace(".org", "").replace(".net", "")))

        # Tier 2
        for domain in TIER2_DOMAINS:
            for kw in TIER2_KEYWORDS:
                tasks.append(("tier2_kw", advisor_name, university, [domain], domain.split(".")[1] if "." in domain else domain, kw))

        # Tier 3
        for domain in TIER3_DOMAINS:
            query = f"{advisor_name}"
            if university:
                query = f"{advisor_name} {university}"
            tasks.append(("tier1", query, [domain], domain, domain.replace(".com.cn", "").replace(".org", "")))

        if not tasks:
            return []

        futures = []
        for t in tasks:
            if t[0] == "tier1":
                futures.append(self._executor.submit(
                    self._search_domain, t[1], t[2], t[3], 1.0, advisor_name, university))
            else:
                futures.append(self._executor.submit(
                    self._search_tier2_keyword, t[1], t[2], t[3], t[4], t[5]))

        all_results = []
        for f in futures:
            try:
                all_results.extend(f.result(timeout=15))
            except Exception:
                pass

        return all_results[:50]

    async def search_async(
        self, advisor_name: str, university: str = "",
    ) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self.search, advisor_name, university)
