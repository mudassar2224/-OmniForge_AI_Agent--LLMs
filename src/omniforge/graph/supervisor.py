"""
Supervisor node for the OmniForge LangGraph.

The supervisor analyzes user requests, creates bounded plans,
selects relevant skills, and routes to appropriate agent nodes.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

# Route constants
ROUTE_GENERAL = "GENERAL"
ROUTE_RESEARCH = "RESEARCH"
ROUTE_ACADEMIC = "ACADEMIC_RESEARCH"
ROUTE_CODING = "CODING"
ROUTE_DATA_ANALYSIS = "DATA_ANALYSIS"
ROUTE_DOCUMENT = "DOCUMENT_ANALYSIS"
ROUTE_IMAGE = "IMAGE_GENERATION"
ROUTE_VIDEO = "VIDEO_GENERATION"
ROUTE_MULTIMODAL = "MULTIMODAL"
ROUTE_MULTI_STEP = "MULTI_STEP"
ROUTE_FINISH = "FINISH"

ALL_ROUTES = [
    ROUTE_GENERAL, ROUTE_RESEARCH, ROUTE_ACADEMIC, ROUTE_CODING,
    ROUTE_DATA_ANALYSIS, ROUTE_DOCUMENT, ROUTE_IMAGE, ROUTE_VIDEO,
    ROUTE_MULTIMODAL, ROUTE_MULTI_STEP, ROUTE_FINISH
]

SUPERVISOR_SYSTEM_PROMPT = """You are OmniForge AI's master orchestrator. Analyze the conversation and decide ONE action.

You MUST respond with valid JSON only. No other text.

Routing rules (FOLLOW STRICTLY):
- GENERAL: Greetings, casual conversation, explanations, advice, learning roadmaps, opinions. Route here if NO verified web links or current news are needed. THIS IS THE DEFAULT.
- RESEARCH: User asks to search the web, find latest news, OR asks for specific resources, URLs, links, or YouTube videos. (The GENERAL agent cannot browse the web and will hallucinate dead links, so you MUST route to RESEARCH if the user wants working links).
- ACADEMIC_RESEARCH: User explicitly asks about research papers, arXiv, scientific literature.
- CODING: User explicitly asks you to WRITE, CREATE, BUILD, or DEBUG code/scripts/programs. Just mentioning "code" in conversation is NOT enough.
- DATA_ANALYSIS: User explicitly asks to analyze a CSV, dataset, or spreadsheet.
- DOCUMENT_ANALYSIS: User uploaded a file (PDF, DOCX) and asks about it.
- IMAGE_GENERATION: User explicitly asks to generate/create an image or picture.
- VIDEO_GENERATION: User explicitly asks to generate/create a video.
- FINISH: Use this ONLY to end the loop AFTER a worker agent (like GENERAL or RESEARCH) has successfully generated the answer. NEVER route to FINISH on the very first step of a user's request.

IMPORTANT RULES:
1. When in doubt, use GENERAL. Most questions are GENERAL.
2. FINISH DOES NOT GENERATE AN ANSWER. If you want the system to answer the user's prompt (like giving a roadmap), YOU MUST ROUTE TO GENERAL (or RESEARCH if links are needed).
3. Simple questions like "hi", "hello", "thanks", "what is X", "explain Y" MUST be routed to GENERAL.
4. Only route to CODING if the user literally says "write code", "create a script", "implement", "build a program", etc.

{skill_context}

{memory_context}

Loop counter: This is supervisor call #{loop_count}. If loop_count >= 3, you MUST route to FINISH.

Respond with this exact JSON:
{{
    "route": "ROUTE_NAME",
    "plan": "Brief plan",
    "needs_approval": false,
    "reasoning": "Why this route"
}}
"""


async def supervisor_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """
    Supervisor node: analyzes the request and determines routing.
    
    Returns updated state with route, plan, active_skills, and activity events.
    """
    from omniforge.config.settings import get_settings
    from omniforge.config.models import ModelRegistry
    from omniforge.skills.loader import get_skill_registry, select_skills_for_task
    from omniforge.graph.events import EventEmitter

    settings = get_settings()
    model_registry = ModelRegistry()
    emitter = EventEmitter()
    events = []
    loop_count = state.get("_loop_count", 0) + 1
    
    # If a worker node previously encountered a fatal error, pass it through so the router can halt
    if state.get("error"):
        events.append(emitter.emit_error("Supervisor halting due to upstream error"))
        return {
            "route": ROUTE_GENERAL,
            "activity_events": events,
            "error": state.get("error")
        }

    # Emit planning event
    events.append(emitter.emit_planning("Analyzing request and creating plan"))

    messages = state.get("messages", [])
    if not messages:
        return {
            "route": ROUTE_GENERAL,
            "plan": "No messages to process.",
            "activity_events": events,
            "active_skills": [],
            "needs_approval": False,
            "error": "",
        }

    # Get the last user message
    last_message = messages[-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    # Select relevant skills
    registry = get_skill_registry()
    selected_skills = select_skills_for_task(user_text, registry)
    skill_summaries = registry.get_skill_summaries()
    skill_context = f"Available skills:\n{skill_summaries}" if skill_summaries else ""

    # Format memory context
    relevant_memories = state.get("relevant_memories", [])
    memory_context = ""
    if relevant_memories:
        mem_lines = "\n".join(f"- {m}" for m in relevant_memories[:5])
        memory_context = f"Relevant user memories:\n{mem_lines}"

    # Build supervisor prompt
    system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
        skill_context=skill_context,
        memory_context=memory_context,
        loop_count=loop_count,
    )

    try:
        from omniforge.agents import _trim_messages
        llm = model_registry.get_llm()
        
        # Pass trimmed conversation history so supervisor knows what step we're on
        trimmed_msgs = _trim_messages(messages, max_recent=6)
        all_messages = [SystemMessage(content=system_prompt)] + trimmed_msgs
        
        if loop_count == 1:
            all_messages.append(HumanMessage(content="This is step 1. You MUST route to a worker agent like GENERAL, RESEARCH, or CODING to handle the user's new request. DO NOT route to FINISH."))
        else:
            all_messages.append(HumanMessage(content="Analyze the conversation history. If the last AI response successfully answered the user, YOU MUST ROUTE TO FINISH. Never route to GENERAL twice in a row."))
        
        response = await llm.ainvoke(all_messages)
        
        # Parse JSON response
        content = response.content
        if isinstance(content, list):
            response_text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
        else:
            response_text = str(content).strip()
            
        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if len(lines) > 2:
                response_text = "\n".join(lines[1:-1])
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()
        
        routing = json.loads(response_text)
        
        route = routing.get("route", ROUTE_GENERAL)
        if route not in ALL_ROUTES:
            route = ROUTE_GENERAL
            
        if loop_count == 1 and route == ROUTE_FINISH:
            route = ROUTE_GENERAL
            
        # Hardcode FINISH if the AI loops back to GENERAL. GENERAL is a one-shot response.
        if loop_count > 1 and route == ROUTE_GENERAL:
            route = ROUTE_FINISH
            
        plan = routing.get("plan", "Process the request.")
        needs_approval = routing.get("needs_approval", False)
        sub_routes = routing.get("sub_routes", [])

        events.append(emitter.emit_planning(
            f"Route: {route} | Plan: {plan}", status="complete"
        ))

        return {
            "route": route,
            "plan": plan,
            "_loop_count": loop_count,
            "active_skills": selected_skills,
            "needs_approval": needs_approval,
            "activity_events": events,
            "error": "",
        }

    except json.JSONDecodeError:
        # Fallback: simple keyword routing
        logger.warning("Supervisor JSON parse failed, using keyword routing")
        route, plan = _keyword_route(user_text)
        events.append(emitter.emit_planning(
            f"Route: {route} (keyword fallback)", status="complete"
        ))
        return {
            "route": route,
            "plan": plan,
            "_loop_count": loop_count,
            "active_skills": selected_skills,
            "needs_approval": False,
            "activity_events": events,
            "error": "",
        }
    except Exception as e:
        logger.error(f"Supervisor error: {e}")
        events.append(emitter.emit_error(f"Supervisor error: {e}"))
        return {
            "route": ROUTE_GENERAL,
            "plan": "Fallback to general conversation due to routing error.",
            "_loop_count": loop_count,
            "active_skills": [],
            "needs_approval": False,
            "activity_events": events,
            "error": str(e),
        }


def _keyword_route(text: str) -> tuple[str, str]:
    """Simple keyword-based routing fallback."""
    text_lower = text.lower()
    
    research_kw = ["search", "find", "look up", "latest", "current", "news", "web"]
    academic_kw = ["paper", "arxiv", "research", "literature", "study", "journal"]
    coding_kw = ["code", "implement", "program", "python", "function", "class", "debug", "fix"]
    data_kw = ["csv", "data", "dataset", "analyze data", "statistics", "excel", "spreadsheet"]
    doc_kw = ["pdf", "document", "docx", "read file", "summarize file"]
    image_kw = ["image", "picture", "draw", "generate image", "create image", "illustration"]
    video_kw = ["video", "clip", "animation", "generate video"]
    
    for kw in video_kw:
        if kw in text_lower:
            return ROUTE_VIDEO, "Generate a video based on the request."
    for kw in image_kw:
        if kw in text_lower:
            return ROUTE_IMAGE, "Generate an image based on the request."
    for kw in academic_kw:
        if kw in text_lower:
            return ROUTE_ACADEMIC, "Search academic sources for the requested information."
    for kw in coding_kw:
        if kw in text_lower:
            return ROUTE_CODING, "Write or modify code as requested."
    for kw in data_kw:
        if kw in text_lower:
            return ROUTE_DATA_ANALYSIS, "Analyze the provided data."
    for kw in doc_kw:
        if kw in text_lower:
            return ROUTE_DOCUMENT, "Analyze the provided document."
    for kw in research_kw:
        if kw in text_lower:
            return ROUTE_RESEARCH, "Search the web for the requested information."
    
    return ROUTE_GENERAL, "Respond to the user's request directly."
