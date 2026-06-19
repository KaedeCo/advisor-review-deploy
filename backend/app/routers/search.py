"""
搜索 API — 接收导师信息，调度已启用平台的爬虫 + Tavily 多源搜索引擎，返回聚合结果
"""

import asyncio
import time
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from ..models import SearchRequest, SearchResponse
from ..config import get_enabled_platforms
from ..services.crawlers.gradchoice import GradChoiceScraper
from ..services.search_engine import TavilySearchEngine
from ..services.merger import merge_and_rank
from ..db import save_search_result

logger = logging.getLogger("search")
router = APIRouter()

# 缓存
_crawler_cache: dict = {}
_tavily_engine: Optional[TavilySearchEngine] = None


def _get_gradchoice_scraper(access_token: str = "") -> GradChoiceScraper:
    cache_key = f"gradchoice_{hash(access_token)}"
    if cache_key not in _crawler_cache:
        _crawler_cache[cache_key] = GradChoiceScraper(access_token=access_token)
    return _crawler_cache[cache_key]


def _get_letpub_scraper():
    """懒加载 LetPub（需 playwright，避免启动时强依赖）"""
    if "letpub" not in _crawler_cache:
        try:
            from ..services.crawlers.letpub import LetPubScraper
            _crawler_cache["letpub"] = LetPubScraper()
        except ImportError as e:
            raise ImportError(
                "LetPub 爬虫需要 playwright 模块，请运行: pip install playwright && playwright install chromium"
            ) from e
    return _crawler_cache["letpub"]


def _get_eeban_scraper():
    """懒加载保研论坛爬虫"""
    if "eeban" not in _crawler_cache:
        from ..services.crawlers.eeban import EebanScraper
        _crawler_cache["eeban"] = EebanScraper()
    return _crawler_cache["eeban"]


def _get_muchong_scraper():
    """懒加载小木虫爬虫"""
    if "muchong" not in _crawler_cache:
        from ..services.crawlers.muchong import MuchongScraper
        _crawler_cache["muchong"] = MuchongScraper()
    return _crawler_cache["muchong"]


def _get_daoshipingjia_scraper():
    """懒加载导师评价网爬虫"""
    if "daoshipingjia" not in _crawler_cache:
        from ..services.crawlers.daoshipingjia import DaoshiPingjiaScraper
        _crawler_cache["daoshipingjia"] = DaoshiPingjiaScraper()
    return _crawler_cache["daoshipingjia"]


def _get_pireview_scraper():
    """懒加载 PI Review 爬虫"""
    if "pireview" not in _crawler_cache:
        from ..services.crawlers.pireview import PIReviewScraper
        _crawler_cache["pireview"] = PIReviewScraper()
    return _crawler_cache["pireview"]


def _get_kaoyan_scraper():
    """懒加载考研论坛爬虫"""
    if "kaoyan" not in _crawler_cache:
        from ..services.crawlers.kaoyan import KaoyanScraper
        _crawler_cache["kaoyan"] = KaoyanScraper()
    return _crawler_cache["kaoyan"]


def _format_github_results(db_rows: list[dict]) -> list[dict]:
    """将 GitHub 数据库查询结果转为 AdvisorResult 兼容格式"""
    results = []
    for r in db_rows:
        results.append({
            "name": r.get("name", ""),
            "university": r.get("university", ""),
            "department": r.get("department", ""),
            "overall_score": r.get("avg_rating"),
            "review_count": r.get("review_count", 0),
            "reviews": r.get("reviews", []),
            "source": "github_rms",
            "detail_url": "https://github.com/wangzhiye-tiancai/RateMySupervisor",
        })
    return results


def _get_tavily_engine(api_key: str = "") -> TavilySearchEngine:
    global _tavily_engine
    if _tavily_engine is None or _tavily_engine._api_key != api_key:
        _tavily_engine = TavilySearchEngine(api_key=api_key)
    return _tavily_engine


def _run_crawlers_sync(advisor_name: str, university: str, target_platforms: list[dict],
                       department: str = "", gradchoice_token: str = "") -> tuple[list[dict], list[str]]:
    all_results = []
    platforms_used = []

    for platform in target_platforms:
        try:
            if platform["key"] == "gradchoice":
                scraper = _get_gradchoice_scraper(access_token=gradchoice_token)
                results = scraper.search(advisor_name, university)
                if results:
                    all_results.extend(results)
                    platforms_used.append("gradchoice")

            elif platform["key"] == "letpub":
                # LetPub 使用 async Playwright，在主事件循环中异步执行，
                # 不由 _run_crawlers_sync 处理。见 _run_letpub_async
                pass

            elif platform["key"] == "github_rms":
                from ..services.github_import import search_github
                db_results = search_github(advisor_name, university)
                if db_results:
                    formatted = _format_github_results(db_results)
                    all_results.extend(formatted)
                    platforms_used.append("github_rms")

            elif platform["key"] == "eeban":
                scraper = _get_eeban_scraper()
                results = scraper.search_with_detail(advisor_name, university)
                if results:
                    all_results.extend(results)
                    platforms_used.append("eeban")
                else:
                    # 精确搜索 0 结果 → 降级：全局搜索（去版块限定）
                    # 有校名 → 搜校名，给其他信源提供侧面印证
                    # 无校名 → 搜通用选导关键词
                    if university:
                        logger.info("[eeban] 精确搜索 0 结果，降级→全局搜校名: %s", university)
                        fallback = scraper.search_with_detail(
                            university, university="",
                            fetch_details=True, max_threads=5,
                        )
                    else:
                        logger.info("[eeban] 精确搜索 0 结果，降级→全局搜通用关键词")
                        fallback = scraper.search_with_detail(
                            "选导师", university="",
                            fetch_details=True, max_threads=5,
                        )
                    if fallback:
                        # 标记来源以便区分
                        for r in fallback:
                            r["source"] = "eeban_校名降级"
                        all_results.extend(fallback)
                        platforms_used.append("eeban")
                    else:
                        logger.info("[eeban] 全局校名搜索也为空")

            elif platform["key"] == "muchong":
                scraper = _get_muchong_scraper()
                results = scraper.search_with_detail(advisor_name, university)
                if results:
                    all_results.extend(results)
                    platforms_used.append("muchong")
                else:
                    # 同 eeban 降级策略：搜不到人名 → 搜校名
                    if university:
                        logger.info("[muchong] 精确搜索 0 结果，降级→全局搜校名: %s", university)
                        fallback = scraper.search_with_detail(
                            university, university="",
                            fetch_details=True, max_threads=5,
                        )
                    else:
                        logger.info("[muchong] 精确搜索 0 结果，降级→全局搜通用关键词")
                        fallback = scraper.search_with_detail(
                            "选导师", university="",
                            fetch_details=True, max_threads=5,
                        )
                    if fallback:
                        for r in fallback:
                            r["source"] = "muchong_校名降级"
                        all_results.extend(fallback)
                        platforms_used.append("muchong")
                    else:
                        logger.info("[muchong] 全局搜索也为空")

            elif platform["key"] == "daoshipingjia":
                scraper = _get_daoshipingjia_scraper()
                # daoshipingjia 是树状目录查找，不需要降级
                # department 通过 advisor_name 后的第二个参数在搜索入口传入
                results = scraper.search(
                    advisor_name,
                    university,
                    department or "",
                )
                if results:
                    all_results.extend(results)
                    platforms_used.append("daoshipingjia")

            elif platform["key"] == "pireview":
                scraper = _get_pireview_scraper()
                results = scraper.search(advisor_name, university)
                if results:
                    all_results.extend(results)
                    platforms_used.append("pireview")

            elif platform["key"] == "kaoyan":
                scraper = _get_kaoyan_scraper()
                results = scraper.search_with_detail(advisor_name, university)
                if results:
                    all_results.extend(results)
                    platforms_used.append("kaoyan")
                else:
                    # 精确搜索 0 结果 -> 降级：搜"导师"全局
                    logger.info('[kaoyan] 精确搜索 0 结果，降级->搜索"导师"')
                    fallback = scraper.search_with_detail(
                        "导师", university="",
                        fetch_details=True, max_threads=8,
                    )
                    if fallback:
                        for r in fallback:
                            r["source"] = "kaoyan_校名降级"
                        all_results.extend(fallback)
                        platforms_used.append("kaoyan")

        except Exception as e:
            logger.warning("[%s] 爬取失败: %s", platform["key"], e)
            continue

    return all_results, platforms_used


async def _run_tavily_search(advisor_name: str, university: str, target_platforms: list[dict],
                              tavily_key: str = "") -> tuple[list[dict], bool]:
    """仅在 tavily 平台启用时执行"""
    # 检查平台开关
    tavily_enabled = any(p.get("key") == "tavily" for p in target_platforms)
    if not tavily_enabled and target_platforms:
        return [], False

    try:
        engine = _get_tavily_engine(api_key=tavily_key)
        if not engine.available:
            logger.info("Tavily 不可用，跳过搜索引擎")
            return [], False

        results = await engine.search_async(advisor_name, university)
        if results:
            logger.info("Tavily 搜索完成: %d 条结果", len(results))
            return results, True
        return [], True
    except Exception as e:
        logger.warning("Tavily 搜索异常: %s", e)
        return [], False


async def _run_letpub_async(advisor_name: str, university: str,
                            target_platforms: list[dict]) -> tuple[list[dict], bool]:
    """LetPub 异步爬虫（Playwright async API，主事件循环中运行）"""
    letpub_enabled = any(p.get("key") == "letpub" for p in target_platforms)
    if not letpub_enabled:
        return [], False

    try:
        scraper = _get_letpub_scraper()
        results = await scraper.search(advisor_name, university)
        if results:
            logger.info("LetPub 搜索完成: %d 条基金项目", len(results))
            return results, True
        return [], True
    except Exception as e:
        logger.warning("LetPub 搜索异常: %s", e)
        return [], False


@router.post("/search", response_model=SearchResponse)
async def search_advisor(req: SearchRequest):
    """
    搜索导师评价
    
    - advisor_name: 导师姓名（必填）
    - university: 院校（可选）
    - department: 院系（可选）
    - platforms: 指定平台列表（空=全部已启用平台）
    """
    start_time = time.time()

    # 确定要使用的平台列表
    if req.platforms:
        target_platforms = [p for p in get_enabled_platforms() if p["key"] in req.platforms]
        logger.info("[search] 前端指定平台: %s → 后端匹配: %s",
                     req.platforms, [p["key"] for p in target_platforms])
    else:
        target_platforms = get_enabled_platforms()
        logger.info("[search] 前端未指定平台，使用全部已启用: %s",
                     [p["key"] for p in target_platforms])

    # ── 并行执行：直连爬虫(线程) + Tavily 搜索引擎 + LetPub(async) ──
    gradchoice_token = req.cookies.get("gradchoice", "") if req.cookies else ""
    crawler_task = asyncio.to_thread(
        _run_crawlers_sync, req.advisor_name, req.university or "", target_platforms,
        req.department or "", gradchoice_token,
    )
    tavily_task = _run_tavily_search(req.advisor_name, req.university or "", target_platforms, tavily_key=req.tavily_key)
    letpub_task = _run_letpub_async(req.advisor_name, req.university or "", target_platforms)

    (crawler_results, platforms_used), (tavily_results, tavily_used), (letpub_results, letpub_used) = \
        await asyncio.gather(crawler_task, tavily_task, letpub_task)

    # ── 合并结果 ──
    all_raw = crawler_results + tavily_results + letpub_results

    if tavily_used:
        platforms_used.append("tavily")
    if letpub_used:
        platforms_used.append("letpub")

    # ── 去重 + 融合 + 排名 —— Tavily 匿名结果自动归入同名 GradChoice 条目 ──
    all_results = merge_and_rank(all_raw, advisor_name=req.advisor_name)

    elapsed = round(time.time() - start_time, 2)

    # ── 计算实际评价总数（融合后每个 entry 的 review_count 之和）─
    real_total = sum(
        (r.review_count if hasattr(r, 'review_count') else r.get('review_count', 0))
        for r in all_results
    )

    # ── 持久化搜索结果到 SQLite ──
    try:
        save_search_result(
            query=f"{req.advisor_name} {req.university} {req.department}".strip(),
            advisor_name=req.advisor_name,
            university=req.university or "",
            department=req.department or "",
            results=[r if isinstance(r, dict) else r.model_dump() for r in all_results],
            total_count=real_total,
            platforms_used=platforms_used,
            elapsed_seconds=elapsed,
        )
    except Exception as e:
        logger.warning("[History] 保存搜索历史失败（不影响结果返回）: %s", e)

    return SearchResponse(
        query=f"{req.advisor_name} {req.university} {req.department}".strip(),
        results=all_results,
        total_count=len(all_results),
        platforms_used=platforms_used,
        elapsed_seconds=elapsed,
    )


@router.get("/platforms")
async def list_platforms():
    """获取所有可用平台及其状态"""
    from ..config import load_config
    config = load_config()
    return config.get("platforms", {})
