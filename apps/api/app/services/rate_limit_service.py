from app.core.config import Settings
from app.core.exceptions import RateLimitedError


class AuthRateLimiter:
    """Fixed-window counters in Redis, keyed by IP and by account.

    Degrades safely: if Redis is unreachable, login is allowed through
    rather than locking every user out — availability of core
    CRM/ticket flows must not depend on a side infrastructure
    component per the project's degraded-mode requirement.
    """

    def __init__(self, redis_client, settings: Settings) -> None:
        self.redis = redis_client
        self.settings = settings

    def check_and_increment(self, *, ip: str, account_key: str) -> None:
        if not self.settings.auth_rate_limit_enabled:
            return

        window = self.settings.auth_rate_limit_window_seconds
        try:
            ip_key = f"authrl:ip:{ip}"
            acct_key = f"authrl:acct:{account_key}"

            ip_count = self.redis.incr(ip_key)
            if ip_count == 1:
                self.redis.expire(ip_key, window)

            acct_count = self.redis.incr(acct_key)
            if acct_count == 1:
                self.redis.expire(acct_key, window)
        except Exception:
            # Redis unavailable — fail open, do not block authentication.
            return

        if ip_count > self.settings.auth_rate_limit_ip_attempts:
            raise RateLimitedError("Too many login attempts from this address")
        if acct_count > self.settings.auth_rate_limit_account_attempts:
            raise RateLimitedError("Too many login attempts for this account")
