"""
SQLite 数据库模块 — 搜索历史持久化存储

使用 Python 内置 sqlite3，无需额外依赖。
数据文件存放在 data/ 目录下，与 config.json 同级。
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "history.db"


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接，自动建表"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")     # 每次 commit 直接写主文件，不依赖 WAL
    conn.execute("PRAGMA synchronous=FULL")         # 每次 commit 强制 fsync 落盘
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    """创建表（如果不存在）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query       TEXT    NOT NULL DEFAULT '',
            advisor_name   TEXT    DEFAULT '',
            university     TEXT    DEFAULT '',
            department     TEXT    DEFAULT '',
            results_json   TEXT    NOT NULL,
            total_count    INTEGER NOT NULL DEFAULT 0,
            platforms_used TEXT    DEFAULT '[]',
            elapsed_seconds REAL   DEFAULT 0.0,
            created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_history_created ON search_history(created_at DESC);

        CREATE TABLE IF NOT EXISTS analysis_results (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_name  TEXT    NOT NULL DEFAULT '',
            university    TEXT    DEFAULT '',
            department    TEXT    DEFAULT '',
            review_count  INTEGER NOT NULL DEFAULT 0,
            sentiment_json TEXT,            -- SnowNLP 结果 (JSON)
            deepseek_json  TEXT,            -- DeepSeek 综合分析 (JSON)
            deepseek_sentiment_json TEXT,   -- DeepSeek 逐条情感分类 (JSON)
            dimension_scores_json TEXT,     -- 六维评分（JSON）
            advisor_profile_json TEXT,      -- 导师画像 (JSON)
            reviews_text   TEXT,            -- 原始评论文本
            created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_created ON analysis_results(created_at DESC);
    """)
    # 自动迁移：补上可能缺失的 dimension_scores_json 列
    try:
        conn.execute("SELECT dimension_scores_json FROM analysis_results LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE analysis_results ADD COLUMN dimension_scores_json TEXT")
    # 自动迁移：补上可能缺失的 deepseek_sentiment_json 列
    try:
        conn.execute("SELECT deepseek_sentiment_json FROM analysis_results LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE analysis_results ADD COLUMN deepseek_sentiment_json TEXT")
    # 自动迁移：补上可能缺失的 advisor_profile_json 列
    try:
        conn.execute("SELECT advisor_profile_json FROM analysis_results LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE analysis_results ADD COLUMN advisor_profile_json TEXT")
    conn.commit()


# ─── CRUD 操作 ──────────────────────────────────────────────

def save_search_result(
    *,
    query: str,
    advisor_name: str = "",
    university: str = "",
    department: str = "",
    results: list[dict],
    total_count: int = 0,
    platforms_used: list[str] | None = None,
    elapsed_seconds: float = 0.0,
) -> int:
    """
    保存一条搜索记录。
    返回新记录的 ID。
    """
    conn = _get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO search_history (query, advisor_name, university, department,
                                        results_json, total_count, platforms_used, elapsed_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query,
            advisor_name,
            university,
            department,
            json.dumps(results, ensure_ascii=False),
            total_count,
            json.dumps(platforms_used or [], ensure_ascii=False),
            elapsed_seconds,
        ))
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_search_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """获取搜索历史列表（不含完整的 results_json 以节省带宽）"""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT id, query, advisor_name, university, department,
                   total_count, platforms_used, elapsed_seconds, created_at
            FROM search_history
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_search_detail(record_id: int) -> Optional[dict]:
    """获取单条搜索的完整数据（含 results_json）"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM search_history WHERE id = ?", (record_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_search_record(record_id: int) -> bool:
    """删除一条搜索记录"""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM search_history WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_all_history() -> int:
    """清空所有搜索历史，返回删除数量"""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM search_history")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_history_stats() -> dict:
    """获取统计摘要"""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
        latest = conn.execute("SELECT created_at FROM search_history ORDER BY created_at DESC LIMIT 1").fetchone()
        return {
            "total_records": total,
            "latest_search": latest[0] if latest else None,
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  分析结果 CRUD
# ═══════════════════════════════════════════════════════════════

def save_analysis_result(
    *,
    advisor_name: str = "",
    university: str = "",
    department: str = "",
    review_count: int = 0,
    sentiment: dict | None = None,
    deepseek: dict | None = None,
    deepseek_sentiment: dict | None = None,
    dimension_scores: dict | None = None,
    advisor_profile: dict | None = None,
    reviews_text: str = "",
) -> int:
    """保存/更新分析结果。同一个 advisor 只保留最新一份"""
    conn = _get_conn()
    try:
        # 查找是否已有记录（按 advisor_name 去重）
        existing = conn.execute(
            "SELECT id FROM analysis_results WHERE advisor_name = ?", (advisor_name,)
        ).fetchone()

        if existing:
            # 更新已有记录
            conn.execute("""
                UPDATE analysis_results
                SET sentiment_json = COALESCE(?, sentiment_json),
                    deepseek_json  = COALESCE(?, deepseek_json),
                    deepseek_sentiment_json = COALESCE(?, deepseek_sentiment_json),
                    advisor_profile_json = COALESCE(?, advisor_profile_json),
                    dimension_scores_json = COALESCE(?, dimension_scores_json),
                    reviews_text   = COALESCE(?, reviews_text),
                    university     = COALESCE(NULLIF(?, ''), university),
                    department     = COALESCE(NULLIF(?, ''), department),
                    review_count   = CASE WHEN ? > 0 THEN ? ELSE review_count END,
                    updated_at     = datetime('now', 'localtime')
                WHERE id = ?
            """, (
                json.dumps(sentiment, ensure_ascii=False) if sentiment else None,
                json.dumps(deepseek, ensure_ascii=False) if deepseek else None,
                json.dumps(deepseek_sentiment, ensure_ascii=False) if deepseek_sentiment else None,
                json.dumps(advisor_profile, ensure_ascii=False) if advisor_profile else None,
                json.dumps(dimension_scores, ensure_ascii=False) if dimension_scores else None,
                reviews_text or None,
                university, department,
                review_count, review_count,
                existing["id"],
            ))
            conn.commit()
            return existing["id"]
        else:
            # 创建新记录
            cursor = conn.execute("""
                INSERT INTO analysis_results (advisor_name, university, department,
                    review_count, sentiment_json, deepseek_json, deepseek_sentiment_json,
                    advisor_profile_json, dimension_scores_json, reviews_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                advisor_name, university, department, review_count,
                json.dumps(sentiment, ensure_ascii=False) if sentiment else None,
                json.dumps(deepseek, ensure_ascii=False) if deepseek else None,
                json.dumps(deepseek_sentiment, ensure_ascii=False) if deepseek_sentiment else None,
                json.dumps(advisor_profile, ensure_ascii=False) if advisor_profile else None,
                json.dumps(dimension_scores, ensure_ascii=False) if dimension_scores else None,
                reviews_text,
            ))
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_analysis_list(limit: int = 50, offset: int = 0) -> list[dict]:
    """获取分析结果列表（不含原始文本）"""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT id, advisor_name, university, department, review_count, created_at, updated_at
            FROM analysis_results
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_analysis_detail(record_id: int) -> dict | None:
    """获取单条分析完整数据"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM analysis_results WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        r = dict(row)
        # 解析 JSON 字段
        for field in ("sentiment_json", "deepseek_json", "deepseek_sentiment_json", "advisor_profile_json", "dimension_scores_json"):
            if isinstance(r.get(field), str):
                try:
                    r[field.replace("_json", "")] = json.loads(r[field])
                except json.JSONDecodeError:
                    r[field.replace("_json", "")] = None
                del r[field]
        return r
    finally:
        conn.close()


def delete_analysis(record_id: int) -> bool:
    """删除一条分析记录"""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM analysis_results WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_kpi_stats() -> dict:
    """获取 KPI 统计数据"""
    conn = _get_conn()
    try:
        # 搜索历史统计
        search_stats = conn.execute("""
            SELECT COUNT(*) as total_searches,
                   AVG(elapsed_seconds) as avg_latency,
                   SUM(total_count) as total_results_returned,
                   MAX(created_at) as latest_search
            FROM search_history
        """).fetchone()

        # 分析结果统计
        analysis_stats = conn.execute("""
            SELECT COUNT(*) as total_analyses,
                   COUNT(CASE WHEN sentiment_json IS NOT NULL THEN 1 END) as snownlp_count,
                   COUNT(CASE WHEN deepseek_json IS NOT NULL THEN 1 END) as deepseek_count,
                   COUNT(CASE WHEN deepseek_sentiment_json IS NOT NULL THEN 1 END) as ds_sentiment_count,
                   COUNT(CASE WHEN dimension_scores_json IS NOT NULL THEN 1 END) as dim_score_count,
                   MAX(updated_at) as latest_analysis
            FROM analysis_results
        """).fetchone()

        # 平台使用统计
        platform_stats = conn.execute("""
            SELECT platforms_used, COUNT(*) as count
            FROM search_history
            GROUP BY platforms_used
        """).fetchall()

        # 解析平台使用频率
        platform_freq: dict[str, int] = {}
        for row in platform_stats:
            try:
                platforms = json.loads(row["platforms_used"]) if row["platforms_used"] else []
                for p in platforms:
                    platform_freq[p] = platform_freq.get(p, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        # 评价总数（从分析结果中统计）
        review_stats = conn.execute("""
            SELECT SUM(review_count) as total_reviews_analyzed
            FROM analysis_results
        """).fetchone()

        # 唯一导师数
        unique_advisors = conn.execute("""
            SELECT COUNT(DISTINCT advisor_name) as count
            FROM analysis_results
        """).fetchone()

        return {
            "total_searches": search_stats["total_searches"] or 0,
            "avg_search_latency": round(search_stats["avg_latency"] or 0, 2),
            "total_results_returned": search_stats["total_results_returned"] or 0,
            "latest_search": search_stats["latest_search"],
            "total_analyses": analysis_stats["total_analyses"] or 0,
            "snownlp_calls": analysis_stats["snownlp_count"] or 0,
            "deepseek_calls": (analysis_stats["deepseek_count"] or 0) +
                              (analysis_stats["ds_sentiment_count"] or 0) +
                              (analysis_stats["dim_score_count"] or 0) * 6,
            "dim_score_calls": analysis_stats["dim_score_count"] or 0,
            "latest_analysis": analysis_stats["latest_analysis"],
            "total_reviews_analyzed": review_stats["total_reviews_analyzed"] or 0,
            "unique_advisors": unique_advisors["count"] or 0,
            "platform_frequency": platform_freq,
        }
    finally:
        conn.close()
