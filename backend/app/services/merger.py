"""
结果融合去重模块 — 多源搜索结果的 URL 去重、同名校验、来源加权排序
"""

import re
from typing import Optional


def deduplicate_by_url(results: list[dict]) -> list[dict]:
    """
    按 source_url 去重，保留首次出现的结果

    Args:
        results: 搜索结果列表，每条需包含 source_url 字段

    Returns:
        去重后的结果列表
    """
    seen: set[str] = set()
    unique: list[dict] = []

    for item in results:
        url = item.get("source_url", "") or item.get("detail_url", "")
        # 标准化 URL：去除尾部斜杠、空白
        url = url.strip().rstrip("/")
        if not url:
            unique.append(item)
            continue

        if url not in seen:
            seen.add(url)
            unique.append(item)

    return unique


def deduplicate_by_name_and_university(results: list[dict]) -> list[dict]:
    """
    按「导师姓名 + 院校」去重

    将同一导师在不同来源的评价合并到首个匹配项中
    """
    merged: dict[str, dict] = {}

    for item in results:
        name = (item.get("name", "") or "").strip()
        univ = (item.get("university", "") or "").strip()
        key = f"{name}|||{univ}"

        if key not in merged:
            merged[key] = {**item}
            merged[key]["reviews"] = list(item.get("reviews", []))
            merged[key]["source"] = item.get("source", "")
        else:
            existing = merged[key]
            # 合并评价列表
            existing_reviews = existing.get("reviews", [])
            new_reviews = item.get("reviews", [])
            existing_urls = {r.get("source_url", "") for r in existing_reviews}
            for r in new_reviews:
                if r.get("source_url", "") not in existing_urls:
                    existing_reviews.append(r)
            existing["reviews"] = existing_reviews
            existing["review_count"] = len(existing_reviews)
            # 多源标记
            if item.get("source") and item["source"] not in existing.get("source", ""):
                existing["source"] = f"{existing['source']}+{item['source']}"

    return list(merged.values())


def _extract_text_keywords(text: str) -> list[str]:
    """从文本中提取评价相关关键词命中"""
    kw_map = {
        "mentorship": ["放养", "不管", "每周组会", "手把手", "指导", "push", "佛系"],
        "ethics": ["抢一作", "压榨", "尊重", "PUA", "人品", "师德"],
        "funding": ["工资", "补贴", "经费", "项目", "充足", "没钱"],
        "relationship": ["关系", "氛围", "和谐", "紧张", "友好", "支持"],
        "career": ["毕业", "出路", "就业", "学术界", "工业界", "博后"],
    }
    hits = []
    for _dim, keywords in kw_map.items():
        for kw in keywords:
            if kw in text:
                hits.append(kw)
    return hits


def rank_results(results: list[dict]) -> list[dict]:
    """
    多因子排序：来源权重 + 评价数量 + 关键词丰富度

    排序权重：
    - tier1 专业平台 +0.3
    - tier2 社交平台 +0.15
    - tier3 学术源 +0.1
    - 评价数 >=5 +0.2
    - 评价数 >=3 +0.1
    - 含负面关键词 +0.05（用户更关注避坑信息）
    """

    SOURCE_WEIGHTS = {
        "gradchoice": 0.30,
        "daoshipingjia": 0.28,
        "pi-review": 0.25,
        "ratemysupervisor": 0.25,
        "tieba": 0.15,
        "zhihu": 0.15,
        "1point3acres": 0.15,
        "douban": 0.12,
        "muchong": 0.18,
        "eeban": 0.18,
        "kaoyan": 0.15,
        "letpub": 0.12,
        "semanticscholar": 0.10,
        "github": 0.20,
        "ddgs": 0.08,  # DDGS 通用搜索结果权重最低
    }

    for item in results:
        score = 0.0

        source = (item.get("source", "") or "").lower()
        for site_key, weight in SOURCE_WEIGHTS.items():
            if site_key in source:
                score += weight
                break
        else:
            score += 0.05  # 未知来源最低权重

        review_count = item.get("review_count", 0)
        if review_count >= 5:
            score += 0.20
        elif review_count >= 3:
            score += 0.10

        # 评价内容关键词丰富度
        all_text = " ".join(
            r.get("content", "") for r in item.get("reviews", [])
        )
        keywords = _extract_text_keywords(all_text)
        score += min(len(keywords) * 0.02, 0.10)

        item["_rank_score"] = round(score, 4)

    return sorted(results, key=lambda x: x.get("_rank_score", 0), reverse=True)


def merge_and_rank(
    results: list[dict],
    dedup_by_url: bool = True,
    merge_by_advisor: bool = True,
    advisor_name: str = "",
) -> list[dict]:
    """
    一站式融合排名流水线

    将所有来源的评价合并到同一导师条目下：
    1. 名+校完全匹配 → 归入同一条
    2. 名匹配但校为空 → 归入具名校的条目
    3. 完全匿名（名和校均为空）→ 归入搜索结果名匹配的条目
    """
    if dedup_by_url:
        results = deduplicate_by_url(results)

    if merge_by_advisor:
        results = deduplicate_by_name_and_university(results)

    # ── 将所有可关联的条目合并到主条目 ──
    if results:
        # 找主条目：优先选名+校都有值的，其次选有名无校的
        full = [r for r in results if (r.get("name") or "").strip() and (r.get("university") or "").strip()]
        partial = [r for r in results if (r.get("name") or "").strip() and not (r.get("university") or "").strip()]
        anonymous = [r for r in results if not (r.get("name") or "").strip() and r.get("reviews")]

        primary = full[0] if full else (partial[0] if partial else results[0])
        to_merge = [r for r in (full[1:] + partial + anonymous) if r is not primary]

        existing_urls = {rev.get("source_url", "") for rev in primary.get("reviews", [])}
        for item in to_merge:
            for rev in item.get("reviews", []):
                url = rev.get("source_url", "")
                if url and url not in existing_urls:
                    primary["reviews"].append(rev)
                    existing_urls.add(url)
            src = item.get("source", "")
            if src and src not in primary.get("source", ""):
                primary["source"] = f"{primary['source']}+{src}"
        primary["review_count"] = len(primary["reviews"])
        results = [primary]

    results = rank_results(results)
    return results
