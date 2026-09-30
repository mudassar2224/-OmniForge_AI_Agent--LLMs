def rank_sources(sources: list[dict], query: str) -> list[dict]:
    """Scores and ranks sources based on relevance, source type, etc."""
    type_priority = {
        "academic": 5,
        "documentation": 4,
        "code": 3,
        "web": 2,
        "forum": 1,
        "news": 2,
        "llm": 1
    }
    
    scored_sources = []
    query_lower = query.lower()
    
    for source in sources:
        score = 0
        
        title = source.get("title", "").lower()
        if query_lower in title:
            score += 10
            
        snippet = source.get("snippet", "") or ""
        score += min(len(snippet) / 100.0, 5.0)
        
        stype = source.get("source_type", "web")
        score += type_priority.get(stype, 1) * 2
        
        domain = source.get("domain", "").lower()
        if domain.endswith(".edu") or domain.endswith(".gov"):
            score += 5
        elif domain in ("github.com", "arxiv.org", "semanticscholar.org"):
            score += 5
            
        s = source.copy()
        s["relevance_score"] = score
        scored_sources.append(s)
        
    return sorted(scored_sources, key=lambda x: x.get("relevance_score", 0), reverse=True)
