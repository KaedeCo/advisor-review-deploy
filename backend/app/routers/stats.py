"""
统计 API — KPI 仪表板数据
"""

from fastapi import APIRouter
from ..db import get_kpi_stats, get_history_stats
from ..config import load_config, get_enabled_platforms

router = APIRouter()


@router.get("/stats")
async def get_stats():
    """获取 KPI 统计数据"""
    db_stats = get_kpi_stats()
    history_stats = get_history_stats()
    config = load_config()

    # 平台配置统计
    all_platforms = config.get("platforms", {})
    enabled_platforms = get_enabled_platforms()

    # GitHub 离线数据集统计
    github_advisors = 0
    github_reviews = 0
    try:
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent.parent.parent / "data" / "history.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT COUNT(DISTINCT name) as advisors, COUNT(*) as reviews FROM github_reviews").fetchone()
            if row:
                github_advisors = row["advisors"] or 0
                github_reviews = row["reviews"] or 0
            conn.close()
    except Exception:
        pass

    return {
        # 数据覆盖
        "github_advisors": github_advisors,
        "github_reviews": github_reviews,
        "unique_advisors_analyzed": db_stats["unique_advisors"],
        "total_reviews_analyzed": db_stats["total_reviews_analyzed"],

        # 搜索性能
        "total_searches": db_stats["total_searches"],
        "avg_search_latency": db_stats["avg_search_latency"],
        "total_results_returned": db_stats["total_results_returned"],
        "latest_search": db_stats["latest_search"],

        # AI 分析
        "total_analyses": db_stats["total_analyses"],
        "snownlp_calls": db_stats["snownlp_calls"],
        "deepseek_calls": db_stats["deepseek_calls"],
        "dim_score_calls": db_stats["dim_score_calls"],
        "latest_analysis": db_stats["latest_analysis"],

        # 平台
        "total_platforms": len(all_platforms),
        "enabled_platforms": len(enabled_platforms),
        "platform_frequency": db_stats["platform_frequency"],
        "enabled_platform_list": [{"key": p["key"], "name": p["name"], "tier": p["tier"]} for p in enabled_platforms],

        # DeepSeek/Tavily 配置状态
        "deepseek_configured": bool(config.get("deepseek", {}).get("api_key", "")),
        "tavily_configured": bool(config.get("tavily", {}).get("api_key", "")),
    }
