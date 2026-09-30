# 🔥 OmniForge AI

### Research · Code · Remember · Create

A **multimodal personal AI agent** that can research the live web, reason over sources, write and execute code, understand files, remember users across conversations, use reusable skills and MCP tools, and generate images/videos through Gemini.

> Built as a portfolio project demonstrating LangChain · LangGraph · MCP · Gemini · LangSmith · Agent Skills

---

## Architecture

```
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │ Streamlit UI │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  LangGraph  │
                    │  Supervisor │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Research      Coding       General
           Agent         Agent        Agent
              │            │            │
         ┌────┼────┐       │            │
         ▼    ▼    ▼       ▼            ▼
      Gemini DDGS Jina  Sandbox      Gemini
      Search            Exec
              │
              ▼
         Synthesize
         + Citations
              │
              ▼
          RESPONSE
```

## Features

| Capability | Description |
|---|---|
| 💬 General AI | Conversation, explanations, reasoning |
| 🌐 Web Research | Multi-source web search (Gemini, DDGS, Brave, SearXNG) |
| 📚 Academic Research | arXiv, Semantic Scholar, OpenAlex, Crossref |
| 🔗 URL Analysis | Jina Reader for page extraction |
| 💻 Coding | Write, execute, debug, and repair Python code |
| 📁 File Analysis | PDF, DOCX, CSV, XLSX, images, JSON, text |
| 🖼️ Image Generation | Gemini image models |
| 🎬 Video Generation | Veo video generation (async) |
| 🧠 Memory | Short-term (checkpoints) + long-term (cross-conversation) |
| 🔀 Model Routing | Auto-selects Flash vs Pro based on task complexity |
| 📊 Observability | LangSmith tracing + live activity panel |
| 🧾 Citations | Inline source references [1][2][3] |
| 🔌 MCP | Extensible tool servers via Model Context Protocol |
| 📋 Agent Skills | Progressive skill loading for specialized tasks |
| 🛑 Bounded Execution | Deterministic limits on retries, searches, repairs |

## Tech Stack

- **Python 3.12** + **UV** for package management
- **Streamlit** frontend
- **LangChain** + **LangGraph** agent orchestration
- **Gemini API** (Google AI) for reasoning, coding, multimodal
- **LangMem** for long-term memory
- **LangSmith** for observability
- **MCP** (Model Context Protocol) for extensible tools
- **SQLite** for persistence
- **DDGS** for multi-engine web search
- **Jina** for webpage extraction

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager
- Gemini API key (from [Google AI Studio](https://aistudio.google.com/apikey))

### Installation

```bash
git clone https://github.com/yourusername/omniforge-ai.git
cd omniforge-ai

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
uv run streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Environment Variables

### Required

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) → Create API key |

### Optional (enhance functionality)

| Variable | Where to get it | What it enables |
|---|---|---|
| `LANGSMITH_API_KEY` | [LangSmith](https://smith.langchain.com/) → Settings → API keys | Execution tracing & observability |
| `GITHUB_TOKEN` | [GitHub](https://github.com/settings/tokens) → Personal access token | Authenticated GitHub search (higher limits) |
| `JINA_API_KEY` | [Jina AI](https://jina.ai/) → API keys | Higher rate limits for page extraction |
| `BRAVE_SEARCH_API_KEY` | [Brave Search API](https://brave.com/search/api/) | Additional search source |
| `SEARXNG_URL` | Self-hosted SearXNG instance URL | Private metasearch engine |
| `SEMANTIC_SCHOLAR_API_KEY` | [Semantic Scholar](https://www.semanticscholar.org/product/api) | Higher academic search limits |

> **Important:** The Gemini Developer API key is separate from a Google AI Pro subscription. Create your API key through Google AI Studio.

### Feature flags

```env
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=OmniForge-AI
MEMORY_ENABLED=true
MEDIA_ENABLED=true
```

---

## Project Structure

```
OmniForge/
├── app.py                          # Streamlit entry point
├── pyproject.toml                  # UV project config
├── .env.example                    # Environment template
│
├── src/omniforge/
│   ├── config/                     # Settings, model registry
│   ├── graph/                      # LangGraph state, supervisor, router
│   ├── agents/                     # Research, coding, media, file agents
│   ├── memory/                     # Checkpointing, long-term, summarizer
│   ├── research/                   # Web, academic, code search tools
│   ├── coding/                     # Workspace, executor, verifier
│   ├── media/                      # Image & video generation
│   ├── files/                      # PDF, DOCX, CSV, spreadsheet handlers
│   ├── mcp/                        # MCP client & servers
│   ├── skills/                     # Skill registry & loader
│   └── ui/                         # Streamlit components
│
├── skills/                         # Agent skill definitions (SKILL.md)
├── data/                           # SQLite databases, cache
├── workspace/                      # Coding agent workspace
├── artifacts/                      # Generated images, videos, reports
└── tests/                          # Test suite
```

## LangGraph Flow

```
START → memory_load → supervisor → [route] → agent → synthesis → memory_save → END
```

Routes: `GENERAL`, `RESEARCH`, `ACADEMIC_RESEARCH`, `CODING`, `DATA_ANALYSIS`, `DOCUMENT_ANALYSIS`, `IMAGE_GENERATION`, `VIDEO_GENERATION`, `MULTIMODAL`, `MULTI_STEP`

## MCP Servers

Run MCP servers independently:

```bash
# Research tools server
uv run python -m omniforge.mcp.servers.research_server

# Coding tools server
uv run python -m omniforge.mcp.servers.coding_server

# File tools server
uv run python -m omniforge.mcp.servers.files_server
```

## Skills

Skills use the [Agent Skills](https://agentskills.io/) format. Each skill has a `SKILL.md` with YAML frontmatter and procedural instructions:

- **planning** — Break complex requests into bounded steps
- **web-research** — Multi-source web search with fallback
- **deep-research** — Comprehensive multi-source research
- **source-verification** — Cross-check sources for accuracy
- **coding** — Write, test, and repair Python code
- **debugging** — Diagnose and fix code errors
- **data-analysis** — Analyze datasets with pandas
- **document-analysis** — Extract info from documents
- **report-generation** — Generate structured reports
- **media-generation** — Generate images and videos

## Memory System

- **Short-term:** LangGraph checkpointing (SQLite) for conversation persistence
- **Long-term:** Cross-conversation memory store for preferences, facts, decisions
- **Summarization:** Automatic conversation compression for long sessions
- **Controls:** View, add, delete, and clear memories through the UI

## Security

- API keys loaded from `.env` only — never hardcoded
- Workspace isolation for code execution
- Blocked dangerous operations (os.system, eval, etc.)
- External content treated as untrusted (prompt injection protection)
- No secrets in UI output or error messages

## Running Tests

```bash
uv run pytest tests/ -v
```

---

## Screenshots

*Coming soon*

---

## License

MIT

---

**Built by [Your Name]** as a portfolio project demonstrating modern AI agent architecture.
