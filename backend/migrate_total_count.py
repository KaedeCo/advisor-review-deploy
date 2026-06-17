"""
一次性迁移：将 search_history 中 total_count 从旧的 len(results) 修正为实际评论总数
"""
import json, sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT id, results_json, total_count FROM search_history").fetchall()
updated = 0

for row in rows:
    try:
        results = json.loads(row["results_json"])
    except (json.JSONDecodeError, TypeError):
        continue

    real_total = sum(
        r.get("review_count", len(r.get("reviews", [])))
        for r in results
    )

    if real_total != row["total_count"]:
        conn.execute(
            "UPDATE search_history SET total_count = ? WHERE id = ?",
            (real_total, row["id"]),
        )
        updated += 1
        print(f"  id={row['id']}: {row['total_count']} → {real_total}")

conn.commit()
conn.close()
print(f"\n更新完成: {updated} 条记录")
