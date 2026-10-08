import asyncio
import uuid
from typing import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from app.domain.models import Session


class SessionStore:
    """In-memory session store with per-session asyncio.Lock for serialized concurrency."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def get_lock(self, session_id: str) -> asyncio.Lock:
        """Retrieves or creates a dedicated asyncio.Lock for the session ID."""
        async with self._registry_lock:
            if session_id not in self._locks:
                self._locks[session_id] = asyncio.Lock()
            return self._locks[session_id]

    @asynccontextmanager
    async def lock(self, session_id: str) -> AsyncIterator[None]:
        """Async context manager to lock operations for a specific session."""
        session_lock = await self.get_lock(session_id)
        async with session_lock:
            yield

    async def create(self, session_id: str | None = None) -> Session:
        """Creates and stores a new Session."""
        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = Session(id=sid, created_at=now, updated_at=now)
        self._sessions[sid] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        """Retrieves a session by ID."""
        return self._sessions.get(session_id)

    async def save(self, session: Session) -> Session:
        """Updates and persists the session."""
        session.updated_at = datetime.now(timezone.utc)
        self._sessions[session.id] = session
        return session

    async def delete(self, session_id: str) -> bool:
        """Deletes a session and cleans up its lock."""
        async with self._registry_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._locks.pop(session_id, None)
                return True
            return False

    async def list_all(self) -> list[Session]:
        """Returns all active sessions."""
        return list(self._sessions.values())


# Global singleton store instance for the application lifecycle
session_store = SessionStore()
