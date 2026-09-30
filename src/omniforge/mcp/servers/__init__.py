"""MCP server implementations for OmniForge AI capabilities."""
from omniforge.mcp.servers.research_server import (
    mcp as research_mcp,
    web_search,
    fetch_url,
    search_papers,
)
from omniforge.mcp.servers.coding_server import (
    mcp as coding_mcp,
    list_workspace,
    read_file,
    write_file,
    run_python,
)
from omniforge.mcp.servers.files_server import (
    mcp as files_mcp,
    list_files,
    read_document,
    get_file_info,
)

__all__ = [
    "research_mcp",
    "web_search",
    "fetch_url",
    "search_papers",
    "coding_mcp",
    "list_workspace",
    "read_file",
    "write_file",
    "run_python",
    "files_mcp",
    "list_files",
    "read_document",
    "get_file_info",
]
