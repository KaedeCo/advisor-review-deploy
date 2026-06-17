"""
请求限速器 — Token Bucket 算法，按域名独立限速，防止触发反爬机制
"""

import time
import threading
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """
    基于 Token Bucket 的域名级限速器

    Attributes:
        max_requests: 每个时间窗口内最大请求数
        per_seconds: 时间窗口大小（秒）
        burst: 突发允许量（token 桶容量倍数）
    """

    def __init__(self, max_requests: int = 20, per_seconds: int = 60, burst: float = 1.5):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.bucket_capacity = int(max_requests * burst)
        self._tokens: dict[str, float] = defaultdict(lambda: self.bucket_capacity)
        self._last_refill: dict[str, float] = defaultdict(time.time)
        self._lock = threading.Lock()
        self._refill_rate = max_requests / per_seconds

    def _refill(self, domain: str):
        """补充 token"""
        now = time.time()
        elapsed = now - self._last_refill[domain]
        new_tokens = elapsed * self._refill_rate
        self._tokens[domain] = min(self.bucket_capacity, self._tokens[domain] + new_tokens)
        self._last_refill[domain] = now

    def acquire(self, domain: str = "default", block: bool = True, timeout: float = 30.0) -> bool:
        """
        尝试获取一个请求许可

        Args:
            domain: 域名标识，不同域名独立限速
            block: 是否阻塞等待直到获取 token
            timeout: 最大等待时间（秒），仅 block=True 时生效

        Returns:
            True 获取成功，False 超时或 token 不足
        """
        start = time.time()
        while True:
            with self._lock:
                self._refill(domain)
                if self._tokens[domain] >= 1.0:
                    self._tokens[domain] -= 1.0
                    return True

            if not block:
                return False

            elapsed = time.time() - start
            if elapsed >= timeout:
                return False

            # 等到预计有一个 token 可用
            wait_time = 1.0 / self._refill_rate
            time.sleep(wait_time)

    def wait(self, domain: str = "default", timeout: float = 30.0):
        """阻塞等待直到获取许可（acquire 的别名）"""
        if not self.acquire(domain, block=True, timeout=timeout):
            raise TimeoutError(f"Rate limit timeout for domain '{domain}' after {timeout}s")

    def remaining(self, domain: str = "default") -> int:
        """查询当前剩余可用 token 数"""
        with self._lock:
            self._refill(domain)
            return int(self._tokens[domain])

    def reset(self, domain: str = "default"):
        """重置指定域名的限速状态"""
        with self._lock:
            self._tokens[domain] = self.bucket_capacity
            self._last_refill[domain] = time.time()


# ── 预设限速策略 ──────────────────────────────────────────────

# 专业平台：温和策略（这些平台需要友好对待）
PROFESSIONAL_PLATFORM_LIMITER = RateLimiter(max_requests=10, per_seconds=60, burst=1.2)

# 社交平台：中等策略（贴吧等反爬弱的可稍激进）
SOCIAL_PLATFORM_LIMITER = RateLimiter(max_requests=15, per_seconds=60, burst=1.5)

# DDGS 搜索引擎：低频策略（免费 API 需节制）
DDGS_LIMITER = RateLimiter(max_requests=5, per_seconds=60, burst=1.0)

# 通用默认
DEFAULT_LIMITER = RateLimiter(max_requests=20, per_seconds=60, burst=1.5)
