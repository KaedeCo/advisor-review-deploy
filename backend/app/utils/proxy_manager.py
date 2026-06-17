"""
代理管理器 — 代理池轮换，为高反爬平台（知乎/小红书等）预留基础设施
"""

import random
import logging
from typing import Optional

logger = logging.getLogger("proxy_manager")


class ProxyManager:
    """
    代理管理器

    支持：
    - 轮询 (round-robin) 代理分配
    - 随机代理选择
    - 代理健康检查（预留接口）
    - 无代理时直连回退

    Usage:
        pm = ProxyManager(["http://127.0.0.1:7890", "http://127.0.0.1:7891"])
        proxy = pm.get_proxy()  # "http://127.0.0.1:7890"
        pm.mark_dead("http://127.0.0.1:7890")  # 标记为不可用
    """

    def __init__(self, proxies: Optional[list[str]] = None):
        """
        Args:
            proxies: 代理地址列表，格式如 ["http://host:port", "https://host:port"]
                     为 None 或空列表时，get_proxy() 返回 None（直连模式）
        """
        self._proxies: list[str] = proxies or []
        self._dead_proxies: set[str] = set()
        self._index: int = 0

    @property
    def proxy_count(self) -> int:
        """可用代理数量"""
        return len(self._alive_proxies)

    @property
    def _alive_proxies(self) -> list[str]:
        """当前活跃（未标记为 dead）的代理"""
        return [p for p in self._proxies if p not in self._dead_proxies]

    def add_proxy(self, proxy: str):
        """添加一个代理地址"""
        if proxy not in self._proxies:
            self._proxies.append(proxy)
            logger.info("代理已添加: %s", proxy)

    def remove_proxy(self, proxy: str):
        """移除一个代理地址"""
        if proxy in self._proxies:
            self._proxies.remove(proxy)
            self._dead_proxies.discard(proxy)
            logger.info("代理已移除: %s", proxy)

    def get_proxy(self, strategy: str = "round_robin") -> Optional[str]:
        """
        获取一个代理地址

        Args:
            strategy: 分配策略
                - "round_robin": 轮询（默认）
                - "random": 随机

        Returns:
            代理 URL 字符串，无可用代理时返回 None（直连）
        """
        alive = self._alive_proxies
        if not alive:
            return None

        if strategy == "random":
            return random.choice(alive)

        # round_robin
        proxy = alive[self._index % len(alive)]
        self._index = (self._index + 1) % len(alive)
        return proxy

    def mark_dead(self, proxy: str):
        """标记代理为不可用"""
        self._dead_proxies.add(proxy)
        logger.warning("代理已标记为不可用: %s (剩余可用: %d)", proxy, len(self._alive_proxies))

    def revive(self, proxy: str):
        """恢复代理为可用"""
        self._dead_proxies.discard(proxy)
        logger.info("代理已恢复可用: %s", proxy)

    def revive_all(self):
        """恢复所有代理为可用"""
        self._dead_proxies.clear()
        logger.info("所有代理已恢复可用")

    def get_proxies_dict(self) -> Optional[dict[str, str]]:
        """
        获取 requests 库兼容的代理字典格式

        Returns:
            {"http": "http://host:port", "https": "http://host:port"} 或 None
        """
        proxy = self.get_proxy()
        if proxy is None:
            return None
        return {"http": proxy, "https": proxy}


# ── 全局单例 ──────────────────────────────────────────────────

_global_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """获取全局代理管理器单例"""
    global _global_proxy_manager
    if _global_proxy_manager is None:
        _global_proxy_manager = ProxyManager()
    return _global_proxy_manager


def set_global_proxies(proxies: list[str]):
    """设置全局代理列表"""
    global _global_proxy_manager
    _global_proxy_manager = ProxyManager(proxies)
