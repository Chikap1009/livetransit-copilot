"""Agentic (corrective) RAG over service alerts + agency policy docs (Phase E).

The library lives in `rag_documents` (pgvector). We chunk and embed with the local
fastembed model (no LLM quota), retrieve by cosine similarity, and the agent answers
from the retrieved chunks WITH citations. Corrective step (CRAG): if the top hit is
weak, widen the search; the agent is also told to rephrase and retry if results look
irrelevant. Retrieved text is treated as DATA, never as instructions (prompt-injection).

Run ingestion:  python -m backend.app.agent.rag
"""
from pathlib import Path

import httpx
from google.transit import gtfs_realtime_pb2
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from backend.app.agent import embeddings

MBTA_ALERTS_URL = "https://cdn.mbta.com/realtime/Alerts.pb"
KB_DIR = Path(__file__).resolve().parents[3] / "docs" / "kb"

# Cosine distance under which a chunk counts as "relevant" (smaller = closer).
RELEVANT_DISTANCE = 0.45


# --- chunking ----------------------------------------------------------------
def _chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Split a markdown doc into (section_title, body) chunks by '##' headings."""
    doc_title, head, body = "", None, []
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        if line.startswith("# "):
            doc_title = line[2:].strip()
        elif line.startswith("## "):
            if head is not None and (b := "\n".join(body).strip()):
                out.append((f"{doc_title} — {head}", b))
            head, body = line[3:].strip(), []
        else:
            body.append(line)
    if head is not None and (b := "\n".join(body).strip()):
        out.append((f"{doc_title} — {head}", b))
    return out


# --- storing chunks ----------------------------------------------------------
async def _store(pool: AsyncConnectionPool, source: str, items: list[tuple]) -> int:
    """Replace all chunks for `source`, embedding each. items: (title, text, metadata).

    No-op if there's nothing to ingest, so a missing source never wipes existing chunks.
    """
    if not items:
        return 0
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("DELETE FROM rag_documents WHERE source = %s", (source,))
        for title, text, meta in items:
            vec = embeddings.to_pgvector(await embeddings.embed(text))
            await cur.execute(
                """INSERT INTO rag_documents (source, title, chunk_text, embedding, metadata)
                   VALUES (%s, %s, %s, %s::vector, %s)
                   ON CONFLICT (source, chunk_text) DO NOTHING""",
                (source, title, text, vec, Json(meta)),
            )
    return len(items)


async def ingest_kb(pool: AsyncConnectionPool) -> int:
    """Ingest the curated policy/reference markdown in docs/kb/."""
    items = []
    for path in sorted(KB_DIR.glob("*.md")):
        for title, chunk in _chunk_markdown(path.read_text(encoding="utf-8")):
            items.append((title, chunk, {"file": path.name}))
    return await _store(pool, "policy", items)


async def ingest_alerts(pool: AsyncConnectionPool) -> int:
    """Ingest current live MBTA service alerts (refreshes the 'alert' source)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(MBTA_ALERTS_URL, timeout=15)
        resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    items = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        header = alert.header_text.translation[0].text if alert.header_text.translation else ""
        desc_tr = alert.description_text.translation
        desc = desc_tr[0].text if desc_tr else ""
        body = f"{header}\n{desc}".strip()
        if not body:
            continue
        routes = sorted({ie.route_id for ie in alert.informed_entity if ie.route_id})
        title = f"Alert: {header[:80]}" if header else "Service alert"
        items.append((title, body, {"routes": routes, "alert_id": entity.id}))
    return await _store(pool, "alert", items)


# --- retrieval + corrective loop ---------------------------------------------
async def retrieve(
    pool: AsyncConnectionPool, query: str, k: int = 4, source: str | None = None
) -> list[dict]:
    """Top-k chunks most similar to the query (optionally filtered to one source)."""
    vec = embeddings.to_pgvector(await embeddings.embed(query))
    where = "WHERE source = %s" if source else ""
    params: list = [vec]
    if source:
        params.append(source)
    params.append(k)
    sql = f"""
        SELECT source, title, chunk_text, metadata, embedding <=> %s::vector AS distance
        FROM rag_documents {where}
        ORDER BY distance LIMIT %s
    """
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


async def corrective_retrieve(pool: AsyncConnectionPool, query: str, k: int = 4) -> dict:
    """Retrieve, judge relevance by distance, and widen the search once if weak (CRAG)."""
    hits = await retrieve(pool, query, k)
    relevant = [h for h in hits if h["distance"] <= RELEVANT_DISTANCE]
    corrected = False
    if not relevant:                       # weak first pass -> corrective wider pass
        corrected = True
        hits = await retrieve(pool, query, k * 3)
        relevant = [h for h in hits if h["distance"] <= RELEVANT_DISTANCE]
    chunks = relevant or hits[:k]          # best-effort if still nothing strong
    return {
        "query": query,
        "relevant": bool(relevant),
        "corrected": corrected,
        "chunks": [
            {
                "source": c["source"], "title": c["title"], "text": c["chunk_text"],
                "distance": round(float(c["distance"]), 3),
            }
            for c in chunks
        ],
    }


async def bootstrap(pool: AsyncConnectionPool) -> dict:
    """Ingest both policy docs and live alerts."""
    return {"policy_chunks": await ingest_kb(pool), "alert_chunks": await ingest_alerts(pool)}


if __name__ == "__main__":
    from backend.app.core import config
    from backend.app.core.asyncrun import run

    async def _main():
        pool = AsyncConnectionPool(config.DATABASE_URL, min_size=1, max_size=2, open=False)
        await pool.open()
        print("ingested:", await bootstrap(pool))
        await pool.close()

    run(_main())
