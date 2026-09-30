"""MCP server exposing research tools."""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo search.

    Args:
        query: Search string.
        max_results: Maximum number of search results to return.

    Returns:
        JSON string containing list of search result items.
    """
    try:
        from omniforge.research.ddgs_search import ddgs_search

        results = await ddgs_search(query, max_results=max_results)
        return json.dumps(results[:max_results], indent=2)
    except Exception as e:
        logger.error("web_search failed: %s", e)
        return json.dumps([{"error": f"Search failed: {e}"}])


async def fetch_url(url: str) -> str:
    """Fetch and extract readable markdown/text content from a URL via Jina Reader.

    Args:
        url: Web URL to fetch.

    Returns:
        Extracted content truncated to 5,000 characters.
    """
    try:
        from omniforge.research.jina_reader import jina_read

        result = await jina_read(url)
        content = result.get("content", "")
        if not content:
            return "Failed to fetch URL or empty content."
        return content[:5000]
    except Exception as e:
        logger.error("fetch_url failed: %s", e)
        return f"Error fetching URL: {e}"


async def search_papers(query: str, max_results: int = 5) -> str:
    """Search academic research papers on arXiv.

    Args:
        query: Search query for scientific papers.
        max_results: Maximum number of papers to return.

    Returns:
        JSON string containing list of paper metadata records.
    """
    try:
        from omniforge.research.arxiv import search_arxiv

        results = await search_arxiv(query, max_results=max_results)
        return json.dumps(results[:max_results], indent=2)
    except Exception as e:
        logger.error("search_papers failed: %s", e)
        return json.dumps([{"error": f"arXiv search failed: {e}"}])


try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("OmniForge Research")
    mcp.tool()(web_search)
    mcp.tool()(fetch_url)
    mcp.tool()(search_papers)

    if __name__ == "__main__":
        mcp.run()
except ImportError:
    mcp = None  # MCP library not installed or unavailable in current environment
