import asyncio

import httpx

USER_AGENT = "HumanContextAI-MVP/0.1 (educational research use)"


async def get_with_retry(
    url: str, params: dict | None = None, timeout: float = 15.0, max_retries: int = 2
) -> httpx.Response:
    """GET with one behavior Wikimedia's API explicitly asks clients to have:
    back off on 429 using the Retry-After header instead of hammering it."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries + 1):
            resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 429 or attempt == max_retries:
                resp.raise_for_status()
                return resp
            wait_seconds = min(int(resp.headers.get("retry-after", "5")), 30)
            await asyncio.sleep(wait_seconds)
    raise RuntimeError("unreachable")  # loop always returns or raises above
