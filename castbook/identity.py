"""Identity scoring math, kept free of model code so it is unit-testable.

The judge worker produces ArcFace embeddings; this module turns them into the
numbers the identity gate decides on.
"""

from dataclasses import asdict, dataclass

import numpy as np


def normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    if n == 0.0:
        raise ValueError("zero-length embedding")
    return v / n


def character_embedding(embeddings: list[np.ndarray]) -> np.ndarray:
    """Mean of normalized embeddings (one per character-sheet view), renormalized."""
    if not embeddings:
        raise ValueError("no embeddings")
    return normalize(np.mean([normalize(e) for e in embeddings], axis=0))


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(normalize(a), normalize(b)))


@dataclass(frozen=True)
class IdentityScore:
    """Per-artifact identity summary against a character embedding.

    `face_rate` is the share of sampled frames with a detected face. A clip
    where the face vanishes should not pass just because the few frames that
    have one look right.
    """

    n_frames: int
    face_rate: float
    min: float | None
    p10: float | None
    mean: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def score_frames(reference: np.ndarray, frame_embeddings: list[np.ndarray | None]) -> IdentityScore:
    """`frame_embeddings[i]` is None when no face was detected in frame i."""
    n = len(frame_embeddings)
    sims = [cosine(reference, e) for e in frame_embeddings if e is not None]
    if not sims:
        return IdentityScore(n_frames=n, face_rate=0.0, min=None, p10=None, mean=None)
    arr = np.array(sims)
    return IdentityScore(
        n_frames=n,
        face_rate=len(sims) / n if n else 0.0,
        min=float(arr.min()),
        p10=float(np.percentile(arr, 10)),
        mean=float(arr.mean()),
    )
