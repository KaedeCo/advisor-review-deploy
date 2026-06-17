"""
搜索历史 API — 持久化搜索结果的 CRUD 接口
"""

import json
from fastapi import APIRouter, Query
from ..db import get_search_history, get_search_detail, delete_search_record, clear_all_history, get_history_stats

router = APIRouter()


@router.get("/history")
async def list_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """获取搜索历史列表"""
    records = get_search_history(limit=limit, offset=offset)
    stats = get_history_stats()
    # 解析 JSON 字符串字段
    for rec in records:
        if isinstance(rec.get("platforms_used"), str):
            try:
                rec["platforms_used"] = json.loads(rec["platforms_used"])
            except json.JSONDecodeError:
                rec["platforms_used"] = []
    return {
        "records": records,
        "total": stats["total_records"],
        "latest": stats["latest_search"],
    }


@router.get("/history/{record_id}")
async def get_detail(record_id: int):
    """获取单条搜索的完整结果（含评价数据）"""
    record = get_search_detail(record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")
    # 解析 JSON 字段
    record["results"] = json.loads(record.pop("results_json", "[]"))
    if isinstance(record.get("platforms_used"), str):
        try:
            record["platforms_used"] = json.loads(record["platforms_used"])
        except json.JSONDecodeError:
            record["platforms_used"] = []
    return record


@router.delete("/history/{record_id}")
async def delete_detail(record_id: int):
    """删除一条搜索记录"""
    ok = delete_search_record(record_id)
    from fastapi import HTTPException
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"status": "ok", "message": "已删除"}


@router.delete("/history")
async def clear_history():
    """清空所有搜索历史"""
    count = clear_all_history()
    return {"status": "ok", "message": f"已清空 {count} 条记录"}
