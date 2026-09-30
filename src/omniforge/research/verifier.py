def verify_sources(sources: list[dict]) -> list[dict]:
    """Verifies sources by checking URLs and titles, marking status."""
    verified = []
    
    for source in sources:
        s = source.copy()
        
        url = s.get("url", "").strip()
        title = s.get("title", "").strip()
        
        if not url or not title:
            s["status"] = "unverified"
        else:
            s["status"] = "verified"
            
        verified.append(s)
        
    return verified
