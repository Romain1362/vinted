import re
import time

import requests
from bs4 import BeautifulSoup

from robots import USER_AGENT, is_allowed

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+")
# Loose match for European phone formats; length is filtered afterwards
# since a strict regex misses too many valid national formats.
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(0?\d{1,4}\)|0?\d{1,4})(?:[\s.-]?\d{2,4}){2,5}")


def _plausible_phone(candidate: str) -> bool:
    digits = re.sub(r"\D", "", candidate)
    return 8 <= len(digits) <= 15


def fetch_page(url: str, timeout: float = 10.0) -> dict:
    result = {
        "url": url,
        "fetched_ok": False,
        "title": "",
        "meta_description": "",
        "emails": [],
        "phones": [],
        "error": "",
    }
    if not is_allowed(url):
        result["error"] = "disallowed_by_robots_txt"
        return result

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result

    soup = BeautifulSoup(resp.text, "lxml")
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        result["meta_description"] = meta["content"].strip()

    text = soup.get_text(" ", strip=True)
    result["emails"] = sorted(set(EMAIL_RE.findall(text)))[:5]
    result["phones"] = sorted({m for m in PHONE_RE.findall(text) if _plausible_phone(m)})[:5]
    result["fetched_ok"] = True
    return result


def fetch_pages(urls: list[str], pause_seconds: float = 2.0) -> dict[str, dict]:
    enriched = {}
    for url in urls:
        enriched[url] = fetch_page(url)
        time.sleep(pause_seconds)
    return enriched
