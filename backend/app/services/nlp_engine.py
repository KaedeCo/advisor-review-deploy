"""
NLP 分析引擎 — SnowNLP 本地情感分析 + DeepSeek 远程深度分析
"""

import re
from typing import Optional

from snownlp import SnowNLP
import httpx

from ..models import SentimentResult, DeepSeekAnalysisResponse, AdvisorProfile, AdvisorProfileRequest
from ..config import get_deepseek_api_key


def analyze_sentiment(text: str) -> SentimentResult:
    """
    使用 SnowNLP 对评论文本进行本地情感分析
    将每条评论分类为 正面(>0.6) / 负面(<0.4) / 中性([0.4, 0.6])
    """
    # 将文本拆分为单条评论
    reviews = split_reviews(text)

    positive, negative, neutral = [], [], []

    for review in reviews:
        content = review.strip()
        if len(content) < 5:
            continue

        s = SnowNLP(content)
        score = s.sentiments  # 0~1, >0.6 偏正面, <0.4 偏负面

        detail = {
            "text_preview": content[:80] + ("..." if len(content) > 80 else ""),
            "sentiment_score": round(score, 3),
            "label": (
                "positive" if score > 0.6 else ("negative" if score < 0.4 else "neutral")
            ),
        }

        if score > 0.6:
            positive.append(detail)
        elif score < 0.4:
            negative.append(detail)
        else:
            neutral.append(detail)

    return SentimentResult(
        positive_count=len(positive),
        negative_count=len(negative),
        neutral_count=len(neutral),
        details=positive + negative + neutral,
        analyzer="SnowNLP",
    )


async def deepseek_sentiment(text: str) -> SentimentResult:
    """
    使用 DeepSeek 对每条评论逐一进行情感分类
    一次 API 调用批量处理，返回与 SnowNLP 兼容的 SentimentResult
    """
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置，请先在设置页面添加")

    reviews = split_reviews(text)
    if not reviews:
        raise ValueError("未找到有效评论")

    # 截断每条评论并编号
    numbered = "\n\n".join(
        f"[{i + 1}] {r[:300]}" for i, r in enumerate(reviews[:50])
    )

    prompt = f"""你是一位专业的情感分析员。以下是对某位导师的 {len(reviews[:50])} 条学生评价。
请逐条判断每条评价的情感倾向：positive（正面/推荐）、negative（负面/批评）、neutral（中性/客观描述）。

用纯 JSON 数组返回，每个元素包含 index 和 label：
[
  {{"index": 1, "label": "positive"}},
  {{"index": 2, "label": "negative"}},
  ...
]

评价内容：
{numbered}

只返回 JSON 数组，不要包含任何其他文字。"""

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你只返回纯净的 JSON 数组，不含其他文字。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # 提取 JSON
        json_match = re.search(r"\[[\s\S]*\]", content)
        if not json_match:
            raise ValueError(f"DeepSeek 返回格式异常: {content[:200]}")

        import json
        classifications = json.loads(json_match.group())

        positive, negative, neutral = [], [], []
        for item in classifications:
            idx = item.get("index", 0) - 1
            label = item.get("label", "neutral")
            if idx < 0 or idx >= len(reviews):
                continue

            review_text = reviews[idx].strip()
            detail = {
                "text_preview": review_text[:80] + ("..." if len(review_text) > 80 else ""),
                "sentiment_score": 0.85 if label == "positive" else (0.15 if label == "negative" else 0.5),
                "label": label,
            }

            if label == "positive":
                positive.append(detail)
            elif label == "negative":
                negative.append(detail)
            else:
                neutral.append(detail)

        return SentimentResult(
            positive_count=len(positive),
            negative_count=len(negative),
            neutral_count=len(neutral),
            details=positive + negative + neutral,
            analyzer="DeepSeek",
        )


async def deepseek_analyze(text: str) -> DeepSeekAnalysisResponse:
    """
    使用 DeepSeek API 对评价进行深度分析
    返回：摘要、优点、缺点、风险标记、综合评分
    """
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置，请先在设置页面添加")

    system_prompt = """你是一位专业的学术导师评价分析师。用户会提供多条关于某位研究生导师的学生评价。

请用中文输出以下 JSON 格式的分析结果（不要包含 markdown 代码块标记）：
{
    "summary": "一段话总结该导师的整体情况",
    "pros": ["优点1", "优点2", ...],
    "cons": ["缺点/问题1", "缺点/问题2", ...],
    "risk_flags": ["需要警惕的红旗信号1", ...],
    "overall_rating": 7.5
}

评分标准（满分10分）：
- 9-10: 极其推荐的优秀导师
- 7-8: 推荐的好导师
- 5-6: 一般，需谨慎考虑
- 3-4: 不推荐，存在明显问题
- 0-2: 强烈不推荐，严重红旗

注意：要基于学生实际评价内容进行客观分析，不要凭空捏造。"""

    user_prompt = f"以下是对某位导师的多条学生评价，请进行分析：\n\n{text[:4000]}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]

            # 提取 JSON（可能被包裹在 ```json 中）
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                import json
                analysis = json.loads(json_match.group())
                return DeepSeekAnalysisResponse(
                    summary=analysis.get("summary", ""),
                    pros=analysis.get("pros", []),
                    cons=analysis.get("cons", []),
                    risk_flags=analysis.get("risk_flags", []),
                    overall_rating=analysis.get("overall_rating"),
                    analyzer="DeepSeek",
                )

            return DeepSeekAnalysisResponse(summary=content, analyzer="DeepSeek")

    except httpx.HTTPError as e:
        raise ValueError(f"DeepSeek API 请求失败: {e}")


def split_reviews(text: str) -> list[str]:
    """
    将混合文本拆分为单条评论
    支持多种分隔符模式
    """
    if not text:
        return []

    # 常见分隔符
    separators = [
        r"\n\s*- ",      # - 开头的行
        r"\n\s*\*\s*",   # * 开头的行
        r"\n\s*\d+[\.、]",  # 数字序号
        r"\n---+",       # 分隔线
        r"\n{2,}",       # 双换行以上
    ]

    segments = [text]
    for sep_pattern in separators:
        new_segments = []
        for seg in segments:
            parts = re.split(sep_pattern, seg)
            new_segments.extend(parts)
        segments = new_segments

    # 过滤有效片段
    results = []
    for seg in segments:
        cleaned = seg.strip()
        if len(cleaned) >= 10:  # 至少10个字符才算一条有效评论
            results.append(cleaned)

    return results if results else [text]


async def generate_advisor_profile(req: AdvisorProfileRequest) -> AdvisorProfile:
    """使用 DeepSeek 生成导师画像"""
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置")

    system_prompt = """你是一位资深的学术导师评价分析师。根据学生评价生成导师画像。
用中文输出纯 JSON（不要 markdown 代码块标记），格式如下：
{
    "one_line_summary": "一句话概括该导师的核心特点",
    "teaching_style": "指导风格：放养/微操/手把手等，100字内",
    "personality": "人品师德：是否尊重学生、有无PUA倾向等，100字内",
    "research_strength": "学术水平：论文质量、研究方向前沿性等，100字内",
    "student_outcome": "学生出路：毕业去向、就业质量等，100字内",
    "risk_level": "低风险/中风险/高风险",
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "overall_recommendation": "总体推荐意见，50字内"
}"""

    user_prompt = f"导师：{req.advisor_name}，院校：{req.university} {req.department}\n\n学生评价：\n{req.reviews_text[:3000]}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                    "temperature": 0.3,
                    "max_tokens": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                import json
                profile = json.loads(json_match.group())
                return AdvisorProfile(
                    advisor_name=req.advisor_name,
                    university=req.university,
                    department=req.department,
                    one_line_summary=profile.get("one_line_summary", ""),
                    teaching_style=profile.get("teaching_style", ""),
                    personality=profile.get("personality", ""),
                    research_strength=profile.get("research_strength", ""),
                    student_outcome=profile.get("student_outcome", ""),
                    risk_level=profile.get("risk_level", ""),
                    keywords=profile.get("keywords", []),
                    overall_recommendation=profile.get("overall_recommendation", ""),
                )

            return AdvisorProfile(
                advisor_name=req.advisor_name,
                university=req.university,
                department=req.department,
                one_line_summary=content[:200],
            )
    except httpx.HTTPError as e:
        raise ValueError(f"DeepSeek API 请求失败: {e}")
