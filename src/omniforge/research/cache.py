import aiosqlite
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple SQLite-based cache for web requests and search results."""
    
    def __init__(self, db_path: str = "data/cache/requests.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME
                )
            ''')
            await db.commit()
            
    async def get(self, key: str, max_age_hours: int = 24) -> dict | None:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT data, timestamp FROM cache WHERE key = ?", 
                    (key,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        data_str, ts_str = row
                        ts = datetime.fromisoformat(ts_str)
                        if datetime.now() - ts < timedelta(hours=max_age_hours):
                            return json.loads(data_str)
                        else:
                            # Expired
                            await db.execute("DELETE FROM cache WHERE key = ?", (key,))
                            await db.commit()
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
        
    async def set(self, key: str, data: dict):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO cache (key, data, timestamp) VALUES (?, ?, ?)",
                    (key, json.dumps(data), datetime.now().isoformat())
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

_cache = None

async def get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager()
        await _cache.initialize()
    return _cache
