def aggregate_sources(source_lists: list[list[dict]]) -> list[dict]:
    """Flattens a list of source lists and assigns sequential citation IDs."""
    combined = []
    citation_id = 1
    for source_list in source_lists:
        for source in source_list:
            s = source.copy()
            s["citation_id"] = citation_id
            combined.append(s)
            citation_id += 1
    return combined
