"""Long-term memory storage using SQLite for OmniForge AI.

Provides persistent memory storage across sessions categorized as semantic,
episodic, or procedural memory, supporting upsert, keyword search, and deletion.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Literal, Optional
import uuid

import aiosqlite
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

MemoryCategory = Literal["semantic", "episodic", "procedural"]
VALID_CATEGORIES: set[str] = {"semantic", "episodic", "procedural"}


class MemoryRecord(BaseModel):
    """Pydantic model representing an individual long-term memory record."""

    id: str = Field(..., description="Unique UUID identifier for the memory")
    category: str = Field(
        ..., description="Memory classification ('semantic', 'episodic', or 'procedural')"
    )
    key: str = Field(..., description="Semantic label or title for the memory")
    value: str = Field(..., description="Information content of the memory")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata key-value pairs"
    )
    created_at: str = Field(
        ..., description="ISO 8601 formatted UTC creation timestamp"
    )
    updated_at: str = Field(
        ..., description="ISO 8601 formatted UTC last update timestamp"
    )

    model_config = ConfigDict(from_attributes=True)


class MemoryStore:
    """Asynchronous SQLite-backed memory store for persistent long-term memories.

    Supports categorized storage (semantic, episodic, procedural) with upsert semantics,
    flexible keyword retrieval, and maintenance operations.
    """

    def __init__(self, db_path: str = "data/memory/long_term.db") -> None:
        """Initialize the MemoryStore with the specified database path.

        Args:
            db_path: Path to the SQLite database file. Defaults to
                'data/memory/long_term.db'.
        """
        self.db_path = db_path
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Create the memories table and indexes if they do not already exist."""
        async with self._lock:
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        metadata TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_cat_key ON memories (category, key);"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories (category);"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories (updated_at DESC);"
                )
                await db.commit()

            self._initialized = True
            logger.info("Initialized MemoryStore at %s", self.db_path)

    async def _ensure_initialized(self) -> None:
        """Ensure the database and table are initialized before any operation."""
        if not self._initialized:
            await self.initialize()

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a database row into a dictionary with deserialized metadata."""
        raw_meta = row["metadata"] if isinstance(row, aiosqlite.Row) else row[4]
        meta: dict[str, Any] = {}
        if raw_meta:
            try:
                meta = json.loads(raw_meta)
            except Exception as exc:
                logger.warning("Failed to deserialize memory metadata: %s", exc)
                meta = {"raw": raw_meta}

        if isinstance(row, aiosqlite.Row):
            return {
                "id": str(row["id"]),
                "category": str(row["category"]),
                "key": str(row["key"]),
                "value": str(row["value"]),
                "metadata": meta,
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }

        return {
            "id": str(row[0]),
            "category": str(row[1]),
            "key": str(row[2]),
            "value": str(row[3]),
            "metadata": meta,
            "created_at": str(row[5]),
            "updated_at": str(row[6]),
        }

    async def store(
        self,
        category: str,
        key: str,
        value: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Store a memory entry, upserting if (category, key) already exists.

        Args:
            category: Classification of the memory ('semantic', 'episodic', or 'procedural').
            key: Semantic key or identifier.
            value: The content/information to remember.
            metadata: Optional dictionary of additional context metadata.

        Returns:
            The memory ID (existing ID if updated, or new UUID if inserted).
        """
        await self._ensure_initialized()

        now_iso = datetime.now(timezone.utc).isoformat()
        meta_dict = metadata if isinstance(metadata, dict) else {}
        meta_json = json.dumps(meta_dict)

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id FROM memories WHERE category = ? AND key = ?",
                    (category, key),
                ) as cursor:
                    existing = await cursor.fetchone()

                if existing:
                    memory_id = str(existing["id"])
                    await db.execute(
                        """
                        UPDATE memories
                        SET value = ?, metadata = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (value, meta_json, now_iso, memory_id),
                    )
                    logger.debug("Upserted existing memory [%s] %s (%s)", category, key, memory_id)
                else:
                    memory_id = str(uuid.uuid4())
                    await db.execute(
                        """
                        INSERT INTO memories (id, category, key, value, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (memory_id, category, key, value, meta_json, now_iso, now_iso),
                    )
                    logger.debug("Stored new memory [%s] %s (%s)", category, key, memory_id)

                await db.commit()
                return memory_id

    async def retrieve(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories by category and/or keyword in key/value.

        Args:
            category: Optional category filter ('semantic', 'episodic', 'procedural').
            query: Optional search keyword to match within key or value.
            limit: Maximum number of memories to return. Defaults to 10.

        Returns:
            List of memory dictionaries ordered by updated_at descending.
        """
        await self._ensure_initialized()

        conditions: list[str] = []
        params: list[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)

        if query and query.strip():
            conditions.append("(key LIKE ? OR value LIKE ?)")
            wildcard = f"%{query.strip()}%"
            params.extend([wildcard, wildcard])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT id, category, key, value, metadata, created_at, updated_at
            FROM memories
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            memory_id: Identifier of the memory record.

        Returns:
            True if a record was deleted, False otherwise.
        """
        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                await db.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug("Deleted memory record id: %s", memory_id)
                return deleted

    async def clear_category(self, category: str) -> int:
        """Clear all memories within a specific category.

        Args:
            category: Category to clear.

        Returns:
            Count of deleted records.
        """
        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM memories WHERE category = ?", (category,))
                await db.commit()
                count = cursor.rowcount
                logger.info("Cleared %d memories from category '%s'", count, category)
                return count

    async def clear_all(self) -> int:
        """Clear all stored memories across all categories.

        Returns:
            Count of deleted records.
        """
        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM memories")
                await db.commit()
                count = cursor.rowcount
                logger.info("Cleared all %d memories from store", count)
                return count

    async def list_all(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """List all memories, optionally filtered by category.

        Args:
            category: Optional category filter. If None, lists all memories.

        Returns:
            List of memory dictionaries ordered by updated_at descending.
        """
        await self._ensure_initialized()

        if category:
            sql = """
                SELECT id, category, key, value, metadata, created_at, updated_at
                FROM memories
                WHERE category = ?
                ORDER BY updated_at DESC
            """
            params: tuple[Any, ...] = (category,)
        else:
            sql = """
                SELECT id, category, key, value, metadata, created_at, updated_at
                FROM memories
                ORDER BY updated_at DESC
            """
            params = ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]
