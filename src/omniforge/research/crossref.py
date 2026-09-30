import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_crossref(query: str, max_results: int = 5) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.crossref.org/works",
                params={"query": query, "rows": max_results}
            )
            resp.raise_for_status()
            data = resp.json()
            
            sources = []
            for item in data.get("message", {}).get("items", []):
                url = item.get("URL", "")
                title = item.get("title", [""])[0] if item.get("title") else ""
                
                pub_date = ""
                issued = item.get("issued", {}).get("date-parts", [[]])
                if issued and issued[0]:
                    pub_date = str(issued[0][0])
                
                sources.append({
                    "title": title,
                    "url": url,
                    "domain": "crossref.org",
                    "source_provider": "crossref",
                    "source_type": "academic",
                    "query": query,
                    "snippet": title,
                    "content": item.get("abstract", ""),
                    "publication_date": pub_date,
                    "status": "raw"
                })
            return sources
    except Exception as e:
        logger.error(f"Crossref search failed: {e}")
        return []

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def resolve_doi(doi: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://api.crossref.org/works/{doi}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Crossref resolve DOI failed: {e}")
        return {}
