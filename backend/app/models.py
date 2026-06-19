"""
Pydantic 数据模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    """搜索请求"""
    advisor_name: str = Field(..., min_length=1, max_length=50, description="导师姓名")
    university: str = Field(default="", max_length=100, description="院校名称")
    department: str = Field(default="", max_length=100, description="院系名称")
    platforms: list[str] = Field(
        default_factory=list,
        description="指定的平台列表，空列表表示使用全部已启用平台",
    )
    # 部署版：API Key/Cookie 由前端传入
    deepseek_key: str = Field(default="", description="DeepSeek API Key（由前端 localStorage 提供）")
    tavily_key: str = Field(default="", description="Tavily API Key（由前端 localStorage 提供）")
    cookies: dict = Field(default_factory=dict, description="平台 Cookies，如 {gradchoice: '...', letpub: '...'}")


class ReviewItem(BaseModel):
    """单条评价"""
    author: str = ""
    rating: Optional[float] = None
    date: str = ""
    content: str = ""
    source: str = ""
    source_url: str = ""


class AdvisorResult(BaseModel):
    """单个导师的搜索结果"""
    name: str = ""
    university: str = ""
    department: str = ""
    overall_score: Optional[float] = None
    review_count: int = 0
    reviews: list[ReviewItem] = Field(default_factory=list)
    source: str = ""
    detail_url: str = ""


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str = ""
    results: list[AdvisorResult] = Field(default_factory=list)
    total_count: int = 0
    platforms_used: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


class SentimentResult(BaseModel):
    """情感分析结果"""
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    total_count: int = 0
    details: list[dict] = Field(default_factory=list)
    analyzer: str = "SnowNLP"


class DeepSeekAnalysisRequest(BaseModel):
    """DeepSeek 分析请求"""
    reviews_text: str = Field(..., description="待分析的评论文本汇总")
    deepseek_key: str = Field(default="", description="DeepSeek API Key（由前端 localStorage 提供）")


class SentimentAnalysisRequest(BaseModel):
    """情感分析请求（JSON Body，避免 URL 参数过长 431 错误）"""
    reviews_text: str = Field(..., description="待分析的评论文本汇总")
    advisor_name: str = ""
    university: str = ""
    department: str = ""
    review_count: int = 0
    deepseek_key: str = Field(default="", description="DeepSeek API Key（由前端 localStorage 提供）")


class DeepSeekAnalysisResponse(BaseModel):
    """DeepSeek 分析响应"""
    summary: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    overall_rating: Optional[float] = None
    analyzer: str = "DeepSeek"


class SettingsResponse(BaseModel):
    """设置页响应"""
    deepseek_configured: bool = False
    gradchoice_cookie_set: bool = False
    gradchoice_token_preview: str = ""
    letpub_cookie_set: bool = False
    letpub_cookie_preview: str = ""
    tavily_configured: bool = False
    tavily_available: bool = False
    tavily_detail: str = ""
    tavily_key_preview: str = ""
    platforms: list[dict] = Field(default_factory=list)


class PlatformConfigUpdate(BaseModel):
    """平台配置更新"""
    platform: str = Field(..., description="平台标识")
    enabled: bool = Field(..., description="是否启用")


class DeepseekConfigUpdate(BaseModel):
    """DeepSeek 配置更新"""
    api_key: str = Field(..., description="API Key")


class TavilyConfigUpdate(BaseModel):
    """Tavily 配置更新"""
    api_key: str = Field(..., description="Tavily API Key")


# ═══════════════════════════════════════════════════════════════
#  六维评分模型
# ═══════════════════════════════════════════════════════════════

class DimensionScore(BaseModel):
    """单个维度评分"""
    score: float = Field(..., ge=1, le=10, description="1-10 分")
    reasoning: str = Field(default="", description="评分依据")
    red_flags: list[str] = Field(default_factory=list, description="该维度发现的红旗信号")


class DimensionScores(BaseModel):
    """六维评分汇总"""
    academic: DimensionScore = Field(description="学术水平")
    mentorship: DimensionScore = Field(description="指导风格")
    ethics: DimensionScore = Field(description="人品师德")
    relationship: DimensionScore = Field(description="师生关系")
    funding: DimensionScore = Field(description="科研经费")
    career: DimensionScore = Field(description="学生出路")
    overall: float = Field(default=0, ge=0, le=10, description="综合加权得分")
    confidence: float = Field(default=0, ge=0, le=1, description="置信度")


class SixDimensionRequest(BaseModel):
    """六维评分请求"""
    reviews_text: str = Field(..., min_length=10, description="评论文本汇总")
    advisor_name: str = Field(default="", description="导师姓名")
    university: str = Field(default="", description="院校")
    department: str = Field(default="", description="院系")
    review_count: int = Field(default=0, description="评价数量")
    deepseek_key: str = Field(default="", description="DeepSeek API Key（由前端 localStorage 提供）")


class SixDimensionResponse(BaseModel):
    """六维评分响应"""
    advisor_name: str = ""
    scores: DimensionScores
    red_flags_summary: list[str] = Field(default_factory=list, description="跨维度汇总的严重红旗信号")
    saved: bool = False


class AdvisorProfileRequest(BaseModel):
    """导师画像请求"""
    reviews_text: str = Field(..., min_length=10, description="评论文本汇总")
    advisor_name: str = ""
    university: str = ""
    department: str = ""
    deepseek_key: str = Field(default="", description="DeepSeek API Key（由前端 localStorage 提供）")


class AdvisorProfile(BaseModel):
    """导师画像响应"""
    advisor_name: str = ""
    university: str = ""
    department: str = ""
    one_line_summary: str = ""
    teaching_style: str = ""
    personality: str = ""
    research_strength: str = ""
    student_outcome: str = ""
    risk_level: str = ""
    keywords: list[str] = Field(default_factory=list)
    overall_recommendation: str = ""
