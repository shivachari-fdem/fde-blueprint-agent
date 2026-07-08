import asyncio
import os
import asyncpg
from typing import List, Dict

class AsyncMemoryManager:
    """Manages agent conversation history with PostgreSQL persistence."""
    
    def __init__(self, session_id: str = "default_session", max_messages: int = 10):
        self.session_id = session_id
        self.max_messages = max_messages
        
        # We now use environment variables to securely load database credentials
        # rather than hardcoding them into the script.
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_name = os.getenv("DB_NAME", "conversations")
        self.db_host = os.getenv("DB_HOST", "127.0.0.1") 
        self.pool = None

    async def _connect(self):
        """Establishes a connection pool to PostgreSQL if it doesn't exist."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                user=self.db_user,
                password=self.db_pass,
                database=self.db_name,
                host=self.db_host
            )
        return self.pool

    async def _init_db(self):
        """Initialize the PostgreSQL database and create the table."""
        pool = await self._connect()
        async with pool.acquire() as conn:
            # Note: PostgreSQL uses 'SERIAL' instead of 'AUTOINCREMENT'
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT
                )
            """)

    async def add_message(self, role: str, content: str):
        """Asynchronously add a message to PostgreSQL."""
        pool = await self._connect()
        async with pool.acquire() as conn:
            # Note: PostgreSQL uses $1, $2, $3 instead of ?, ?, ? for variables
            await conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
                self.session_id, role, content
            )
        await self._compact_if_needed()

    async def get_messages(self) -> List[Dict[str, str]]:
        """Retrieve the current conversation history from PostgreSQL."""
        pool = await self._connect()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, content FROM messages WHERE session_id = $1 ORDER BY id ASC",
                self.session_id
            )
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def _compact_if_needed(self):
        """Sliding window compaction to prevent token overflow."""
        pool = await self._connect()
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM messages WHERE session_id = $1", self.session_id)
            
            if count > self.max_messages:
                print(f"[Memory System] Context limit reached ({count} msgs). Compacting DB...")
                delete_count = count - self.max_messages
                
                await conn.execute("""
                    DELETE FROM messages 
                    WHERE id IN (
                        SELECT id FROM messages 
                        WHERE session_id = $1 
                        ORDER BY id ASC 
                        LIMIT $2
                    )
                """, self.session_id, delete_count)
