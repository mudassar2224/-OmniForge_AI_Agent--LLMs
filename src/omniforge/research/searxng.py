import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
import urllib.parse

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_searxng(query: str, max_results: int = 5, url: str | None = None) -> list[dict]:
    if not url:
        return []
        
    endpoint = f"{url.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "json"
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        sources = []
        for r in results:
            domain = ""
            try:
                domain = urllib.parse.urlparse(r.get("url", "")).netloc
            except Exception:
                pass
                
            sources.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "domain": domain,
                "source_provider": "searxng",
                "source_type": "web",
                "query": query,
                "snippet": r.get("content", ""),
                "content": "",
                "publication_date": r.get("publishedDate", ""),
                "status": "raw"
            })
        return sources[:max_results]
