---
name: web-research
description: Search the web using multiple providers with fallback
---

# Web Research Skill

When this skill is activated, perform fast, comprehensive, and resilient web queries across multiple backends:

1. **Targeted Query Formulation**: Convert broad questions into precise, keyword-focused search strings. Omit conversational filler words.
2. **Multi-Provider Fallback**: Query the primary search provider first (DuckDuckGo, Jina Search, or Gemini Search). On rate limit or timeout, immediately fail over to secondary providers.
3. **Domain Diversity**: Aggregate content across multiple distinct authoritative domains rather than relying on a single perspective or blog post.
4. **Clean Content Extraction**: Retrieve targeted web URLs using clean readers (such as Jina Reader or trafilatura) to strip navigational boilerplate and capture readable text.
5. **Freshness & Recency Filtering**: When queries demand up-to-date information, filter by publication date, news endpoints, and recent timestamps.
6. **Provenance Tracking**: Always retain source URLs, page titles, snippets, and retrieval timestamps for citations and downstream synthesis.
