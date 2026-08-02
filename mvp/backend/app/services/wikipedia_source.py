import httpx

from app.services.http_utils import get_with_retry

_REST_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_ACTION_API = "https://en.wikipedia.org/w/api.php"


class PersonNotFound(Exception):
    pass


async def fetch_summary(name: str) -> dict:
    """REST summary: canonical title, short extract, page url, description."""
    url = _REST_SUMMARY.format(title=name.strip().replace(" ", "_"))
    try:
        resp = await get_with_retry(url)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise PersonNotFound(name) from exc
        raise
    return resp.json()


async def fetch_full_extract(title: str, max_chars: int = 8000) -> str:
    """Full plain-text extract via the action API — longer than the REST summary."""
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "titles": title,
        "format": "json",
        "redirects": "1",
    }
    resp = await get_with_retry(_ACTION_API, params=params)
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        return page.get("extract", "")[:max_chars]
    return ""
