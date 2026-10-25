"""Embedding models behind one small interface (decision S2). Nothing here downloads anything until asked."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from pr_review.ingestion.text import ident_field

# S2: pin each model to an exact revision once the spike prints it (eval/spikes/s2_embed_check.py).
MODELS = {
    "bge": {"name": "BAAI/bge-small-en-v1.5", "remote_code": False, "revision": None},
    "jina": {"name": "jinaai/jina-embeddings-v2-base-code", "remote_code": True, "revision": None},
}


class Embedder(Protocol):
    name: str
    dims: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Deterministic, offline, no dependency: a bag of identifier parts hashed into `dims` buckets and normalised.
    Used by the tests and as a weak stand-in; it is NOT the S2 model and is never reported as one."""

    def __init__(self, dims: int = 64):
        self.dims, self.name = dims, f"hash-{dims}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dims
            for w in ident_field(t).split():
                h = int.from_bytes(hashlib.sha256(w.encode()).digest()[:4], "big")
                v[h % self.dims] += 1.0 if h & 1 << 31 else -1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class SentenceTransformerEmbedder:
    """A local sentence-transformers model on the CPU. Only imported when chosen."""

    def __init__(self, key: str):
        from sentence_transformers import SentenceTransformer  # optional dependency
        cfg = MODELS[key]
        self._model = SentenceTransformer(cfg["name"], trust_remote_code=cfg["remote_code"],
                                          revision=cfg["revision"], device="cpu")
        self.name = cfg["name"] + (f"@{cfg['revision']}" if cfg["revision"] else "")
        self.dims = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, batch_size=16, normalize_embeddings=True).tolist()


def get(key: str) -> Embedder | None:
    if key == "none":
        return None
    if key.startswith("hash"):
        return HashEmbedder(int(key.split("-")[1]) if "-" in key else 64)
    return SentenceTransformerEmbedder(key)
