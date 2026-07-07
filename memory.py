import asyncio
import sqlite3
from typing import List, Dict

class AsyncMemoryManager:
    """Manages agent conversation history with SQLite persistence."""
    
    def __init__(self, session_id: str = "default_session", max_messages: int = 10, db_path: str = "conversations.db"):
        self.session_id = session_id
        self.max_messages = max_messages
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create the table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT
                )
            """)
            conn.commit()

    async def add_message(self, role: str, content: str):
        """Asynchronously add a message to SQLite and trigger compaction if needed."""
        await asyncio.sleep(0.01) 
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (self.session_id, role, content)
            )
            conn.commit()
            
        await self._compact_if_needed()

    async def get_messages(self) -> List[Dict[str, str]]:
        """Retrieve the current conversation history from SQLite."""
        await asyncio.sleep(0.01)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
                (self.session_id,)
            )
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]

    async def _compact_if_needed(self):
        """Sliding window compaction in SQLite to prevent token overflow."""
        await asyncio.sleep(0.01)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (self.session_id,))
            count = cursor.fetchone()[0]
            
            if count > self.max_messages:
                print(f"[Memory System] Context limit reached ({count} msgs for {self.session_id}). Compacting DB...")
                delete_count = count - self.max_messages
                
                cursor.execute("""
                    DELETE FROM messages 
                    WHERE id IN (
                        SELECT id FROM messages 
                        WHERE session_id = ? 
                        ORDER BY id ASC 
                        LIMIT ?
                    )
                """, (self.session_id, delete_count))
                conn.commit()
