-- db/migrations/0012_memory.sql
-- Phase D: long-term + vector memory for the Copilot.
-- One table holds a user's remembered facts AND each fact's embedding, so we can
-- fetch them by user (exact) or by meaning (vector similarity) in one place.

-- pgvector: adds the `vector` column type + similarity operators + HNSW index.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE user_memory (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    TEXT NOT NULL,                 -- who this fact is about (single demo user for now)
    kind       TEXT NOT NULL,                 -- 'preference' | 'place' | 'fact'
    content    TEXT NOT NULL,                 -- the human-readable fact, e.g. "home stop is Davis"
    embedding  vector(384),                   -- bge-small-en-v1.5 dimensionality
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, content)                 -- don't store the exact same fact twice
);

-- Fast exact lookups: "all of this user's memories" (and the preferences we auto-load).
CREATE INDEX user_memory_user_idx ON user_memory (user_id, kind);

-- Fast semantic recall: approximate nearest-neighbour over the embeddings.
-- cosine distance is the right metric for sentence-embedding similarity.
CREATE INDEX user_memory_embed_idx ON user_memory
    USING hnsw (embedding vector_cosine_ops);
