"""Long-term + vector memory backed by pgvector (Phase D).

A user's durable facts live in `user_memory`, each with its embedding. We fetch
them two ways:
  * by similarity (recall) — embed the query, order by cosine distance (<=>),
  * by exact filter (load_preferences) — pull the user's saved prefs/places to
    inject into the agent's context every run, so it uses them unprompted.
"""
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.agent import embeddings

VALID_KINDS = ("preference", "place", "fact")


async def remember(pool: AsyncConnectionPool, user_id: str, kind: str, content: str) -> None:
    """Embed and store a durable fact (idempotent on (user_id, content))."""
    kind = kind if kind in VALID_KINDS else "fact"
    vec = embeddings.to_pgvector(await embeddings.embed(content))
    sql = """
        INSERT INTO user_memory (user_id, kind, content, embedding)
        VALUES (%s, %s, %s, %s::vector)
        ON CONFLICT (user_id, content) DO NOTHING
    """
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(sql, (user_id, kind, content, vec))


async def recall(pool: AsyncConnectionPool, user_id: str, query: str, k: int = 5) -> list[dict]:
    """Top-k of the user's facts most similar (by meaning) to the query."""
    vec = embeddings.to_pgvector(await embeddings.embed(query))
    sql = """
        SELECT content, kind, embedding <=> %s::vector AS distance
        FROM user_memory
        WHERE user_id = %s
        ORDER BY distance
        LIMIT %s
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (vec, user_id, k))
        return await cur.fetchall()


async def load_preferences(pool: AsyncConnectionPool, user_id: str) -> list[dict]:
    """The user's saved preferences/places, for unprompted use in context."""
    sql = """
        SELECT kind, content FROM user_memory
        WHERE user_id = %s AND kind IN ('preference', 'place')
        ORDER BY created_at
        LIMIT 20
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, (user_id,))
        return await cur.fetchall()
