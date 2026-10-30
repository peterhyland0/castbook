"""Content-addressed artifact store.

M1 backs this with a Modal Volume mounted at ARTIFACTS_DIR. M2 adds a GCS
implementation behind the same interface; callers only see `get`/`put`.

Layout: <root>/<key[:2]>/<key>/<name> plus a meta.json next to it.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class Artifact:
    key: str
    name: str
    data: bytes
    meta: dict[str, Any]


class ArtifactStore(Protocol):
    def get(self, key: str) -> Artifact | None: ...
    def put(self, key: str, name: str, data: bytes, meta: dict[str, Any]) -> Artifact: ...


class LocalStore:
    """Filesystem store. Works on a laptop and on a mounted Modal Volume."""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)

    def _dir(self, key: str) -> Path:
        return self.root / key[:2] / key

    def get(self, key: str) -> Artifact | None:
        d = self._dir(key)
        meta_path = d / "meta.json"
        if not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text())
        name = meta["name"]
        return Artifact(key=key, name=name, data=(d / name).read_bytes(), meta=meta)

    def put(self, key: str, name: str, data: bytes, meta: dict[str, Any]) -> Artifact:
        d = self._dir(key)
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(data)
        meta = {**meta, "name": name}
        # meta.json is written last: its presence is what marks the artifact complete,
        # so a crash mid-write never produces a cache hit on a partial file.
        tmp = d / "meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2, default=str))
        tmp.replace(d / "meta.json")
        return Artifact(key=key, name=name, data=data, meta=meta)

    def path(self, key: str) -> Path | None:
        a = self.get(key)
        return self._dir(key) / a.name if a else None
