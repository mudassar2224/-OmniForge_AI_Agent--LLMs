"""LangGraph SQLite checkpointing for thread and conversation memory.

This module provides an asynchronous SQLite checkpointer used by LangGraph
to persist conversation state across interactions and turns.
"""

from __future__ import annotations

import logging
import os
from contextlib import AbstractAsyncContextManager
from typing import Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

_checkpointer: Optional[AsyncSqliteSaver] = None
_saver_context: Optional[AbstractAsyncContextManager[AsyncSqliteSaver]] = None


async def get_checkpointer(
    db_path: str = "data/checkpoints/conversations.db",
) -> AsyncSqliteSaver:
    """Get or create the SQLite checkpointer for conversation persistence.

    Creates the required directory structure if needed, establishes or acquires
    an AsyncSqliteSaver instance, and runs database setup (table creation).

    Args:
        db_path: File system path to the SQLite database. Defaults to
            "data/checkpoints/conversations.db".

    Returns:
        An initialized AsyncSqliteSaver ready to pass to LangGraph compile().
    """
    global _checkpointer, _saver_context
    if _checkpointer is None:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        res = AsyncSqliteSaver.from_conn_string(db_path)
        # Handle both async context manager (standard in langgraph-checkpoint-sqlite)
        # and direct instance return for flexibility and backward/forward compatibility.
        if hasattr(res, "__aenter__"):
            _saver_context = res
            _checkpointer = await _saver_context.__aenter__()
        else:
            _checkpointer = res

        await _checkpointer.setup()
        logger.info("Initialized AsyncSqliteSaver checkpoint at %s", db_path)

    return _checkpointer


async def close_checkpointer() -> None:
    """Close the active checkpointer and release database resources."""
    global _checkpointer, _saver_context
    if _saver_context is not None:
        try:
            await _saver_context.__aexit__(None, None, None)
            logger.debug("AsyncSqliteSaver context manager exited.")
        except Exception as exc:
            logger.warning("Error exiting checkpointer context manager: %s", exc)
        finally:
            _saver_context = None

    _checkpointer = None
