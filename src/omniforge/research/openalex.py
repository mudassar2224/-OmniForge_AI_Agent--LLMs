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
async def search_openalex(query: str, max_results: int = 5, email: str | None = None) -> list[dict]:
    params = {
        "search": query,
        "per_page": max_results
    }
    if email:
        params["mailto"] = email
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.openalex.org/works", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            sources = []
            for item in data.get("results", []):
                url = item.get("doi") or item.get("id") or ""
                
                # reconstruct abstract from inverted index
                abstract_inverted = item.get("abstract_inverted_index")
                abstract = ""
                if abstract_inverted:
                    words = []
                    max_idx = max([idx for indices in abstract_inverted.values() for idx in indices]) if abstract_inverted else -1
                    if max_idx >= 0:
                        words = [""] * (max_idx + 1)
                        for word, indices in abstract_inverted.items():
                            for idx in indices:
                                words[idx] = word
                    abstract = " ".join(words).strip()
                
                sources.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "domain": _extract_domain(url) or "openalex.org",
                    "source_provider": "openalex",
                    "source_type": "academic",
                    "query": query,
                    "snippet": abstract[:200] if abstract else "",
                    "content": abstract,
                    "publication_date": str(item.get("publication_year", "")),
                    "status": "raw"
                })
            return sources
    except Exception as e:
        logger.error(f"OpenAlex search failed: {e}")
        return []
