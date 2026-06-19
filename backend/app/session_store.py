"""In-memory session store.

Holds the live session dict shared across all routers. Replace with a
persistent store (Redis, DynamoDB, etc.) when moving beyond a single process.
"""

sessions: dict[str, dict] = {}
