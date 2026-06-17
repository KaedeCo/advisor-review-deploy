"""
六维评分引擎 — 6 路并行 DeepSeek 调用 + 本地 Red Flag 正则检测

六个维度分别构造专用 Prompt，让大模型聚焦单一维度进行精准推断。
每路调用相互独立，通过 asyncio.gather 并发执行，6 路 ~2-5 秒完成。
"""

import asyncio
import json as json_mod
import logging
import re
from typing import Optional

import httpx

from ..config import get_deepseek_api_key
from ..models import DimensionScore, DimensionScores

logger = logging.getLogger("scorer")

# ═══════════════════════════════════════════════════════════════
#  维度权重（报告 §2.2）
# ═══════════════════════════════════════════════════════════════

DIMENSION_WEIGHTS = {
    "academic": 4.0,       # ★★★★☆ 高
    "mentorship": 5.0,     # ★★★★★ 极高
    "ethics": 5.0,         # ★★★★★ 极高
    "relationship": 4.0,   # ★★★★☆ 高
    "funding": 3.0,        # ★★★☆☆ 中高
    "career": 4.0,         # ★★★★☆ 高
}

# ═══════════════════════════════════════════════════════════════
#  各维度 DeepSeek Prompt 模板
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_TEMPLATE = """你是一位专业的学术导师评价分析师。
用户会提供多条关于某位研究生导师的学生评价。

请聚焦于「{dim_cn}」这一维度进行深度分析。

评分标准（满分 10 分）：
- 9-10: 极其优秀，学生一致好评
- 7-8: 良好，大多数学生满意
- 5-6: 一般，褒贬不一
- 3-4: 较差，存在明显问题
- 1-2: 极差，学生强烈不满

请用以下 JSON 格式输出（不要包含 markdown 代码块标记）：
{{
    "score": 7.5,
    "reasoning": "一段话说明该维度下的评价依据和推断逻辑",
    "red_flags": ["需要警惕的问题1", "问题2"]
}}

注意：
1. 基于学生实际评价内容推断，不要凭空捏造
2. 如果某维度相关评价不足，score 可设为 5.0（中性），reasoning 中说明"信息不足"
3. red_flags 只列入有明确证据支撑的严重问题，无则为空数组"""

DIMENSION_PROMPTS = {
    "academic": {
        "dim_cn": "学术水平",
        "focus": """分析导师的学术能力：
- 研究方向是否前沿
- 论文质量和发表情况
- 学生对导师学术能力的评价
- 导师在领域内的知名度
从学生评价中推断导师的学术水平。""",
    },
    "mentorship": {
        "dim_cn": "指导风格",
        "focus": """分析导师的指导方式：
- 是"放养型"还是"微操型"
- 组会频率和质量
- 是否亲自指导学生
- 是否会"挂名"而不实际指导
- 学生反馈的指导体验
从学生评价中推断导师的指导风格（注意区分正面和负面描述）。""",
    },
    "ethics": {
        "dim_cn": "人品师德",
        "focus": """分析导师的道德品质：
- 是否尊重学生
- 是否存在 PUA、压榨、精神虐待
- 是否会抢学生第一作者
- 是否存在学术不端行为
- 是否公平对待所有学生
从学生评价中推断导师的人品师德。关注任何负面信号。""",
    },
    "relationship": {
        "dim_cn": "师生关系",
        "focus": """分析导师与学生的相处氛围：
- 学生的满意度
- 沟通是否顺畅
- 是否提供心理支持
- 整体氛围是紧张还是融洽
- 是否有学生感到"被抛弃"或"孤立"
从学生评价中推断导师的师生关系质量。""",
    },
    "funding": {
        "dim_cn": "科研经费",
        "focus": """分析导师的经费状况：
- 课题组的设备和实验条件
- 学生津贴/补贴水平
- 是否有经费支持学生参加学术会议
- 经费是否充裕
- 学生是否提到"缺钱"、"自费"等
从学生评价中推断导师的科研经费充足度。""",
    },
    "career": {
        "dim_cn": "学生出路",
        "focus": """分析导师指导的毕业去向：
- 学生平均毕业年限
- 毕业后去学术界还是工业界
- 就业质量如何
- 导师是否会帮学生推荐工作
- 是否有学生延期毕业
从学生评价中推断导师的学生出路质量。""",
    },
}

# ═══════════════════════════════════════════════════════════════
#  本地 Red Flag 正则模式（报告 §2.4）
# ═══════════════════════════════════════════════════════════════

RED_FLAG_PATTERNS: list[tuple[str, str, str]] = [
    # (正则模式, 标签, 严重级别)
    (r"换导师|换老师|换了导师|想换导", "换导师", "critical"),
    (r"退学|quit|drop.?out|withdraw", "退学风险", "critical"),
    (r"抑郁|depression|anxiety|焦虑|崩溃|mental.?health", "心理健康问题", "critical"),
    (r"抢一作|抢第.作者|署名问题|authorship", "抢一作/署名争议", "critical"),
    (r"从未见过面|没见过|见不到人|联系不上|找不到人|失踪", "导师失联", "critical"),
    (r"PUA|pua|打压|贬低|羞辱|侮辱|骂|吼|发火", "精神打压/PUA", "high"),
    (r"压榨|剥削|996|007|熬夜|通宵.*加班|周末.*加班", "过度压榨", "high"),
    (r"延期|延毕|delay.*graduat|超期|多年.*毕业", "延期毕业", "high"),
    (r"噩梦|后悔|再.*不想|劝退|千万别", "强烈负面情绪", "high"),
    (r"放养|基本.*不管|自生自灭|没人管|完全不指导", "放养型指导", "medium"),
    (r"补贴.*少|工资.*低|没钱|穷|自费|funding.*low", "经费紧缺", "medium"),
]


async def _call_deepseek_for_dimension(
    client: httpx.AsyncClient,
    api_key: str,
    dim_key: str,
    dim_config: dict,
    reviews_text: str,
) -> DimensionScore:
    """对单个维度调用 DeepSeek"""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(dim_cn=dim_config["dim_cn"])
    user_prompt = f"{dim_config['focus']}\n\n以下是对某位导师的学生评价汇总，请进行分析：\n\n{reviews_text[:3500]}"

    try:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 800,
            },
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # 提取 JSON（可能被包裹在 ```json 中）
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            result = json_mod.loads(json_match.group())
            return DimensionScore(
                score=float(result.get("score", 5.0)),
                reasoning=result.get("reasoning", ""),
                red_flags=result.get("red_flags", []),
            )

        # 回退：无法解析 JSON 时给中性分
        logger.warning("[%s] DeepSeek 返回无法解析 JSON，使用默认值", dim_key)
        return DimensionScore(score=5.0, reasoning=f"（解析失败）{content[:200]}", red_flags=[])

    except (httpx.HTTPError, json_mod.JSONDecodeError, ValueError) as e:
        logger.error("[%s] DeepSeek 调用失败: %s", dim_key, e)
        return DimensionScore(
            score=5.0,
            reasoning=f"评分服务异常: {str(e)[:100]}",
            red_flags=[],
        )


def detect_red_flags_local(text: str) -> list[dict]:
    """
    本地正则检测 Red Flag 信号
    返回: [{"tag": "换导师", "level": "critical", "matched_text": "..."}, ...]
    """
    flags = []
    seen_tags = set()

    for pattern, tag, level in RED_FLAG_PATTERNS:
        if tag in seen_tags:
            continue
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            flags.append({
                "tag": tag,
                "level": level,
                "matched_text": matches[0][:50] if isinstance(matches[0], str) else str(matches[0])[:50],
            })
            seen_tags.add(tag)

    # 按严重级别排序
    level_order = {"critical": 0, "high": 1, "medium": 2}
    flags.sort(key=lambda f: level_order.get(f["level"], 9))

    return flags


async def score_six_dimensions(
    reviews_text: str,
    review_count: int = 0,
) -> tuple[DimensionScores, list[str]]:
    """
    六维并行评分入口

    返回:
    - DimensionScores: 六个维度的评分 + 综合加权分
    - list[str]: 跨维度汇总的严重红旗信号
    """
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置，请先在设置页面添加")

    # 本地 Red Flag 预检
    local_flags = detect_red_flags_local(reviews_text)

    async with httpx.AsyncClient() as client:
        tasks = [
            _call_deepseek_for_dimension(client, api_key, dim_key, dim_config, reviews_text)
            for dim_key, dim_config in DIMENSION_PROMPTS.items()
        ]
        results: list[DimensionScore] = await asyncio.gather(*tasks)

    # 组装结果
    scores = DimensionScores(
        academic=results[0],
        mentorship=results[1],
        ethics=results[2],
        relationship=results[3],
        funding=results[4],
        career=results[5],
        overall=0,
        confidence=0,
    )

    # 计算加权综合分
    weighted_sum = 0.0
    total_weight = sum(DIMENSION_WEIGHTS.values())
    for dim_key, dim_score in [
        ("academic", scores.academic),
        ("mentorship", scores.mentorship),
        ("ethics", scores.ethics),
        ("relationship", scores.relationship),
        ("funding", scores.funding),
        ("career", scores.career),
    ]:
        weighted_sum += dim_score.score * DIMENSION_WEIGHTS[dim_key]

    scores.overall = round(weighted_sum / total_weight, 1)

    # 置信度（基于评价数量）
    if review_count >= 20:
        scores.confidence = 0.95
    elif review_count >= 10:
        scores.confidence = 0.80
    elif review_count >= 5:
        scores.confidence = 0.60
    elif review_count >= 1:
        scores.confidence = 0.35
    else:
        scores.confidence = 0.15

    # 汇总红旗信号
    all_red_flags: list[str] = []
    # 本地正则检测结果
    for f in local_flags:
        label = f"[{f['level'].upper()}] {f['tag']}"
        if f.get("matched_text"):
            label += f" — 匹配: \"{f['matched_text']}\""
        all_red_flags.append(label)
    # DeepSeek 各维度检测结果
    for dim_key in ["academic", "mentorship", "ethics", "relationship", "funding", "career"]:
        dim: DimensionScore = getattr(scores, dim_key)
        for rf in dim.red_flags:
            tag = f"[{dim_key.upper()}] {rf}"
            if tag not in all_red_flags:
                all_red_flags.append(tag)

    return scores, all_red_flags
