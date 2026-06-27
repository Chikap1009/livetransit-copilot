"""Local text embeddings via fastembed (ONNX, CPU) for agent memory (Phase D).

No API and no quota: bge-small-en-v1.5 runs locally on CPU. The model is loaded
once (lru_cache) and baked into the Docker image at build time, so production
never downloads it at runtime. Deploys to any CPU host (e.g. a droplet).
"""
import asyncio
import os
from functools import lru_cache

from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"   # small, fast, 384-dim
DIM = 384
# In Docker we bake the model into a stable cache dir at build time (set via env);
# locally, None lets fastembed use its default cache.
_CACHE_DIR = os.environ.get("FASTEMBED_CACHE") or None


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=_CACHE_DIR)


def _embed_sync(text: str) -> list[float]:
    return next(iter(_model().embed([text]))).tolist()


async def embed(text: str) -> list[float]:
    """Embed one string. fastembed is sync/CPU-bound, so run it off the event loop."""
    return await asyncio.to_thread(_embed_sync, text)


def to_pgvector(vec: list[float]) -> str:
    """Format a vector as a pgvector literal, e.g. '[0.1,0.2,...]' for ::vector casts."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
