"""
分析 API — SnowNLP 本地情感分析 + DeepSeek 远程深度分析 + 六维评分 + 持久化 CRUD
"""

import time
from fastapi import APIRouter, HTTPException, Query

from ..models import (
    SentimentResult,
    SentimentAnalysisRequest,
    DeepSeekAnalysisRequest,
    DeepSeekAnalysisResponse,
    SixDimensionRequest,
    SixDimensionResponse,
    AdvisorProfileRequest,
)
from ..services.nlp_engine import analyze_sentiment, deepseek_analyze, deepseek_sentiment, generate_advisor_profile
from ..services.scorer import score_six_dimensions
from ..db import (
    save_analysis_result,
    get_analysis_list,
    get_analysis_detail,
    delete_analysis,
)

router = APIRouter()


@router.post("/analyze/sentiment", response_model=SentimentResult)
async def sentiment_analysis(req: SentimentAnalysisRequest):
    """SnowNLP 情感分析 — JSON Body 传参，避免 URL 过长 431 错误"""
    if not req.reviews_text or not req.reviews_text.strip():
        raise HTTPException(status_code=400, detail="评论文本不能为空")

    start_time = time.time()
    result = analyze_sentiment(req.reviews_text)
    result.total_count = result.positive_count + result.negative_count + result.neutral_count
    elapsed = round(time.time() - start_time, 2)
    print(f"[SnowNLP] 分析完成，耗时 {elapsed}s，共 {result.total_count} 条")

    try:
        save_analysis_result(
            advisor_name=req.advisor_name,
            university=req.university,
            department=req.department,
            review_count=req.review_count,
            sentiment={"positive_count": result.positive_count,
                        "negative_count": result.negative_count,
                        "neutral_count": result.neutral_count,
                        "total_count": result.total_count,
                        "details": result.details},
            reviews_text=req.reviews_text,
        )
    except Exception as e:
        print(f"[SnowNLP] 持久化失败: {e}")

    return result


@router.post("/analyze/sentiment/deepseek", response_model=SentimentResult)
async def deepseek_sentiment_analysis(req: SentimentAnalysisRequest):
    """DeepSeek 情感分类 — 逐条评论用 LLM 判断正/负/中性"""
    if not req.reviews_text or not req.reviews_text.strip():
        raise HTTPException(status_code=400, detail="评论文本不能为空")

    start_time = time.time()
    try:
        result = await deepseek_sentiment(req.reviews_text, api_key=req.deepseek_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result.total_count = result.positive_count + result.negative_count + result.neutral_count
    elapsed = round(time.time() - start_time, 2)
    print(f"[DeepSeek-Sentiment] 完成，耗时 {elapsed}s，共 {result.total_count} 条")

    # 持久化
    try:
        save_analysis_result(
            advisor_name=req.advisor_name,
            university=req.university,
            department=req.department,
            review_count=req.review_count,
            deepseek_sentiment={"positive_count": result.positive_count,
                                "negative_count": result.negative_count,
                                "neutral_count": result.neutral_count,
                                "total_count": result.total_count,
                                "details": result.details,
                                "analyzer": "DeepSeek"},
            reviews_text=req.reviews_text,
        )
        print(f"[DeepSeek-Sentiment] 结果已持久化: {req.advisor_name}")
    except Exception as e:
        print(f"[DeepSeek-Sentiment] 持久化失败: {e}")

    return result


@router.post("/analyze/deepseek", response_model=DeepSeekAnalysisResponse)
async def deepseek_analysis(
    req: DeepSeekAnalysisRequest,
    advisor_name: str = Query(default=""),
    university: str = Query(default=""),
    department: str = Query(default=""),
    review_count: int = Query(default=0),
):
    """DeepSeek 深度分析 — 自动持久化"""
    if not req.reviews_text.strip():
        raise HTTPException(status_code=400, detail="评论文本不能为空")

    start_time = time.time()
    result = await deepseek_analyze(req.reviews_text, api_key=req.deepseek_key)
    elapsed = round(time.time() - start_time, 2)
    print(f"[DeepSeek] 分析完成，耗时 {elapsed}s")

    # 自动持久化
    try:
        save_analysis_result(
            advisor_name=advisor_name,
            university=university,
            department=department,
            review_count=review_count,
            deepseek={"summary": result.summary, "pros": result.pros,
                       "cons": result.cons, "risk_flags": result.risk_flags,
                       "overall_rating": result.overall_rating},
            reviews_text=req.reviews_text,
        )
        print(f"[DeepSeek] 结果已持久化: {advisor_name}")
    except Exception as e:
        print(f"[DeepSeek] 持久化失败: {e}")

    return result


# ─── 分析结果 CRUD ──────────────────────────────────────────

@router.get("/analyze/list")
async def list_analyses(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """获取所有分析结果列表"""
    return {"records": get_analysis_list(limit=limit, offset=offset)}


@router.get("/analyze/detail/{record_id}")
async def get_analysis(record_id: int):
    """获取单条分析完整数据"""
    record = get_analysis_detail(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return record


@router.delete("/analyze/{record_id}")
async def delete_analysis_record(record_id: int):
    """删除一条分析记录"""
    ok = delete_analysis(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return {"status": "ok", "message": "已删除"}


# ─── 六维评分 ─────────────────────────────────────────────

@router.post("/analyze/dimensions", response_model=SixDimensionResponse)
async def analyze_dimensions(req: SixDimensionRequest):
    """
    六维并行评分 — 6 路 DeepSeek 同时调用，每路聚焦一个维度

    维度包括：学术水平、指导风格、人品师德、师生关系、科研经费、学生出路
    同时执行本地 Red Flag 正则检测，与 DeepSeek 结果合并
    """
    if not req.reviews_text or not req.reviews_text.strip():
        raise HTTPException(status_code=400, detail="评论文本不能为空")

    start_time = time.time()

    try:
        scores, red_flags_summary = await score_six_dimensions(
            req.reviews_text,
            review_count=req.review_count,
            api_key=req.deepseek_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"六维评分失败: {e}")

    elapsed = round(time.time() - start_time, 2)
    print(f"[六维评分] 完成，耗时 {elapsed}s，综合分 {scores.overall}")

    # 持久化
    saved = False
    try:
        save_analysis_result(
            advisor_name=req.advisor_name,
            university=req.university,
            department=req.department,
            review_count=req.review_count,
            deepseek=None,  # 不覆盖已有的 DeepSeek 综合结果
            dimension_scores={
                "academic": {"score": scores.academic.score, "reasoning": scores.academic.reasoning, "red_flags": scores.academic.red_flags},
                "mentorship": {"score": scores.mentorship.score, "reasoning": scores.mentorship.reasoning, "red_flags": scores.mentorship.red_flags},
                "ethics": {"score": scores.ethics.score, "reasoning": scores.ethics.reasoning, "red_flags": scores.ethics.red_flags},
                "relationship": {"score": scores.relationship.score, "reasoning": scores.relationship.reasoning, "red_flags": scores.relationship.red_flags},
                "funding": {"score": scores.funding.score, "reasoning": scores.funding.reasoning, "red_flags": scores.funding.red_flags},
                "career": {"score": scores.career.score, "reasoning": scores.career.reasoning, "red_flags": scores.career.red_flags},
                "overall": scores.overall,
                "confidence": scores.confidence,
            },
            reviews_text=req.reviews_text,
        )
        saved = True
        print(f"[六维评分] 结果已持久化: {req.advisor_name}")
    except Exception as e:
        print(f"[六维评分] 持久化失败: {e}")

    return SixDimensionResponse(
        advisor_name=req.advisor_name,
        scores=scores,
        red_flags_summary=red_flags_summary,
        saved=saved,
    )


@router.post("/analyze/profile")
async def advisor_profile(req: AdvisorProfileRequest):
    """导师画像 — DeepSeek 聚合提取导师形象"""
    if not req.reviews_text or not req.reviews_text.strip():
        raise HTTPException(status_code=400, detail="评论文本不能为空")

    start_time = time.time()
    try:
        profile = await generate_advisor_profile(req, api_key=req.deepseek_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    elapsed = round(time.time() - start_time, 2)
    print(f"[导师画像] 完成，耗时 {elapsed}s: {req.advisor_name}")

    # 持久化
    try:
        save_analysis_result(
            advisor_name=req.advisor_name,
            university=req.university,
            department=req.department,
            review_count=req.reviews_text.count('\n\n') + 1,
            advisor_profile={
                "one_line_summary": profile.one_line_summary,
                "teaching_style": profile.teaching_style,
                "personality": profile.personality,
                "research_strength": profile.research_strength,
                "student_outcome": profile.student_outcome,
                "risk_level": profile.risk_level,
                "keywords": profile.keywords,
                "overall_recommendation": profile.overall_recommendation,
            },
            reviews_text=req.reviews_text,
        )
        print(f"[导师画像] 结果已持久化: {req.advisor_name}")
    except Exception as e:
        print(f"[导师画像] 持久化失败: {e}")

    return profile
