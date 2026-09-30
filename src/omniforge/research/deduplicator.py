from urllib.parse import urlparse, urlunparse

def deduplicate_sources(sources: list[dict]) -> list[dict]:
    """Removes sources with duplicate URLs after normalization."""
    seen_urls = set()
    unique_sources = []
    
    for source in sources:
        raw_url = source.get("url", "")
        if not raw_url:
            unique_sources.append(source)
            continue
            
        try:
            parsed = urlparse(raw_url)
            netloc = parsed.netloc
            if netloc.startswith("www."):
                netloc = netloc[4:]
            path = parsed.path.rstrip("/")
            normalized = urlunparse((parsed.scheme, netloc, path, "", "", ""))
        except Exception:
            normalized = raw_url
            
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique_sources.append(source)
            
    return unique_sources
