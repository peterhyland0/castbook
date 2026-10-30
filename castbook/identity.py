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

    `profile_rate` is the share of sampled frames whose face is turned past
    `max_yaw`. ArcFace similarity collapses on profiles even for the right
    person (first run: ~0.02 at full profile vs 0.71 frontal), so those frames
    are excluded from min/p10/mean rather than read as identity drift.
    `n_scored` is how many frames the stats are computed over; when it is 0
    the clip is unscorable, which is not the same as failing.
    """

    n_frames: int
    face_rate: float
    min: float | None
    p10: float | None
    mean: float | None
    profile_rate: float = 0.0
    n_scored: int = 0
    max_yaw: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def is_profile(yaw: float | None, max_yaw: float | None) -> bool:
    return yaw is not None and max_yaw is not None and abs(yaw) > max_yaw


def score_frames(
    reference: np.ndarray,
    frame_embeddings: list[np.ndarray | None],
    yaws: list[float | None] | None = None,
    max_yaw: float | None = None,
) -> IdentityScore:
    """`frame_embeddings[i]` is None when no face was detected in frame i.

    `yaws[i]` is the head yaw in degrees for frame i (None if unknown). With
    `max_yaw` set, frames turned further than that are counted but not scored.
    """
    n = len(frame_embeddings)
    yaws = yaws if yaws is not None else [None] * n
    if len(yaws) != n:
        raise ValueError("yaws must align with frame_embeddings")
    faces = [(e, y) for e, y in zip(frame_embeddings, yaws, strict=True) if e is not None]
    profile = sum(is_profile(y, max_yaw) for _, y in faces)
    sims = [cosine(reference, e) for e, y in faces if not is_profile(y, max_yaw)]
    common = {
        "n_frames": n,
        "face_rate": len(faces) / n if n else 0.0,
        "profile_rate": profile / n if n else 0.0,
        "n_scored": len(sims),
        "max_yaw": max_yaw,
    }
    if not sims:
        return IdentityScore(min=None, p10=None, mean=None, **common)
    arr = np.array(sims)
    return IdentityScore(min=float(arr.min()), p10=float(np.percentile(arr, 10)), mean=float(arr.mean()), **common)
