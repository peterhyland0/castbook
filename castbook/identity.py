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
    `occluded_rate` is the share of frames where a hand covers enough of the
    face box that the embedding no longer describes the face; those frames are
    excluded the same way. The two rates can overlap: a frame can be both
    turned away and covered. `n_scored` is how many frames the stats are computed
    over; when it is 0 the clip is unscorable, which is not the same as failing.
    """

    n_frames: int
    face_rate: float
    min: float | None
    p10: float | None
    mean: float | None
    profile_rate: float = 0.0
    occluded_rate: float = 0.0
    n_scored: int = 0
    max_yaw: float | None = None

    @property
    def coverage(self) -> float:
        return self.n_scored / self.n_frames if self.n_frames else 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def is_profile(yaw: float | None, max_yaw: float | None) -> bool:
    return yaw is not None and max_yaw is not None and abs(yaw) > max_yaw


def is_occluded(hand_overlap: float | None, max_hand_overlap: float | None) -> bool:
    return hand_overlap is not None and max_hand_overlap is not None and hand_overlap > max_hand_overlap


Box = tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


def overlap_fraction(face: Box, other: Box) -> float:
    """Share of the face box covered by `other` (0..1)."""
    w = min(face[2], other[2]) - max(face[0], other[0])
    h = min(face[3], other[3]) - max(face[1], other[1])
    area = (face[2] - face[0]) * (face[3] - face[1])
    return 0.0 if w <= 0 or h <= 0 or area <= 0 else (w * h) / area


def frame_status(
    has_face: bool,
    yaw: float | None,
    hand_overlap: float | None,
    max_yaw: float | None,
    max_hand_overlap: float | None,
) -> str:
    """Why a frame is or isn't scored. Order matters: a turned-away face that is
    also covered reads as "profile", since turning away is the bigger effect."""
    if not has_face:
        return "no_face"
    if is_profile(yaw, max_yaw):
        return "profile"
    if is_occluded(hand_overlap, max_hand_overlap):
        return "occluded"
    return "scored"


def score_frames(
    reference: np.ndarray,
    frame_embeddings: list[np.ndarray | None],
    yaws: list[float | None] | None = None,
    max_yaw: float | None = None,
    hand_overlaps: list[float | None] | None = None,
    max_hand_overlap: float | None = None,
) -> IdentityScore:
    """`frame_embeddings[i]` is None when no face was detected in frame i.

    `yaws[i]` is the head yaw in degrees for frame i (None if unknown). With
    `max_yaw` set, frames turned further than that are counted but not scored.
    `hand_overlaps[i]` is the share of the face box covered by a hand; with
    `max_hand_overlap` set, frames above it are counted as occluded, not scored.
    """
    n = len(frame_embeddings)
    yaws = yaws if yaws is not None else [None] * n
    hand_overlaps = hand_overlaps if hand_overlaps is not None else [None] * n
    if len(yaws) != n or len(hand_overlaps) != n:
        raise ValueError("yaws and hand_overlaps must align with frame_embeddings")
    statuses = [
        frame_status(e is not None, y, h, max_yaw, max_hand_overlap)
        for e, y, h in zip(frame_embeddings, yaws, hand_overlaps, strict=True)
    ]
    sims = [cosine(reference, e) for e, st in zip(frame_embeddings, statuses, strict=True) if st == "scored"]
    common = {
        "n_frames": n,
        "face_rate": sum(st != "no_face" for st in statuses) / n if n else 0.0,
        "profile_rate": statuses.count("profile") / n if n else 0.0,
        "occluded_rate": sum(
            e is not None and is_occluded(h, max_hand_overlap)
            for e, h in zip(frame_embeddings, hand_overlaps, strict=True)
        )
        / n
        if n
        else 0.0,
        "n_scored": len(sims),
        "max_yaw": max_yaw,
    }
    if not sims:
        return IdentityScore(min=None, p10=None, mean=None, **common)
    arr = np.array(sims)
    return IdentityScore(min=float(arr.min()), p10=float(np.percentile(arr, 10)), mean=float(arr.mean()), **common)


@dataclass(frozen=True)
class GateConfig:
    """Identity gate thresholds. `min_score` is provisional until calibrated on
    hand-labeled shots (M3): same-person generated frames scored 0.60-0.76 in the
    first runs, so 0.5 is a conservative starting point, not a tuned value."""

    metric: str = "p10"  # one of: min, p10, mean
    min_score: float = 0.5
    min_coverage: float = 0.5  # share of sampled frames that must be scorable


@dataclass(frozen=True)
class Verdict:
    """`pass` and `fail` are claims about identity. `unverifiable` means too few
    frames could be scored to make either claim, so the right response is a
    re-prompt (less head turn, hands away from face), not a blind re-roll."""

    status: str  # pass | fail | unverifiable
    metric: str
    value: float | None
    threshold: float
    coverage: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {**asdict(self), "reasons": list(self.reasons)}


def verdict(score: IdentityScore, gate: GateConfig) -> Verdict:
    value = getattr(score, gate.metric)
    common = {"metric": gate.metric, "value": value, "threshold": gate.min_score, "coverage": score.coverage}
    if score.n_scored == 0 or score.coverage < gate.min_coverage:
        reasons = [f"only {score.n_scored}/{score.n_frames} frames scorable (need {gate.min_coverage:.0%})"]
        if score.profile_rate:
            reasons.append(f"{score.profile_rate:.0%} profile")
        if score.occluded_rate:
            reasons.append(f"{score.occluded_rate:.0%} face covered by a hand")
        if score.face_rate < 1:
            reasons.append(f"{1 - score.face_rate:.0%} no face detected")
        return Verdict(status="unverifiable", reasons=tuple(reasons), **common)
    if value < gate.min_score:
        return Verdict(status="fail", reasons=(f"{gate.metric} {value:.2f} < {gate.min_score:.2f}",), **common)
    return Verdict(status="pass", reasons=(f"{gate.metric} {value:.2f} ≥ {gate.min_score:.2f}",), **common)
