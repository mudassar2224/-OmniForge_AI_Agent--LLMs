import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_github_repos(query: str, max_results: int = 5, token: str | None = None) -> list[dict]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "per_page": max_results},
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            
            sources = []
            for item in data.get("items", []):
                sources.append({
                    "title": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "domain": "github.com",
                    "source_provider": "github",
                    "source_type": "code",
                    "query": query,
                    "snippet": item.get("description", ""),
                    "content": item.get("description", ""),
                    "publication_date": item.get("updated_at", ""),
                    "status": "raw"
                })
            return sources
    except Exception as e:
        logger.error(f"GitHub repo search failed: {e}")
        return []

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
async def search_github_code(query: str, max_results: int = 5, token: str | None = None) -> list[dict]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.github.com/search/code",
                params={"q": query, "per_page": max_results},
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            
            sources = []
            for item in data.get("items", []):
                repo = item.get("repository", {}).get("full_name", "")
                sources.append({
                    "title": f"{item.get('name', '')} in {repo}",
                    "url": item.get("html_url", ""),
                    "domain": "github.com",
                    "source_provider": "github",
                    "source_type": "code",
                    "query": query,
                    "snippet": "",
                    "content": "",
                    "publication_date": "",
                    "status": "raw"
                })
            return sources
    except Exception as e:
        logger.error(f"GitHub code search failed: {e}")
        return []
