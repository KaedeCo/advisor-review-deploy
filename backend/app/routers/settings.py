"""
设置 API — 部署版：所有 API Key/Cookie 由前端 localStorage 管理，后端不持久化。
仅提供验证端点（接受参数）和平台列表查询。
"""

from fastapi import APIRouter, Query
from ..config import load_config, get_platform_cookie

router = APIRouter()


@router.get("/settings")
async def get_settings():
    """获取平台列表（公开信息，不含任何 Key/Cookie）"""
    config = load_config()
    return {
        "platforms": [
            {"key": k, **v} for k, v in config.get("platforms", {}).items()
        ],
    }


@router.get("/platforms")
async def list_platforms():
    """获取所有可用平台及其状态"""
    config = load_config()
    return config.get("platforms", {})


# ═══════════════════════════════════════════════════════════
#  验证端点（接收参数，不读服务端配置）
# ═══════════════════════════════════════════════════════════

@router.post("/settings/check-tavily")
async def check_tavily_connectivity(tavily_key: str = ""):
    """手动检查 Tavily API 连通性（使用前端传来的 key）"""
    if not tavily_key or len(tavily_key) < 10:
        return {"available": False, "detail": "API Key 未提供或长度不足"}

    import asyncio
    try:
        from ..services.search_engine import TavilySearchEngine
    except ImportError:
        return {"available": False, "detail": "tavily-python not installed"}

    e = TavilySearchEngine(api_key=tavily_key)
    try:
        ok = await asyncio.to_thread(lambda: e.available)
    except asyncio.CancelledError:
        return {"available": False, "detail": "Check cancelled"}
    except Exception as ex:
        return {"available": False, "detail": str(ex)[:200]}

    _, detail = TavilySearchEngine.get_connectivity_status()
    return {"available": ok, "detail": detail}


@router.post("/settings/verify-token")
async def verify_gradchoice_token(token: str = ""):
    """验证 GradChoice Access Token（使用前端传来的 token）"""
    if not token or len(token) < 20:
        return {"valid": False, "status_code": 0, "detail": "Token 未提供或长度不足", "url": ""}

    from ..services.crawlers.gradchoice import GradChoiceScraper
    scraper = GradChoiceScraper(access_token=token)
    return scraper.verify_token()


@router.post("/settings/verify-letpub")
async def verify_letpub_cookie(phpsessid: str = ""):
    """验证 LetPub PHPSESSID（使用前端传来的 cookie）"""
    if not phpsessid or len(phpsessid) < 5:
        return {"valid": False, "detail": "PHPSESSID 未提供或长度不足"}

    import httpx
    try:
        cookies = {"PHPSESSID": phpsessid.strip()}
        async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
            resp = await client.get(
                "https://www.letpub.com.cn/index.php?page=grant",
                headers={"User-Agent": "Mozilla/5.0 Chrome/124"},
                follow_redirects=True,
            )
            text = resp.text
            if "退出" in text or "个人中心" in text or "会员" in text:
                return {"valid": True, "detail": "Cookie 有效，已登录"}
            elif "登录" in text.lower() and "注册" in text.lower():
                return {"valid": False, "detail": "Cookie 无效，页面仍显示登录/注册入口"}
            from urllib.parse import quote
            search_url = (
                f"https://www.letpub.com.cn/index.php?page=grant&name={quote('张三')}"
                f"&company=&person={quote('张三')}"
            )
            resp2 = await client.get(search_url, follow_redirects=True)
            if "keyword-datalist" in resp2.text and '<td>' in resp2.text:
                return {"valid": True, "detail": "Cookie 有效，搜索结果正常返回"}
            return {"valid": True, "detail": "Cookie 可能有效（页面正常加载）"}
    except Exception as e:
        return {"valid": False, "detail": f"验证请求失败: {str(e)[:200]}"}
