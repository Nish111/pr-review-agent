"""Embedding models behind one small interface (decision S2). Nothing here downloads anything until asked."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Protocol

from pr_review.ingestion.text import ident_field

# S2: chosen model = bge (25 Oct spike). Each run records the exact version it used (name@commit-hash) in the index,
# so a silently updated model is refused rather than mixed (I8). jina is listed but does not load with
# transformers 5.x (spike, 25 Oct): see .genesis/decisions/S2-embedding-model.md.
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
        rev = cfg["revision"] or _cached_revision(cfg["name"])
        self.name = cfg["name"] + (f"@{rev}" if rev else "")       # I8: the exact version is part of the identity
        dim = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension", None)       # renamed in sentence-transformers 6
        self.dims = int(dim()) if dim else len(self._model.encode(["x"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, batch_size=16, normalize_embeddings=True).tolist()


def _cached_revision(repo_id: str) -> str | None:
    """The commit hash of the model version in the local Hugging Face cache (refs/main), if it can be read."""
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
    except ImportError:
        return None
    ref = Path(HF_HUB_CACHE) / ("models--" + repo_id.replace("/", "--")) / "refs" / "main"
    return ref.read_text(encoding="utf-8").strip() if ref.is_file() else None


def get(key: str) -> Embedder | None:
    if key == "none":
        return None
    if key.startswith("hash"):
        return HashEmbedder(int(key.split("-")[1]) if "-" in key else 64)
    return SentenceTransformerEmbedder(key)
