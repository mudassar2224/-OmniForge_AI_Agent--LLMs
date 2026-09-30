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
async def search_semantic_scholar(query: str, max_results: int = 5, api_key: str | None = None) -> list[dict]:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
        
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={max_results}&fields=title,abstract,url,year,citationCount,externalIds",
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        
        sources = []
        for item in data.get("data", []):
            url = item.get("url") or ""
            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "domain": _extract_domain(url) or "semanticscholar.org",
                "source_provider": "semantic_scholar",
                "source_type": "academic",
                "query": query,
                "snippet": item.get("abstract", "")[:200] if item.get("abstract") else "",
                "content": item.get("abstract", ""),
                "publication_date": str(item.get("year", "")),
                "status": "raw"
            })
        return sources

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def get_paper_details(paper_id: str, api_key: str | None = None) -> dict:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
        
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=title,abstract,url,year,citationCount,externalIds,authors",
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return data
