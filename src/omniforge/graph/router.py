"""
Router node for the OmniForge LangGraph.

Determines which agent node(s) to execute based on the supervisor's routing decision.
"""

import logging
from typing import Literal

from omniforge.graph.supervisor import (
    ROUTE_GENERAL, ROUTE_RESEARCH, ROUTE_ACADEMIC, ROUTE_CODING,
    ROUTE_DATA_ANALYSIS, ROUTE_DOCUMENT, ROUTE_IMAGE, ROUTE_VIDEO,
    ROUTE_MULTIMODAL, ROUTE_MULTI_STEP, ROUTE_FINISH
)

logger = logging.getLogger(__name__)


def route_to_agent(state: dict) -> str:
    """
    Conditional edge function for LangGraph.
    Routes to the appropriate agent node based on state['route'].
    """
    route = state.get("route", ROUTE_GENERAL)
    error = state.get("error", "")
    
    # If the supervisor encountered a fatal error (e.g. API down, config missing),
    # stop the loop immediately to prevent infinite error bouncing.
    if error:
        logger.error(f"Fatal error detected in state, halting loop: {error}")
        return "synthesis_node"
        
    if route == ROUTE_FINISH:
        return "synthesis_node"
        
    route_map = {
        ROUTE_GENERAL: "general_node",
        ROUTE_RESEARCH: "research_node",
        ROUTE_ACADEMIC: "research_node",
        ROUTE_CODING: "coding_node",
        ROUTE_DATA_ANALYSIS: "coding_node",
        ROUTE_DOCUMENT: "file_node",
        ROUTE_IMAGE: "media_node",
        ROUTE_VIDEO: "media_node",
        ROUTE_MULTIMODAL: "general_node",
        ROUTE_MULTI_STEP: "research_node",
    }
    
    target = route_map.get(route, "general_node")
    logger.info(f"Routing {route} -> {target}")
    return target


def should_synthesize(state: dict) -> str:
    """
    Conditional edge: decide whether to go to synthesis or end.
    """
    route = state.get("route", ROUTE_GENERAL)
    
    # These routes produce their own final answer and don't need synthesis
    if route == ROUTE_GENERAL:
        return "end"
    
    # All other routes benefit from synthesis
    return "synthesis_node"


def should_continue_multi_step(state: dict) -> str:
    """
    For multi-step workflows, determine the next sub-route.
    Currently simplified to go directly to synthesis.
    """
    return "synthesis_node"
