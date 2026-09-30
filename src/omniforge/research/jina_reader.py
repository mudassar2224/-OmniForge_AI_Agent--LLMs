import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except:
        return ""

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def jina_read(url: str, api_key: str | None = None) -> dict:
    from omniforge.research.cache import get_cache
    cache = await get_cache()
    cached = await cache.get(f"jina_read:{url}")
    if cached:
        logger.info(f"Cache hit for {url}")
        return cached

    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"https://r.jina.ai/{url}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        result = {
            "title": data.get("data", {}).get("title", ""),
            "url": url,
            "domain": _extract_domain(url),
            "source_provider": "jina",
            "source_type": "web",
            "query": "",
            "snippet": data.get("data", {}).get("description", ""),
            "content": data.get("data", {}).get("content", ""),
            "publication_date": "",
            "status": "raw"
        }
        await cache.set(f"jina_read:{url}", result)
        return result

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def jina_search(query: str, api_key: str | None = None, max_results: int = 5) -> list[dict]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"https://s.jina.ai/{query}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        sources = []
        for item in data.get("data", [])[:max_results]:
            url = item.get("url", "")
            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "domain": _extract_domain(url),
                "source_provider": "jina",
                "source_type": "web",
                "query": query,
                "snippet": item.get("description", ""),
                "content": item.get("content", ""),
                "publication_date": "",
                "status": "raw"
            })
        return sources
