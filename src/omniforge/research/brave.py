import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
import urllib.parse

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_brave(query: str, max_results: int = 5, api_key: str | None = None) -> list[dict]:
    if not api_key:
        return []
        
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {"q": query, "count": min(max_results, 20)}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("web", {}).get("results", [])
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
                "source_provider": "brave",
                "source_type": "web",
                "query": query,
                "snippet": r.get("description", ""),
                "content": "",
                "publication_date": r.get("page_age", ""),
                "status": "raw"
            })
        return sources[:max_results]
