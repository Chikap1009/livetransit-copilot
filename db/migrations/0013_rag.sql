-- db/migrations/0013_rag.sql
-- Phase E: the RAG document library. Chunks of service alerts + agency policy/
-- reference docs, each with an embedding, so the agent can retrieve relevant
-- passages by meaning and answer with citations.

CREATE EXTENSION IF NOT EXISTS vector;   -- already enabled in 0012; safe to repeat

CREATE TABLE rag_documents (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source     TEXT NOT NULL,             -- 'alert' | 'policy' | 'reference'
    title      TEXT,                      -- human label, used in citations
    chunk_text TEXT NOT NULL,             -- the retrievable passage
    embedding  vector(384),               -- bge-small-en-v1.5
    metadata   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, chunk_text)           -- don't store the same chunk twice
);

-- Semantic retrieval over the chunks (approximate nearest-neighbour, cosine).
CREATE INDEX rag_documents_embed_idx ON rag_documents
    USING hnsw (embedding vector_cosine_ops);

-- Filter/refresh by source (e.g. wipe + re-ingest live alerts).
CREATE INDEX rag_documents_source_idx ON rag_documents (source);
