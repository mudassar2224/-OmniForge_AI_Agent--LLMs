---
name: document-analysis
description: Extract and analyze information from PDF, DOCX, and other documents
---

# Document Analysis Skill

When this skill is activated, inspect, extract, and analyze unstructured and semi-structured documents:

1. **Format Detection & Loader Selection**: Identify file extensions (PDF, DOCX, TXT, Markdown, HTML) and select appropriate extraction libraries (`pypdf`, `python-docx`, `beautifulsoup4`).
2. **Structural Hierarchy Preservation**: Retain document structure including headers, subheadings, paragraphs, footnotes, and bulleted sections.
3. **Table & Schema Extraction**: Parse embedded tabular data into structured dictionary or DataFrame objects for downstream calculation.
4. **Semantic Chunking**: For long documents, segment contents into coherent thematic chunks with token count awareness for effective retrieval.
5. **Entity & Clause Extraction**: Extract crucial information such as contracts clauses, metrics, definitions, dates, and executive summaries.
6. **Cross-Document Comparative Synthesis**: Correlate concepts across multiple documents, highlighting commonalities, variances, and conflicting clauses.
