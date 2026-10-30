"""Versioned workflow configs (workflows/<id>@<version>.yaml)."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"


class RetryPolicy(BaseModel):
    """How the identity gate drives re-rolls for one step.

    The ladder mirrors what Mage Agent does in prose, made deterministic:
    re-roll with a new seed on `fail`; on `unverifiable`, first re-prompt with
    `reprompt_suffix` (keep the face visible) up to `max_reprompts` times, then
    re-roll. When attempts run out, keep the best attempt (pass > unverifiable >
    fail, then by score) and mark the shot as degraded rather than failing the run.
    """

    model_config = ConfigDict(extra="forbid")
    max_attempts: int = 3
    max_reprompts: int = 1
    reprompt_suffix: str = ""


class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str | None = None
    params: dict[str, Any] = {}
    sample_every: int | None = None
    max_yaw: float | None = None
    max_hand_overlap: float | None = None
    gate: dict[str, Any] | None = None
    retry: RetryPolicy | None = None


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    version: int
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
