"""
Agent node implementations for the OmniForge LangGraph.

Each agent is a LangGraph node function that processes specific types of requests.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Research Agent
# ──────────────────────────────────────────────────────────────

RESEARCH_SYSTEM_PROMPT = """You are OmniForge's research agent. You have access to search results and source content.

Your job:
1. Analyze the search results provided
2. Synthesize information from multiple sources
3. Identify key findings, agreements, and conflicts
4. Provide a well-structured answer with citations [1], [2], etc.
5. Be honest about what the sources say and don't say

Citation rules:
- Use [N] to reference sources by their citation_id
- Never fabricate citations or URLs
- Prefer primary sources and official documentation
- Note when sources conflict

{skill_instructions}
"""


async def research_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """Research agent: searches multiple sources and synthesizes findings."""
    from omniforge.config.models import ModelRegistry
    from omniforge.graph.events import EventEmitter
    from omniforge.graph.supervisor import ROUTE_ACADEMIC
    from omniforge.research.ddgs_search import ddgs_search
    from omniforge.research.aggregator import aggregate_sources
    from omniforge.research.deduplicator import deduplicate_sources
    from omniforge.research.ranker import rank_sources
    from omniforge.research.verifier import verify_sources

    emitter = EventEmitter()
    events = []
    sources = []
    model_registry = ModelRegistry()

    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""
    route = state.get("route", "RESEARCH")
    is_academic = route == ROUTE_ACADEMIC

    # Step 1: Web search via DDGS, Brave, and SearXNG
    from omniforge.config.settings import get_settings
    settings = get_settings()
    
    events.append(emitter.emit_searching("Searching web via DDGS"))
    try:
        ddgs_results = await ddgs_search(last_msg, max_results=8)
        events.append(emitter.emit_searching(f"DDGS returned {len(ddgs_results)} results", status="complete"))
        sources.extend(ddgs_results)
    except Exception as e:
        events.append(emitter.emit_fallback(f"DDGS search failed: {e}"))
        
    if settings.BRAVE_SEARCH_API_KEY:
        try:
            from omniforge.research.brave import search_brave
            events.append(emitter.emit_searching("Searching via Brave"))
            brave_results = await search_brave(last_msg, max_results=5, api_key=settings.BRAVE_SEARCH_API_KEY)
            events.append(emitter.emit_searching(f"Brave returned {len(brave_results)} results", status="complete"))
            sources.extend(brave_results)
        except Exception as e:
            events.append(emitter.emit_fallback(f"Brave search failed: {e}"))

    if settings.SEARXNG_URL:
        try:
            from omniforge.research.searxng import search_searxng
            events.append(emitter.emit_searching("Searching via SearXNG"))
            sx_results = await search_searxng(last_msg, max_results=5, url=settings.SEARXNG_URL)
            events.append(emitter.emit_searching(f"SearXNG returned {len(sx_results)} results", status="complete"))
            sources.extend(sx_results)
        except Exception as e:
            events.append(emitter.emit_fallback(f"SearXNG search failed: {e}"))


    # Step 3: Academic search if needed
    if is_academic:
        try:
            from omniforge.research.arxiv import search_arxiv
            events.append(emitter.emit_searching("Searching arXiv"))
            arxiv_results = await search_arxiv(last_msg, max_results=5)
            events.append(emitter.emit_searching(
                f"arXiv returned {len(arxiv_results)} results", status="complete"
            ))
            sources.extend(arxiv_results)
        except Exception as e:
            events.append(emitter.emit_fallback(f"arXiv search failed: {e}"))

        try:
            from omniforge.research.semantic_scholar import search_semantic_scholar
            events.append(emitter.emit_searching("Searching Semantic Scholar"))
            ss_results = await search_semantic_scholar(last_msg, max_results=5, api_key=settings.SEMANTIC_SCHOLAR_API_KEY)
            events.append(emitter.emit_searching(
                f"Semantic Scholar returned {len(ss_results)} results", status="complete"
            ))
            sources.extend(ss_results)
        except Exception as e:
            events.append(emitter.emit_fallback(f"Semantic Scholar failed: {e}"))

    # Step 4: Aggregate, deduplicate, rank, verify
    events.append(emitter.emit_analyzing("Processing and ranking sources"))
    all_sources = aggregate_sources([sources])
    unique_sources = deduplicate_sources(all_sources)
    ranked_sources = rank_sources(unique_sources, last_msg)
    verified_sources = verify_sources(ranked_sources)
    events.append(emitter.emit_analyzing(
        f"Processed {len(verified_sources)} unique sources", status="complete"
    ))

    # Step 5: Fetch important pages via Jina
    top_sources = verified_sources[:5]
    for i, src in enumerate(top_sources):
        if src.get("url") and not src.get("content"):
            try:
                from omniforge.research.jina_reader import jina_read
                events.append(emitter.emit_fetching(f"Fetching: {src.get('domain', src['url'][:40])}"))
                page = await jina_read(src["url"], api_key=settings.JINA_API_KEY)
                if page.get("content"):
                    top_sources[i]["content"] = page["content"][:3000]
                    top_sources[i]["status"] = "fetched"
                events.append(emitter.emit_fetching(
                    f"Fetched: {src.get('domain', '')}", status="complete"
                ))
            except Exception:
                pass  # Skip failed fetches

    # Step 6: Synthesize with LLM
    events.append(emitter.emit_analyzing("Synthesizing research findings"))
    
    # Build source context for LLM
    source_context = "\n\n".join(
        f"[{s.get('citation_id', i+1)}] {s.get('title', 'Untitled')} ({s.get('url', '')})\n"
        f"Type: {s.get('source_type', 'web')} | Provider: {s.get('source_provider', 'unknown')}\n"
        f"{s.get('content', s.get('snippet', ''))[:1500]}"
        for i, s in enumerate(verified_sources[:10])
    )

    # Load skill instructions if available
    skill_instructions = ""
    active_skills = state.get("active_skills", [])
    if "web-research" in active_skills or "deep-research" in active_skills:
        from omniforge.skills.loader import get_skill_registry
        registry = get_skill_registry()
        for skill_name in ["web-research", "deep-research"]:
            if skill_name in active_skills:
                content = registry.load_skill(skill_name)
                if content:
                    skill_instructions += f"\n{content}\n"

    llm = model_registry.get_llm()
    system = RESEARCH_SYSTEM_PROMPT.format(skill_instructions=skill_instructions)
    
    synthesis_prompt = (
        f"Research query: {last_msg}\n\n"
        f"Sources found ({len(verified_sources)} total):\n\n{source_context}\n\n"
        f"Provide a comprehensive answer using these sources. "
        f"Cite sources using [N] notation."
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=synthesis_prompt),
        ])
        final_answer = response.content
    except Exception as e:
        final_answer = f"Research completed but synthesis failed: {e}\n\nRaw sources collected: {len(verified_sources)}"

    events.append(emitter.emit_complete("Research completed"))

    # Convert sources to dicts for state
    source_dicts = [s if isinstance(s, dict) else s for s in verified_sources]

    return {
        "messages": [AIMessage(content=final_answer)],
        "sources": source_dicts,
        "activity_events": events,
        "final_answer": final_answer,
        "error": "",
    }


# ──────────────────────────────────────────────────────────────
# General Agent
# ──────────────────────────────────────────────────────────────

GENERAL_SYSTEM_PROMPT = """You are OmniForge AI, a multimodal personal AI assistant.

You provide thoughtful, well-structured answers. You are honest about uncertainty.

{memory_context}
{skill_instructions}

Key behaviors:
- Be concise but thorough. NEVER exceed 600 words per response.
- If providing a list, roadmap, or resources, keep it highly summarized to fit within strict length limits.
- ALWAYS provide direct, clickable URLs for any resources, tools, or papers you mention.
- Use the memory context to inform your answers, but DO NOT awkwardly bring up past topics (like what the user was studying) when they just say "hi" or "hello". Keep greetings natural and generic.
- Use markdown formatting.
- Include code blocks when relevant.
- Acknowledge what you don't know.
"""


async def general_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """General conversation agent."""
    from omniforge.config.models import ModelRegistry
    from omniforge.graph.events import EventEmitter

    emitter = EventEmitter()
    events = [emitter.emit_analyzing("Processing request")]
    model_registry = ModelRegistry()

    messages = state.get("messages", [])
    
    # Build memory context
    memory_context = ""
    relevant_memories = state.get("relevant_memories", [])
    if relevant_memories:
        mem_lines = "\n".join(f"- {m}" for m in relevant_memories[:5])
        memory_context = f"\nRelevant memories about the user:\n{mem_lines}\n"

    system = GENERAL_SYSTEM_PROMPT.format(
        memory_context=memory_context,
        skill_instructions="",
    )

    try:
        llm = model_registry.get_llm()
        trimmed_msgs = _trim_messages(messages, max_recent=4)
        all_messages = [SystemMessage(content=system)] + trimmed_msgs
        response = await llm.ainvoke(all_messages)
        events.append(emitter.emit_complete("Response ready"))
        content = response.content
        if isinstance(content, list):
            final_answer = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
        else:
            final_answer = str(content)
            
        return {
            "messages": [AIMessage(content=final_answer)],
            "activity_events": events,
            "final_answer": final_answer,
            "error": "",
        }
    except Exception as e:
        events.append(emitter.emit_error(f"General agent error: {e}"))
        error_msg = f"I encountered an error processing your request: {e}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "activity_events": events,
            "final_answer": error_msg,
            "error": str(e),
        }


# ──────────────────────────────────────────────────────────────
# Coding Agent
# ──────────────────────────────────────────────────────────────

CODING_SYSTEM_PROMPT = """You are OmniForge's coding agent. You write clean, well-documented Python code.

Rules:
- Write production-quality code with type hints, docstrings, error handling
- Follow PEP 8 style
- Format ALL code using markdown code blocks: ```python ... ```
- DO NOT use input() or interactive prompts in your code. Use hardcoded example values instead.
- DO NOT include pip install commands inside code blocks.
- Keep it simple and self-contained.

{skill_instructions}
"""


async def coding_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """Coding agent: writes, executes, and debugs code."""
    from omniforge.config.models import ModelRegistry
    from omniforge.config.settings import get_settings
    from omniforge.graph.events import EventEmitter
    from omniforge.coding.executor import execute_python
    from omniforge.coding.workspace import Workspace
    from omniforge.coding.verifier import verify_python_syntax

    emitter = EventEmitter()
    events = []
    code_artifacts = []
    settings = get_settings()
    model_registry = ModelRegistry()
    workspace = Workspace(settings.WORKSPACE_PATH)

    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""

    events.append(emitter.emit_coding("Writing code"))

    # Load skill instructions
    skill_instructions = ""
    active_skills = state.get("active_skills", [])
    if "coding" in active_skills or "debugging" in active_skills:
        from omniforge.skills.loader import get_skill_registry
        registry = get_skill_registry()
        for skill_name in ["coding", "debugging"]:
            if skill_name in active_skills:
                content = registry.load_skill(skill_name)
                if content:
                    skill_instructions += f"\n{content}\n"

    system = CODING_SYSTEM_PROMPT.format(skill_instructions=skill_instructions)

    try:
        llm = model_registry.get_llm()
        trimmed_msgs = _trim_messages(messages, max_recent=4)
        response = await llm.ainvoke([
            SystemMessage(content=system),
            *trimmed_msgs,
        ])
        
        code_response = response.content
        events.append(emitter.emit_coding("Code generated", status="complete"))

        # Extract code blocks
        code_blocks = _extract_code_blocks(code_response)
        
        # Determine if user wants execution or just code
        user_wants_execution = any(
            kw in last_msg.lower()
            for kw in ["run", "execute", "test", "try it", "output", "result"]
        )

        for i, block in enumerate(code_blocks):
            if block.get("lang", "python") not in ("python", "py", ""):
                # Skip non-python blocks (bash, text, etc)
                continue

            # Skip blocks that contain input() - they'll hang
            if "input(" in block["code"]:
                code_artifacts.append({
                    "filename": f"code_block_{i+1}.py",
                    "code": block["code"],
                    "language": "python",
                    "output": "",
                    "error": "",
                    "tests_passed": None,
                })
                continue

            # Verify syntax first
            syntax_check = verify_python_syntax(block["code"])

            if not syntax_check["valid"]:
                code_artifacts.append({
                    "filename": f"code_block_{i+1}.py",
                    "code": block["code"],
                    "language": "python",
                    "output": "",
                    "error": syntax_check["error"],
                    "tests_passed": False,
                })
                continue

            # Only execute if user explicitly asked for it
            if not user_wants_execution:
                code_artifacts.append({
                    "filename": f"code_block_{i+1}.py",
                    "code": block["code"],
                    "language": "python",
                    "output": "",
                    "error": "",
                    "tests_passed": None,
                })
                continue

            # Execute the code
            events.append(emitter.emit_coding(f"Executing code block {i+1}"))
            result = await execute_python(
                block["code"],
                workspace_path=settings.WORKSPACE_PATH,
                timeout=30,
            )

            artifact = {
                "filename": f"code_block_{i+1}.py",
                "code": block["code"],
                "language": block.get("lang", "python"),
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "tests_passed": result.get("success"),
            }

            # Repair loop (max 2 attempts)
            repair_attempts = 0
            while not result.get("success") and repair_attempts < settings.MAX_CODE_REPAIR_ATTEMPTS:
                repair_attempts += 1
                events.append(emitter.emit_coding(f"Repairing code (attempt {repair_attempts})"))

                repair_prompt = (
                    f"The code failed with error:\n{result.get('error', '')}\n\n"
                    f"Original code:\n```python\n{artifact['code']}\n```\n\n"
                    f"Fix the error. DO NOT use input(). Return complete corrected code."
                )

                repair_response = await llm.ainvoke([
                    SystemMessage(content=system),
                    HumanMessage(content=repair_prompt),
                ])

                repaired_blocks = _extract_code_blocks(repair_response.content)
                if repaired_blocks:
                    repaired_code = repaired_blocks[0]["code"]
                    syn_check = verify_python_syntax(repaired_code)
                    if not syn_check["valid"]:
                        result = {"success": False, "error": f"Syntax error: {syn_check['error']}", "output": ""}
                    else:
                        result = await execute_python(
                            repaired_code,
                            workspace_path=settings.WORKSPACE_PATH,
                            timeout=30,
                        )
                    artifact["code"] = repaired_code
                    artifact["output"] = result.get("output", "")
                    artifact["error"] = result.get("error", "")
                    artifact["tests_passed"] = result.get("success")
                else:
                    break

            if result.get("success"):
                events.append(emitter.emit_coding("Code executed successfully", status="complete"))
            else:
                events.append(emitter.emit_error(
                    f"Code failed after {repair_attempts} repair attempt(s)"
                ))

            code_artifacts.append(artifact)

        events.append(emitter.emit_complete("Coding completed"))

        # Append execution results to the response so the supervisor knows what happened
        result_texts = []
        for a in code_artifacts:
            res_str = f"Execution Result for `{a['filename']}`:\n"
            if a['tests_passed']:
                res_str += f"✅ Success!\nOutput:\n```text\n{a['output'][:1000]}\n```"
            else:
                res_str += f"❌ Failed.\nError:\n```text\n{a['error'][:1000]}\n```"
            result_texts.append(res_str)
            
        if result_texts:
            code_response += "\n\n### Execution Results\n" + "\n\n".join(result_texts)
            # Create a new AIMessage with the appended results
            response = AIMessage(content=code_response)

        return {
            "messages": [response],
            "code_artifacts": code_artifacts,
            "activity_events": events,
            "final_answer": code_response,
            "error": "",
        }

    except Exception as e:
        events.append(emitter.emit_error(f"Coding agent error: {e}"))
        error_msg = f"I encountered an error while coding: {e}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "code_artifacts": code_artifacts,
            "activity_events": events,
            "final_answer": error_msg,
            "error": str(e),
        }


# ──────────────────────────────────────────────────────────────
# File Analysis Agent
# ──────────────────────────────────────────────────────────────

async def file_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """File analysis agent: processes uploaded documents."""
    from omniforge.config.models import ModelRegistry
    from omniforge.graph.events import EventEmitter
    from omniforge.files.multimodal import process_file
    from langchain_core.messages import AIMessage, SystemMessage

    emitter = EventEmitter()
    events = [emitter.emit_analyzing("Analyzing document(s)")]
    model_registry = ModelRegistry()

    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""
    uploaded_files = state.get("uploaded_files", [])

    file_contents = ""
    if uploaded_files:
        for f in uploaded_files:
            events.append(emitter.emit_fetching(f"Reading file: {f['name']}"))
            try:
                result = process_file(f["path"])
                if not result.get("error"):
                    data = result.get("data", {})
                    # Try to get text/content based on file type
                    content_str = data.get("text", data.get("content", str(data)))
                    file_contents += f"\n\n--- File: {f['name']} ---\n{str(content_str)[:20000]}"
                else:
                    file_contents += f"\n\n--- File: {f['name']} (Failed to read: {result.get('error')}) ---\n"
            except Exception as e:
                file_contents += f"\n\n--- File: {f['name']} (Error: {e}) ---\n"
        events.append(emitter.emit_fetching("Finished reading files", status="complete"))
    else:
        file_contents = "\n\nNo files were provided by the user."

    try:
        llm = model_registry.get_llm()
        system = (
            "You are OmniForge's document analysis agent. "
            "Help the user understand, summarize, and extract information from documents. "
            f"Here is the content of the uploaded files:\n{file_contents}"
        )
        trimmed_msgs = _trim_messages(messages, max_recent=4)
        response = await llm.ainvoke([
            SystemMessage(content=system),
            *trimmed_msgs,
        ])
        events.append(emitter.emit_complete("Document analysis complete"))
        return {
            "messages": [response],
            "activity_events": events,
            "final_answer": response.content,
            "error": "",
        }
    except Exception as e:
        events.append(emitter.emit_error(f"File analysis error: {e}"))
        return {
            "messages": [AIMessage(content=f"Document analysis error: {e}")],
            "activity_events": events,
            "error": str(e),
        }


# ──────────────────────────────────────────────────────────────
# Media Agent
# ──────────────────────────────────────────────────────────────

async def media_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """Media agent: generates images and videos."""
    from omniforge.config.settings import get_settings
    from omniforge.graph.events import EventEmitter
    from omniforge.graph.supervisor import ROUTE_VIDEO

    emitter = EventEmitter()
    events = []
    media_artifacts = []
    settings = get_settings()

    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""
    route = state.get("route", "IMAGE_GENERATION")

    if route == ROUTE_VIDEO:
        # Video generation
        events.append(emitter.emit_generating("Generating video (this may take a few minutes)"))
        try:
            from omniforge.media.video import generate_video
            result = await generate_video(
                prompt=last_msg,
                model=settings.VIDEO_MODEL,
                output_dir=f"{settings.ARTIFACTS_PATH}/videos",
            )
            if result.get("success"):
                media_artifacts.append({
                    "type": "video",
                    "path": result["path"],
                    "prompt": last_msg,
                    "model": settings.VIDEO_MODEL,
                })
                events.append(emitter.emit_generating("Video generated", status="complete"))
                answer = f"Video generated successfully and saved to `{result['path']}`."
            else:
                events.append(emitter.emit_error(f"Video generation failed: {result.get('error', '')}"))
                answer = f"Video generation failed: {result.get('error', 'Unknown error')}. The request was understood but the video model could not complete it."
        except Exception as e:
            events.append(emitter.emit_error(f"Video generation error: {e}"))
            answer = f"Video generation is not available: {e}"
    else:
        # Image generation
        events.append(emitter.emit_generating("Generating image"))
        try:
            from omniforge.media.image import generate_image
            result = await generate_image(
                prompt=last_msg,
                model=settings.IMAGE_MODEL,
                output_dir=f"{settings.ARTIFACTS_PATH}/images",
            )
            if result.get("success"):
                media_artifacts.append({
                    "type": "image",
                    "path": result["path"],
                    "prompt": last_msg,
                    "model": settings.IMAGE_MODEL,
                })
                events.append(emitter.emit_generating("Image generated", status="complete"))
                answer = f"Image generated successfully and saved to `{result['path']}`."
            else:
                events.append(emitter.emit_error(f"Image generation failed: {result.get('error', '')}"))
                answer = f"Image generation failed: {result.get('error', 'Unknown error')}"
        except Exception as e:
            events.append(emitter.emit_error(f"Image generation error: {e}"))
            answer = f"Image generation is not available: {e}"

    from langchain_core.messages import AIMessage
    events.append(emitter.emit_complete("Media task completed"))
    
    return {
        "messages": [AIMessage(content=answer)],
        "media_artifacts": media_artifacts,
        "activity_events": events,
        "final_answer": answer,
        "error": "",
    }


# ──────────────────────────────────────────────────────────────
# Synthesis Agent
# ──────────────────────────────────────────────────────────────

async def synthesis_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """
    Synthesis agent: creates the final response with citations and artifacts.
    In multi-pass workflows, this combines the outputs of all agent steps.
    """
    from omniforge.graph.events import EventEmitter
    from langchain_core.messages import AIMessage, HumanMessage

    emitter = EventEmitter()
    events = [emitter.emit_complete("Preparing final response")]

    messages = state.get("messages", [])
    
    # Extract all AIMessages since the last HumanMessage
    recent_ai_msgs = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get("type") == "human"):
            break
        if isinstance(msg, AIMessage) or (isinstance(msg, dict) and msg.get("type") == "ai"):
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if content:
                recent_ai_msgs.append(content)
                
    # Reverse to chronological order
    recent_ai_msgs.reverse()
    
    if state.get("error"):
        final_answer = f"⚠️ An error occurred during processing:\n```\n{state['error']}\n```"
    elif recent_ai_msgs:
        # If there are multiple steps, visually separate them
        if len(recent_ai_msgs) > 1:
            final_answer = "\n\n---\n\n".join(recent_ai_msgs)
        else:
            final_answer = recent_ai_msgs[0]
    else:
        final_answer = state.get("final_answer", "")
        if not final_answer:
            final_answer = "I apologize, but I encountered an internal routing issue and didn't generate a response. Please try asking your question again."

    return {
        "activity_events": events,
        "final_answer": final_answer,
    }


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _extract_code_blocks(text: str) -> list[dict]:
    """Extract code blocks from markdown text."""
    blocks = []
    lines = text.split("\n")
    in_block = False
    current_block = []
    current_lang = "python"

    for line in lines:
        if line.strip().startswith("```") and not in_block:
            in_block = True
            lang = line.strip().removeprefix("```").strip()
            current_lang = lang if lang else "python"
            current_block = []
        elif line.strip() == "```" and in_block:
            in_block = False
            if current_block:
                blocks.append({
                    "code": "\n".join(current_block),
                    "lang": current_lang,
                })
        elif in_block:
            current_block.append(line)

    return blocks


def _trim_messages(messages: list, max_recent: int = 4) -> list:
    """Trim message history."""
    if len(messages) <= max_recent:
        return messages
    return messages[-max_recent:]
