import asyncio
import arxiv
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    try:
        def _search():
            client = arxiv.Client()
            search = arxiv.Search(query=query, max_results=max_results)
            return list(client.results(search))
            
        results = await asyncio.to_thread(_search)
        sources = []
        for r in results:
            sources.append({
                "title": r.title,
                "url": r.entry_id,
                "domain": "arxiv.org",
                "source_provider": "arxiv",
                "source_type": "academic",
                "query": query,
                "snippet": r.summary[:200] if r.summary else "",
                "content": r.summary,
                "publication_date": r.published.isoformat() if r.published else "",
                "status": "raw"
            })
        return sources
    except Exception as e:
        logger.error(f"arxiv search failed: {e}")
        return []
