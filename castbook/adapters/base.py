"""Model capability contract.

Models differ in how they take conditioning: Mage's own Guide lists models where
Character references and First/Last frames are mutually exclusive (Lemon,
MiniMax-H3, Plum, Melon), models with no frame inputs (Cherry), and per-model
reference caps. The orchestrator reads these capabilities to build a valid
conditioning plan per model instead of hard-coding it per workflow.
"""

from dataclasses import dataclass
from enum import StrEnum


class Kind(StrEnum):
    TEXT_TO_IMAGE = "t2i"
    IMAGE_EDIT = "edit"
    IMAGE_TO_VIDEO = "i2v"


@dataclass(frozen=True)
class Capabilities:
    kind: Kind
    max_refs: int = 0
    refs_xor_first_frame: bool = False
    supports_first_frame: bool = False
    supports_last_frame: bool = False
    max_duration_s: float = 0.0
    audio: bool = False


@dataclass(frozen=True)
class Conditioning:
    refs: tuple[str, ...] = ()
    first_frame: str | None = None
    last_frame: str | None = None


class ConditioningError(ValueError):
    pass


def plan_conditioning(
    caps: Capabilities,
    refs: tuple[str, ...] = (),
    first_frame: str | None = None,
    last_frame: str | None = None,
) -> Conditioning:
    """Fit the requested inputs to what the model accepts.

    Identity is baked into keyframes upstream, so when a model forces a choice
    between references and a first frame, the first frame wins: it carries the
    face pixel-for-pixel, references only describe it.
    """
    if last_frame and not caps.supports_last_frame:
        raise ConditioningError("model does not accept a last frame")
    if last_frame and not first_frame:
        raise ConditioningError("a last frame needs a first frame")
    if first_frame and not caps.supports_first_frame:
        raise ConditioningError("model does not accept a first frame")
    if first_frame and caps.refs_xor_first_frame:
        refs = ()
    return Conditioning(refs=tuple(refs[: caps.max_refs]), first_frame=first_frame, last_frame=last_frame)


# Capabilities of the self-hosted models in this repo.
CAPABILITIES: dict[str, Capabilities] = {
    "z-image-turbo": Capabilities(kind=Kind.TEXT_TO_IMAGE),
    "qwen-image-edit-2511": Capabilities(kind=Kind.IMAGE_EDIT, max_refs=3),
    "wan2.2-i2v-a14b": Capabilities(
        kind=Kind.IMAGE_TO_VIDEO,
        supports_first_frame=True,
        supports_last_frame=True,
        refs_xor_first_frame=True,
        max_duration_s=5.0,
    ),
}
