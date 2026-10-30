"""Versioned workflow configs (workflows/<id>@<version>.yaml)."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"

Cause = Literal["small", "profile", "occluded", "no_face"]  # identity.CAUSES


class RetryPolicy(BaseModel):
    """How the identity gate drives re-rolls for one step.

    The ladder mirrors what Mage Agent does in prose, made deterministic:
    re-roll with a new seed on `fail`; on `unverifiable`, first re-prompt with
    `reprompt_suffix` (keep the face visible) up to `max_reprompts` times, then
    re-roll. When attempts run out, keep the best attempt (pass > unverifiable >
    fail, then by score) and mark the shot as degraded rather than failing the run.

    `reprompt_by_cause` overrides the suffix for what blocked scoring
    (identity.blocking_cause: small, profile, occluded, no_face), e.g. tighter
    framing when the face is too small; other causes use `reprompt_suffix`.
    """

    model_config = ConfigDict(extra="forbid")
    max_attempts: int = 3
    max_reprompts: int = 1
    reprompt_suffix: str = ""
    reprompt_by_cause: dict[Cause, str] = {}

    def suffix_for(self, cause: str | None) -> str:
        return self.reprompt_by_cause.get(cause, self.reprompt_suffix)


class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str | None = None
    params: dict[str, Any] = {}
    sample_every: int | None = None
    max_yaw: float | None = None
    max_hand_overlap: float | None = None
    min_face_px: float | None = None
    gate: dict[str, Any] | None = None
    retry: RetryPolicy | None = None


# How shots are conditioned (see dag.py):
#   keyframe_i2v     one keyframe per shot from the portrait, then image-to-video from it
#   keyframe_flf     start and end keyframes per shot, then first-last-frame video between them
#   lastframe_chain  shot 1 as keyframe_i2v; every later shot starts from the previous clip's last frame
Mode = Literal["keyframe_i2v", "keyframe_flf", "lastframe_chain"]


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    version: int
    mode: Mode = "keyframe_i2v"
    steps: dict[str, StepConfig]

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def load_workflow(ref: str, directory: Path = WORKFLOWS_DIR) -> Workflow:
    path = directory / f"{ref}.yaml"
    wf = Workflow.model_validate(yaml.safe_load(path.read_text()))
    if wf.ref != ref:
        raise ValueError(f"{path.name} declares {wf.ref}")
    return wf
