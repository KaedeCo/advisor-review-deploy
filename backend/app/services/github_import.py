"""
GitHub 开源数据集导入 — RateMySupervisor 导师评价数据
Source: https://github.com/wangzhiye-tiancai/RateMySupervisor

数据格式 (comments_data.json):
[
  {
    "school_cate": "985",
    "university": "清华大学",
    "department": "计算机系",
    "supervisor": "张三",
    "rate": 4.5,
    "description": "导师很负责..."
  }
]

流程：
1. git clone / 下载 comments_data.json
2. 清洗：去空行、去重复、name 标准化
3. 导入 SQLite（导师表 + 评价表）
4. 构建 FTS5 全文搜索索引
"""

import json
import os
import re
import sqlite3
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("github_import")

# ── 路径配置 ──────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "history.db"
GITHUB_CACHE_DIR = DATA_DIR / "github_cache"
REPO_URL = "https://github.com/wangzhiye-tiancai/RateMySupervisor.git"
REPO_DIR = GITHUB_CACHE_DIR / "RateMySupervisor"
DATA_FILE = REPO_DIR / "data" / "comments_data.json"

# 克隆源优先级：① Gitee 国内最快 ② GitHub 直连 ③ 镜像代理
CLONE_URLS = [
    ("Gitee 码云",      "https://gitee.com/AprilSloan/RateMySupervisor"),
    ("GitHub 直连",     "https://github.com/wangzhiye-tiancai/RateMySupervisor.git"),
    ("ghproxy 镜像",    "https://mirror.ghproxy.com/https://github.com/wangzhiye-tiancai/RateMySupervisor.git"),
    ("ghproxy.net",     "https://ghproxy.net/https://github.com/wangzhiye-tiancai/RateMySupervisor.git"),
]

GIT_ENV = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",       # 禁止弹出密码框
    "GIT_HTTP_LOW_SPEED_LIMIT": "100", # 低于 100 bytes/s 视为超时
    "GIT_HTTP_LOW_SPEED_TIME": "15",  # 持续 15 秒低速则断开
}
GIT_CLONE_TIMEOUT = 45  # 单个源超时（秒）
GIT_PULL_TIMEOUT = 20   # pull 超时（秒）


def ensure_repo() -> bool:
    """确保本地有数据仓库（克隆或更新）"""
    GITHUB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 已有仓库 → 尝试拉取更新（可选，失败不阻断）
    if REPO_DIR.exists() and _data_file_valid():
        logger.info("仓库已存在且数据文件有效，跳过克隆")
        try:
            subprocess.run(
                ["git", "-C", str(REPO_DIR), "pull", "--ff-only"],
                capture_output=True, timeout=GIT_PULL_TIMEOUT, env=GIT_ENV,
            )
        except Exception:
            logger.warning("git pull 失败，使用已有数据")
        return True

    if REPO_DIR.exists():
        # 目录在但数据文件无效，清掉重来
        import shutil
        shutil.rmtree(str(REPO_DIR), ignore_errors=True)

    # ── 依次尝试克隆源 ──
    for label, url in CLONE_URLS:
        logger.info("尝试 %s: %s", label, url)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(REPO_DIR)],
                check=True, capture_output=True, timeout=GIT_CLONE_TIMEOUT, env=GIT_ENV,
            )
            # 非 GitHub 源 → remote 改回官方地址
            if "github.com" not in url:
                subprocess.run(
                    ["git", "-C", str(REPO_DIR), "remote", "set-url", "origin", REPO_URL],
                    capture_output=True, timeout=10, env=GIT_ENV,
                )
            logger.info("✅ 克隆成功 (via %s)", label)
            return True
        except subprocess.TimeoutExpired:
            logger.warning("克隆超时 (%s, %ds)", label, GIT_CLONE_TIMEOUT)
            _cleanup_repo_dir()
        except Exception as e:
            logger.warning("克隆失败 (%s): %s", label, str(e)[:120])
            _cleanup_repo_dir()

    logger.error("所有克隆源均失败，请手动下载: %s", REPO_URL)
    return False


def _cleanup_repo_dir():
    """清理失败的克隆目录"""
    if REPO_DIR.exists():
        import shutil
        shutil.rmtree(str(REPO_DIR), ignore_errors=True)


def _data_file_valid() -> bool:
    """检查关键数据文件是否存在"""
    return DATA_FILE.exists()


def load_raw_data() -> list[dict]:
    """加载原始 JSON 数据"""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"数据文件不存在: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_data(raw: list[dict]) -> list[dict]:
    """数据清洗：去空、标准化、去重"""
    seen = set()
    cleaned = []
    stats = {"total": len(raw), "empty": 0, "duplicate": 0, "kept": 0}

    for item in raw:
        # 跳过空字段
        supervisor = (item.get("supervisor") or "").strip()
        university = (item.get("university") or "").strip()
        description = (item.get("description") or "").strip()

        if not supervisor or not description:
            stats["empty"] += 1
            continue

        # 标准化
        supervisor = normalize_name(supervisor)
        university = normalize_name(university)
        department = (item.get("department") or "").strip()

        # 评分处理（1-5 转 1-10）
        rate = item.get("rate")
        if isinstance(rate, (int, float)) and rate > 0:
            rating = float(rate) * 2  # 5分制 → 10分制
        else:
            rating = None

        # 去重 key（导师+院校+描述前50字）
        desc_key = description[:50].strip()
        dedup_key = f"{supervisor}|{university}|{desc_key}"
        if dedup_key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(dedup_key)

        cleaned.append({
            "name": supervisor,
            "university": university,
            "department": department,
            "school_cate": (item.get("school_cate") or "").strip(),
            "rating": rating,
            "content": description,
            "source": "github_rms",
            "source_url": "https://github.com/wangzhiye-tiancai/RateMySupervisor",
        })
        stats["kept"] += 1

    logger.info("清洗统计: 总数=%d 空=%d 重复=%d 保留=%d",
                stats["total"], stats["empty"], stats["duplicate"], stats["kept"])
    return cleaned


def normalize_name(name: str) -> str:
    """名称标准化：去多余空格、统一括号"""
    name = re.sub(r"\s+", "", name)
    name = name.replace("（", "(").replace("）", ")")
    return name


# ── 数据库操作 ────────────────────────────────────────────────


def import_to_db(data: list[dict]) -> dict:
    """将清洗后的数据导入 SQLite"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    conn.row_factory = sqlite3.Row

    try:
        _ensure_tables(conn)
        advisors_added, reviews_added = _insert_data(conn, data)
        _build_fts(conn)
        conn.commit()
    finally:
        conn.close()

    return {"advisors": advisors_added, "reviews": reviews_added}


def _ensure_tables(conn: sqlite3.Connection):
    """创建导师表和评价表（如不存在）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS github_advisors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            university  TEXT    DEFAULT '',
            department  TEXT    DEFAULT '',
            school_cate TEXT    DEFAULT '',
            review_count INTEGER DEFAULT 0,
            avg_rating  REAL    DEFAULT 0.0,
            UNIQUE(name, university)
        );

        CREATE TABLE IF NOT EXISTS github_reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id  INTEGER NOT NULL REFERENCES github_advisors(id),
            source      TEXT    DEFAULT 'github_rms',
            source_url  TEXT    DEFAULT '',
            rating      REAL,
            content     TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_github_advisor_name
            ON github_advisors(name);
        CREATE INDEX IF NOT EXISTS idx_github_review_advisor
            ON github_reviews(advisor_id);
    """)
    conn.commit()


def _insert_data(conn: sqlite3.Connection, data: list[dict]) -> tuple[int, int]:
    """批量插入导师和评价数据"""
    logger.info("开始导入 %d 条评价...", len(data))

    # 先按导师聚合
    advisor_map: dict[str, dict] = {}
    for item in data:
        key = f"{item['name']}|||{item['university']}"
        if key not in advisor_map:
            advisor_map[key] = {
                "name": item["name"],
                "university": item["university"],
                "department": item.get("department", ""),
                "school_cate": item.get("school_cate", ""),
                "reviews": [],
            }
        advisor_map[key]["reviews"].append(item)

    advisors_added = 0
    reviews_added = 0

    for key, adv in advisor_map.items():
        # insert or ignore advisor
        conn.execute("""
            INSERT OR IGNORE INTO github_advisors (name, university, department, school_cate)
            VALUES (?, ?, ?, ?)
        """, (adv["name"], adv["university"], adv["department"], adv["school_cate"]))

        # get advisor id
        row = conn.execute(
            "SELECT id FROM github_advisors WHERE name=? AND university=?",
            (adv["name"], adv["university"])
        ).fetchone()
        if not row:
            continue
        advisor_id = row["id"]

        # insert reviews
        ratings = []
        for r in adv["reviews"]:
            conn.execute("""
                INSERT OR IGNORE INTO github_reviews (advisor_id, source, source_url, rating, content)
                VALUES (?, ?, ?, ?, ?)
            """, (advisor_id, r.get("source", "github_rms"),
                  r.get("source_url", ""), r.get("rating"), r["content"]))
            reviews_added += 1
            if r.get("rating"):
                ratings.append(r["rating"])

        # update stats
        avg = sum(ratings) / len(ratings) if ratings else 0
        conn.execute("""
            UPDATE github_advisors
            SET review_count = ?, avg_rating = ?
            WHERE id = ?
        """, (len(adv["reviews"]), round(avg, 2), advisor_id))
        advisors_added += 1

    conn.commit()
    logger.info("导入完成: %d 位导师, %d 条评价", advisors_added, reviews_added)
    return advisors_added, reviews_added


def _build_fts(conn: sqlite3.Connection):
    """构建 FTS5 全文搜索索引"""
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS github_fts
        USING fts5(name, university, department, content=github_advisors, content_rowid=id);
    """)
    # 重建索引
    conn.execute("INSERT INTO github_fts(github_fts) VALUES('rebuild')")
    conn.commit()
    logger.info("FTS 全文索引已构建")


# ── 搜索接口 ──────────────────────────────────────────────────

def search_github(advisor_name: str, university: str = "", limit: int = 20) -> list[dict]:
    """在 GitHub 数据集中搜索导师"""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row

    try:
        # 先尝试精确匹配
        query = "SELECT * FROM github_advisors WHERE name=? AND university=?"
        params = (advisor_name, university)
        rows = conn.execute(query + " LIMIT ?", params + (limit,)).fetchall()

        if not rows:
            # 模糊搜索
            rows = conn.execute(
                "SELECT * FROM github_advisors WHERE name LIKE ? ORDER BY review_count DESC LIMIT ?",
                (f"%{advisor_name}%", limit),
            ).fetchall()

        if not rows and advisor_name:
            # FTS 全文搜索
            try:
                rows = conn.execute(
                    "SELECT a.* FROM github_fts f JOIN github_advisors a ON f.rowid=a.id "
                    "WHERE github_fts MATCH ? LIMIT ?",
                    (advisor_name, limit),
                ).fetchall()
            except Exception:
                rows = []

        results = []
        for row in rows:
            r = dict(row)
            # 加载评价
            reviews = conn.execute(
                "SELECT * FROM github_reviews WHERE advisor_id=? LIMIT 50",
                (r["id"],)
            ).fetchall()

            r["reviews"] = [
                {
                    "author": "匿名",
                    "rating": rev["rating"],
                    "date": rev["created_at"],
                    "content": rev["content"],
                    "source": "GitHub(daohipingjia镜像)",
                    "source_url": rev["source_url"],
                }
                for rev in reviews
            ]
            r["review_count"] = len(r["reviews"])
            r["source"] = "github_rms"
            results.append(r)

        return results
    finally:
        conn.close()


# ── 主入口 ────────────────────────────────────────────────────

def run_import() -> dict:
    """一键执行：下载 → 清洗 → 导入 → 索引"""
    logger.info("========== GitHub 数据集导入开始 ==========")

    if not ensure_repo():
        return {"error": "无法获取数据仓库，请检查网络或手动克隆"}

    raw = load_raw_data()
    logger.info("原始数据: %d 条", len(raw))

    cleaned = clean_data(raw)
    stats = import_to_db(cleaned)

    logger.info("========== 导入完成 ==========")
    return {
        **stats,
        "raw_count": len(raw),
        "cleaned_count": len(cleaned),
        "message": f"成功导入 {stats['advisors']} 位导师, {stats['reviews']} 条评价",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="\033[36m[github_import]\033[0m %(message)s")
    result = run_import()
    print(json.dumps(result, ensure_ascii=False, indent=2))
