"""
设置 API — 管理 DeepSeek API Key / Tavily API Key / 平台 Cookie / 平台开关
"""

from fastapi import APIRouter
from ..models import SettingsResponse, PlatformConfigUpdate, DeepseekConfigUpdate, TavilyConfigUpdate
from ..config import (
    load_config,
    get_deepseek_api_key,
    set_deepseek_api_key,
    get_tavily_api_key,
    set_tavily_api_key,
    get_platform_cookie,
    set_platform_cookie,
    get_enabled_platforms,
    update_platform_enabled,
)

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """获取当前所有设置状态"""
    config = load_config()
    api_key = config.get("deepseek", {}).get("api_key", "")
    gc_cookie = config.get("cookies", {}).get("gradchoice", "")

    token_preview = ""
    raw_token = _extract_raw_jwt(gc_cookie)
    if raw_token and len(raw_token) > 28:
        token_preview = f"{raw_token[:20]}...{raw_token[-8:]}"

    # Tavily 状态 — 读取模块级全局缓存，不主动探测
    tavily_key = config.get("tavily", {}).get("api_key", "")
    tavily_configured = bool(tavily_key and len(tavily_key) > 10)
    tavily_ok = False
    tavily_detail = "Not checked"
    try:
        from ..services.search_engine import TavilySearchEngine
        cached_ok, cached_detail = TavilySearchEngine.get_connectivity_status()
        if cached_ok is True:
            tavily_ok = True
            tavily_detail = "Connected"
        elif cached_ok is False:
            tavily_ok = False
            tavily_detail = cached_detail  # 具体错误信息
        else:
            tavily_detail = cached_detail
    except Exception as ex:
        tavily_detail = str(ex)[:100]

    letpub_cookie = config.get("cookies", {}).get("letpub", "")
    tavily_key = config.get("tavily", {}).get("api_key", "")
    tavily_preview = ""
    if tavily_key and len(tavily_key) > 12:
        tavily_preview = tavily_key[:8] + "..." + tavily_key[-4:]

    return SettingsResponse(
        deepseek_configured=bool(api_key and len(api_key) > 10),
        gradchoice_cookie_set=bool(gc_cookie),
        gradchoice_token_preview=token_preview,
        letpub_cookie_set=bool(letpub_cookie and len(letpub_cookie) > 5),
        letpub_cookie_preview=(letpub_cookie[:20] + "..." + letpub_cookie[-8:]) if len(letpub_cookie) > 28 else letpub_cookie[:30] if letpub_cookie else "",
        tavily_configured=tavily_configured,
        tavily_available=tavily_ok,
        tavily_detail=tavily_detail,
        tavily_key_preview=tavily_preview,
        platforms=[
            {"key": k, **v} for k, v in config.get("platforms", {}).items()
        ],
    )


def _extract_raw_jwt(stored_value: str) -> str:
    """从存储值中提取原始 JWT Token

    支持两种格式：
    1. 裸 JWT：eyJhbGciOiJIUzI1NiIs...
    2. key=value 包装格式：access_token="eyJ..." 或 access_token=eyJ...
    """
    if not stored_value:
        return ""
    stored_value = stored_value.strip()
    # 已经是裸 JWT
    if stored_value.startswith("eyJ"):
        return stored_value
    # 尝试从 key=value 格式提取
    import re
    m = re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', stored_value)
    return m.group(0) if m else ""


@router.post("/settings/deepseek")
async def update_deepseek(req: DeepseekConfigUpdate):
    """更新 DeepSeek API Key"""
    if len(req.api_key) < 10:
        raise ValueError("API Key 长度不足，请检查输入")
    set_deepseek_api_key(req.api_key)
    return {"status": "ok", "message": "DeepSeek API Key 已保存"}


@router.post("/settings/tavily")
async def update_tavily(req: TavilyConfigUpdate):
    """更新 Tavily API Key"""
    if not req.api_key or not req.api_key.strip():
        set_tavily_api_key("")
        return {"status": "ok", "message": "Tavily API Key 已清除"}
    if len(req.api_key.strip()) < 10:
        raise ValueError("API Key 长度不足")
    set_tavily_api_key(req.api_key.strip())
    return {"status": "ok", "message": "Tavily API Key 已保存"}


@router.post("/settings/cookie/{platform}")
async def update_cookie(platform: str, cookie: str = ""):
    """更新指定平台的 Cookie"""
    valid_platforms = ["gradchoice", "tieba", "muchong", "eeban", "letpub"]
    if platform not in valid_platforms:
        raise ValueError(f"不支持的平台: {platform}")
    set_platform_cookie(platform, cookie)
    return {"status": "ok", "message": f"{platform} Cookie 已保存"}


@router.post("/settings/platform")
async def toggle_platform(req: PlatformConfigUpdate):
    """切换平台的启用/禁用状态"""
    update_platform_enabled(req.platform, req.enabled)
    return {"status": "ok", "message": f"平台 {req.platform} 已{'启用' if req.enabled else '禁用'}"}


@router.post("/settings/check-tavily")
async def check_tavily_connectivity():
    """手动检查 Tavily API 连通性"""
    import asyncio

    try:
        from ..services.search_engine import TavilySearchEngine
    except ImportError:
        return {"available": False, "detail": "tavily-python not installed. Run: pip install tavily-python"}

    TavilySearchEngine.reset_connectivity()
    e = TavilySearchEngine()

    try:
        ok = await asyncio.to_thread(lambda: e.available)
    except asyncio.CancelledError:
        return {"available": False, "detail": "Check cancelled"}
    except Exception as ex:
        return {"available": False, "detail": str(ex)[:200]}

    _, detail = TavilySearchEngine.get_connectivity_status()
    return {"available": ok, "detail": detail}


@router.post("/settings/verify-token")
async def verify_gradchoice_token():
    """
    验证 GradChoice Access Token 是否有效
    
    向 GradChoice 发送测试请求，检查认证状态
    """
    from ..services.crawlers.gradchoice import GradChoiceScraper
    # 创建临时爬虫实例（不用缓存，确保使用最新配置）
    scraper = GradChoiceScraper()
    result = scraper.verify_token()
    return result


@router.post("/settings/verify-letpub")
async def verify_letpub_cookie():
    """验证 LetPub PHPSESSID 是否有效"""
    phpsessid = get_platform_cookie("letpub")
    if not phpsessid or len(phpsessid) < 5:
        return {"valid": False, "detail": "PHPSESSID 未配置或长度不足"}

    import httpx
    try:
        cookies = {"PHPSESSID": phpsessid.strip()}
        async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
            # 先访问首页确认登录态
            resp = await client.get(
                f"https://www.letpub.com.cn/index.php?page=grant",
                headers={"User-Agent": "Mozilla/5.0 Chrome/124"},
                follow_redirects=True,
            )
            text = resp.text
            # 检查是否显示登录链接（未登录）还是用户名（已登录）
            if "退出" in text or "个人中心" in text or "会员" in text:
                return {"valid": True, "detail": "Cookie 有效，已登录"}
            elif "登录" in text.lower() and "注册" in text.lower():
                return {"valid": False, "detail": "Cookie 无效，页面仍显示登录/注册入口"}
            # 尝试搜索'张三'验证数据返回
            from urllib.parse import quote
            search_url = (f"https://www.letpub.com.cn/index.php?page=grant&name={quote('张三')}"
                          f"&company=&person={quote('张三')}")
            resp2 = await client.get(search_url, follow_redirects=True)
            if "keyword-datalist" in resp2.text and '<td>' in resp2.text:
                return {"valid": True, "detail": "Cookie 有效，搜索结果正常返回"}
            return {"valid": True, "detail": "Cookie 可能有效（页面正常加载）"}
    except Exception as e:
        return {"valid": False, "detail": f"验证请求失败: {str(e)[:200]}"}
