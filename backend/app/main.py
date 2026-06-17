"""
FastAPI 应用入口
"""

# Windows: Playwright 需要 SelectorEventLoop（支持 create_subprocess_exec）
# 必须在任何 asyncio 操作之前设置，否则 ProactorEventLoop 会报 NotImplementedError
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import search, analysis, settings, history, stats

# ── 配置日志 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="\033[36m[%(name)s]\033[0m %(message)s",
    handlers=[logging.StreamHandler()],
)
# 确保各模块的日志也能输出
logging.getLogger("gradchoice").setLevel(logging.INFO)
logging.getLogger("github_import").setLevel(logging.INFO)
logging.getLogger("eeban").setLevel(logging.INFO)

# ── 启动事件：后台加载 GitHub 开源数据集 ─────────────────
def _startup_github_import():
    """在后台线程中执行 GitHub 数据集导入"""
    try:
        from .services.github_import import run_import
        print("\033[33m[github]\033[0m 正在后台加载 GitHub 开源数据集 (RateMySupervisor)...")
        result = run_import()
        if "error" in result:
            print(f"\033[33m[github]\033[0m ⚠️  {result['error']}")
        else:
            print(f"\033[32m[github]\033[0m ✅ GitHub 数据集就绪 | "
                  f"导师 {result.get('advisors', '?')} 人 | "
                  f"评价 {result.get('reviews', '?')} 条 | "
                  f"原始 {result.get('cleaned_count', '?')} 条")
    except ImportError:
        print("\033[33m[github]\033[0m ⚠️  github_import 模块不可用，跳过预加载")
    except Exception as e:
        print(f"\033[33m[github]\033[0m ⚠️  后台导入失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时后台预加载离线数据"""
    thread = threading.Thread(target=_startup_github_import, daemon=True)
    thread.start()
    yield


app = FastAPI(
    title="导师评价搜索平台",
    description="Advisor Review Search Platform - 多源聚合导师评价查询系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(analysis.router, prefix="/api", tags=["分析"])
app.include_router(settings.router, prefix="/api", tags=["设置"])
app.include_router(history.router, prefix="/api", tags=["历史"])
app.include_router(stats.router, prefix="/api", tags=["统计"])


@app.get("/")
def root():
    return {
        "service": "导师评价搜索平台 API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": [
            "/api/search - 搜索导师评价",
            "/api/analyze/sentiment - SnowNLP情感分析",
            "/api/analyze/deepseek - DeepSeek深度分析",
            "/api/settings - 获取/更新配置",
            "/api/history - 搜索历史（持久化）",
        ],
    }


@app.api_route("/api/comment/analyze", methods=["POST", "GET"])
def _silence_ext():
    """浏览器扩展产生的无关请求，静默忽略"""
    return {"status": "ok"}
