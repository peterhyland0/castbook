"""Shot scripts: the typed input to a multi-shot run.

A script names a character and a list of shots, each with a keyframe prompt
(what the still looks like) and a motion prompt (what happens in the clip).
For now scripts are written by hand; an LLM planner that turns a one-line idea
into a script is the next step and will produce this same structure.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ShotSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    keyframe: str = Field(min_length=1)
    motion: str = Field(min_length=1)


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")
    character: str
    seed: int = 7
    shots: list[ShotSpec] = Field(min_length=1, max_length=12)

    def model_post_init(self, _ctx) -> None:
        ids = [s.id for s in self.shots]
        if len(set(ids)) != len(ids):
            raise ValueError("shot ids must be unique")


def load_script(path: str | Path) -> Script:
    return Script.model_validate(yaml.safe_load(Path(path).read_text()))
