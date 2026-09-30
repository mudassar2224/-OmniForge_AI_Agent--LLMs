"""Execution policy constants and guardrails for OmniForge AI graphs.

Defines operational limits and thresholds governing planning depth, search escalation,
code self-repair retries, web scraping limits, and source aggregation caps.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Maximum depth/iterations for multi-step planning and decomposition
MAX_PLANNING_DEPTH: int = 3

# Maximum number of search escalation attempts across search providers (e.g., DDGS -> Gemini -> Arxiv)
MAX_SEARCH_ESCALATION: int = 3

# Maximum number of self-correction attempts when generated code fails execution or tests
MAX_CODE_REPAIR_ATTEMPTS: int = 2

# Maximum times the exact same search query may be executed to prevent infinite search loops
MAX_IDENTICAL_SEARCH: int = 1

# Maximum retry count for transient tool execution failures before switching to a fallback
MAX_TOOL_RETRIES: int = 2

# Maximum number of source results to collect from a single search query
MAX_SOURCES_PER_SEARCH: int = 10

# Maximum number of web pages to scrape and fetch full contents for in a single workflow
MAX_FETCH_PAGES: int = 5

# Minimum number of verified sources required before synthesizing deep research answers
MIN_SOURCES_FOR_RESEARCH: int = 2

# Target/preferred number of quality sources for comprehensive research answers
PREFERRED_SOURCES: int = 5

# Hard upper bound on total sources stored in AgentState across all iterations
MAX_SOURCES_TOTAL: int = 15


class GraphPolicies(BaseModel):
    """Configurable execution policies for LangGraph workflows in OmniForge."""

    max_planning_depth: int = Field(default=MAX_PLANNING_DEPTH, ge=1)
    max_search_escalation: int = Field(default=MAX_SEARCH_ESCALATION, ge=1)
    max_code_repair_attempts: int = Field(default=MAX_CODE_REPAIR_ATTEMPTS, ge=0)
    max_identical_search: int = Field(default=MAX_IDENTICAL_SEARCH, ge=1)
    max_tool_retries: int = Field(default=MAX_TOOL_RETRIES, ge=0)
    max_sources_per_search: int = Field(default=MAX_SOURCES_PER_SEARCH, ge=1)
    max_fetch_pages: int = Field(default=MAX_FETCH_PAGES, ge=1)
    min_sources_for_research: int = Field(default=MIN_SOURCES_FOR_RESEARCH, ge=1)
    preferred_sources: int = Field(default=PREFERRED_SOURCES, ge=1)
    max_sources_total: int = Field(default=MAX_SOURCES_TOTAL, ge=1)
