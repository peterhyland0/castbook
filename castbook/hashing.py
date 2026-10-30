"""Content-addressed keys for pipeline artifacts.

A step's output is identified by everything that determines it: the step name,
the model and its revision, the parameters, the hashes of its inputs, and the
seed. Same key means same output, so a cache hit lets the orchestrator skip the
step (free resume, and A/B arms share upstream work).
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    if isinstance(obj, float):
        # Avoid 0.1 vs 0.10000000000000001 style drift across platforms.
        return repr(round(obj, 10))
    return obj


def step_key(
    step: str,
    model: str,
    revision: str,
    params: Mapping[str, Any],
    input_hashes: Sequence[str],
    seed: int,
) -> str:
    payload = {
        "step": step,
        "model": f"{model}@{revision}",
        "params": _canonical(params),
        # Order matters (e.g. reference image 1 vs 2), so don't sort.
        "inputs": list(input_hashes),
        "seed": seed,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(blob)
