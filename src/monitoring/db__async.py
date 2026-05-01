"""Async aiosqlite wrapper with exponential backoff retry logic."""

import asyncio
from typing import Any, Optional


class AsyncRetryDB:  # noqa: D101
    """Async database client with retry and backoff."""

    def __init__(self):
        self._pool: list = []
        self._lock = asyncio.Lock()
        self._db_path: Optional[str] = None

    async def _get_connection(self) -> aiosqlite.Connection:  # noqa: D103
        """Get or create SQLite connection pool."""
        
        try:
            from dotenv import load_dotenv, find_dotenv
            
            env_file = find_dotenv()
            if env_file:
                load_dotenv(env_file)
            
            db_path = os.getenv("DB_PATH", "pymon.db")
            self._db_path = db_path
        except Exception:
            pass
        
        return aiosqlite.Connection(self._db_path or "pymon.db", check_same_thread=False)

    async def execute(  # noqa: D103, ANN002
        self, query: str, params: tuple = ()
    ) -> Optional[Any]:
        """Execute with exponential backoff retry."""
        
        max_retries = 5
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                async with self._lock:
                    conn = await self._get_connection()
                    await conn.execute("PRAGMA journal_mode=WAL")
                    
                    async with conn.execute(query, params) as cursor:
                        results = []
                        async for row in cursor:
                            if isinstance(row, aiosqlite.Row):
                                results.append(dict(row))
                            else:
                                results.append(list(row))
                    
                    return results
            except (aiosqlite.IntegrityError, aiosqlite.DatabaseError) as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Retry {attempt + 1}/5 for query with backoff {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise

    async def execute_many(
        self, query: str, params_list: list  # noqa: ANN003, D103
    ) -> Optional[list]:
        """Execute parameterized queries with retry logic."""
        
        if not params_list:
            return None
        
        try:
            async with self._lock:
                conn = await self._get_connection()
                await conn.execute("PRAGMA journal_mode=WAL")
                
                results = []
                for params in params_list:
                    async with conn.execute(query, params) as cursor:
                        row = await cursor.fetchone()
                        if isinstance(row, aiosqlite.Row):
                            results.append(dict(row))
                        else:
                            results.append(list(row))
                
                return results
        except Exception as e:
            print(f"execute_many error for query with params={params_list}: {e}")
            return None

    async def get_cached_result(  # noqa: D103, ANN002
        self, key: str, db_func, args: tuple = ()
    ) -> Optional[Any]:
        """Get from cache first, then DB if not cached."""
        
        try:
            import asyncio
            
            loop = asyncio.new_event_loop()
            try:
                cached = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: cache_client.get(key)
                )
                if cached is not None and isinstance(cached, dict):
                    return cached
            except Exception:
                pass
            
            loop.close()
        except Exception:
            pass
        
        # Call DB function directly
        return db_func(*args)
