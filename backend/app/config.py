"""
全局配置管理 — API Key / Cookie / 平台开关 均通过此模块管理
数据持久化到 JSON 文件，无需数据库即可运行 MVP
"""

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "deepseek": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "tavily": {
        "api_key": "",
    },
    "cookies": {
        "gradchoice": "",
        "letpub": "",
    },
    "platforms": {
        "gradchoice": {"enabled": True, "name": "研选 GradChoice", "tier": 1},
        "tavily": {"enabled": True, "name": "Tavily 广域搜索", "tier": 1},
        "github_rms": {"enabled": True, "name": "GitHub 开源镜像", "tier": 4},
        "tieba": {"enabled": False, "name": "百度贴吧", "tier": 2},
        "muchong": {"enabled": True, "name": "小木虫 muchong.com", "tier": 5},
        "eeban": {"enabled": True, "name": "保研论坛 eeban.com", "tier": 5},
        "kaoyan": {"enabled": True, "name": "考研论坛 bbs.kaoyan.com", "tier": 5},
        "letpub": {"enabled": True, "name": "LetPub NSFC基金", "tier": 3},
        "daoshipingjia": {"enabled": True, "name": "导师评价网 dsPJ.net", "tier": 1},
        "pireview": {"enabled": True, "name": "PI Review", "tier": 1},
    },
}


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """加载配置文件，不存在则使用默认值"""
    _ensure_config_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            # 合并默认配置（防止新增字段丢失）
            config = {**DEFAULT_CONFIG}
            for key in saved:
                if isinstance(saved[key], dict) and isinstance(config.get(key), dict):
                    config[key] = {**config[key], **saved[key]}
                else:
                    config[key] = saved[key]
            return config
    return {**DEFAULT_CONFIG}


def save_config(config: dict):
    """保存配置到文件"""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_deepseek_api_key() -> Optional[str]:
    """获取 DeepSeek API Key"""
    return load_config().get("deepseek", {}).get("api_key", "")


def set_deepseek_api_key(key: str):
    """设置 DeepSeek API Key"""
    config = load_config()
    config["deepseek"]["api_key"] = key
    save_config(config)


def get_platform_cookie(platform: str) -> Optional[str]:
    """获取指定平台的 Cookie"""
    return load_config().get("cookies", {}).get(platform, "")


def set_platform_cookie(platform: str, cookie: str):
    """设置指定平台的 Cookie"""
    config = load_config()
    config["cookies"][platform] = cookie
    save_config(config)


def get_enabled_platforms() -> list[dict]:
    """获取所有已启用的平台列表"""
    config = load_config()
    return [
        {"key": k, **v} for k, v in config.get("platforms", {}).items() if v.get("enabled")
    ]


def get_tavily_api_key() -> Optional[str]:
    return load_config().get("tavily", {}).get("api_key", "")


def set_tavily_api_key(key: str):
    config = load_config()
    if "tavily" not in config:
        config["tavily"] = {}
    config["tavily"]["api_key"] = key
    save_config(config)


def update_platform_enabled(platform: str, enabled: bool):
    """更新平台的启用状态"""
    config = load_config()
    if platform in config.get("platforms", {}):
        config["platforms"][platform]["enabled"] = enabled
        save_config(config)
