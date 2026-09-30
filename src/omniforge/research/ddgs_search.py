import asyncio
from ddgs import DDGS
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
async def ddgs_search(query: str, max_results: int = 10, backend: str = 'auto') -> list[dict]:
    def _search():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results, backend=backend))
            
    results = await asyncio.to_thread(_search)
    sources = []
    for r in results:
        sources.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "domain": _extract_domain(r.get("href", "")),
            "source_provider": "ddgs",
            "source_type": "web",
            "query": query,
            "snippet": r.get("body", ""),
            "content": "",
            "publication_date": "",
            "status": "raw"
        })
    return sources

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def ddgs_news_search(query: str, max_results: int = 5) -> list[dict]:
    def _search():
        with DDGS() as ddgs:
            return list(ddgs.news(query, max_results=max_results))
            
    results = await asyncio.to_thread(_search)
    sources = []
    for r in results:
        sources.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": _extract_domain(r.get("url", "")),
            "source_provider": "ddgs",
            "source_type": "news",
            "query": query,
            "snippet": r.get("body", ""),
            "content": "",
            "publication_date": r.get("date", ""),
            "status": "raw"
        })
    return sources
