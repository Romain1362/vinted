import os
import time

import requests

ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchError(RuntimeError):
    pass


def _credentials() -> tuple[str, str]:
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise GoogleSearchError(
            "GOOGLE_API_KEY et GOOGLE_CSE_ID doivent être définis dans "
            "l'environnement ou un fichier .env (voir .env.example)."
        )
    return api_key, cse_id


def search(query: str, num: int = 10, start: int = 1, country_restrict: str | None = None,
           language_restrict: str | None = None) -> list[dict]:
    api_key, cse_id = _credentials()
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": max(1, min(num, 10)),
        "start": start,
    }
    if country_restrict:
        params["cr"] = country_restrict
    if language_restrict:
        params["lr"] = language_restrict

    resp = requests.get(ENDPOINT, params=params, timeout=15)
    if resp.status_code == 429:
        raise GoogleSearchError(
            "Quota Google Custom Search dépassé (429). Réessaie plus tard "
            "ou augmente ton quota dans Google Cloud Console."
        )
    if not resp.ok:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise GoogleSearchError(f"Erreur Google Custom Search ({resp.status_code}): {detail}")
    return resp.json().get("items", [])


def search_all(query: str, max_results: int = 10, pause_seconds: float = 1.0, **kwargs) -> list[dict]:
    results: list[dict] = []
    start = 1
    while len(results) < max_results:
        batch = search(query, num=min(10, max_results - len(results)), start=start, **kwargs)
        if not batch:
            break
        results.extend(batch)
        start += len(batch)
        if len(batch) < 10:
            break
        time.sleep(pause_seconds)
    return results
