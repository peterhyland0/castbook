"""Character registry: a saved portrait plus its ArcFace embedding, reusable across runs.

Like Mage's Characters, one front-facing portrait defines the face. The golden
set (evals/golden.yaml) is registered lazily from its manifest on the artifacts
Volume, so golden ids work in the API without a separate import step.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from castbook.hashing import sha256_bytes
from castbook.state import StateStore

_SLUG = re.compile(r"[^a-z0-9]+")


class CharacterError(ValueError):
    pass


def golden_ids(artifacts_root: Path) -> list[str]:
    manifest_path = artifacts_root / "golden" / "manifest.json"
    return sorted(json.loads(manifest_path.read_text())) if manifest_path.exists() else []


def resolve_character(state: StateStore, artifacts_root: Path, character_id: str) -> dict:
    found = state.get("characters", character_id)
    if found is not None:
        return found
    manifest_path = artifacts_root / "golden" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    golden = manifest.get(character_id)
    if golden is None or golden.get("embedding") is None:
        raise CharacterError(f"unknown character {character_id}")
    record = {
        "id": character_id,
        "name": character_id,
        "portrait_key": golden["key"],
        "sha256": golden["sha256"],
        "embedding": golden["embedding"],
        "source": "golden",
    }
    state.put("characters", character_id, record)
    return record


def create_character(state: StateStore, store, name: str, portrait: bytes, embed) -> dict:
    """`embed(bytes) -> {"embedding", "n_faces"}`. Rejects images without exactly one face."""
    result = embed(portrait)
    if result["n_faces"] != 1 or result["embedding"] is None:
        raise CharacterError(f"portrait must contain exactly one face (found {result['n_faces']})")
    sha = sha256_bytes(portrait)
    slug = _SLUG.sub("-", name.lower()).strip("-")[:24] or "character"
    character_id = f"{slug}-{uuid.uuid4().hex[:6]}"
    store.put(sha, "portrait.png", portrait, {"step": "character", "name": name})
    record = {
        "id": character_id,
        "name": name,
        "portrait_key": sha,
        "sha256": sha,
        "embedding": result["embedding"],
        "source": "upload",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    state.put("characters", character_id, record)
    return record


def public(record: dict) -> dict:
    """API view: no 512-float embedding in list responses."""
    return {k: v for k, v in record.items() if k != "embedding"}
