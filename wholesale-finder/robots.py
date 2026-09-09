from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

_cache: dict[str, RobotFileParser] = {}

USER_AGENT = "WholesaleFinderBot/1.0 (+research tool, contact: operator)"


def is_allowed(url: str, user_agent: str = USER_AGENT) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    rp = _cache.get(origin)
    if rp is None:
        rp = RobotFileParser()
        rp.set_url(f"{origin}/robots.txt")
        try:
            rp.read()
        except Exception:
            # robots.txt unreachable: default to allowed, matching standard
            # crawler behavior, but callers still rate-limit and identify
            # themselves via USER_AGENT.
            rp = None
        _cache[origin] = rp
    if rp is None:
        return True
    return rp.can_fetch(user_agent, url)
