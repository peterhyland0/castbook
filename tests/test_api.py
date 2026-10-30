import base64
import json

import pytest
from fastapi.testclient import TestClient

from castbook.api import create_app
from castbook.dag import Executor, StepCache, billing
from castbook.runs import apply_event, is_cancel_requested, update_run
from castbook.shots import Script
from castbook.state import MemoryState
from castbook.store import LocalStore
from castbook.workflow import load_workflow
from tests.test_dag import FakeBackend

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
SHOTS = [{"id": "s1", "keyframe": "kf one", "motion": "mv one"}, {"id": "s2", "keyframe": "kf two", "motion": "mv two"}]


class Harness:
    """Wires the API to in-memory state, a temp artifact store and the fake GPU backend.
    `launch` runs the real executor inline, the way run_request does on Modal."""

    def __init__(self, tmp_path, n_faces=1, auto_run=True):
        self.state = MemoryState()
        self.store = LocalStore(tmp_path / "artifacts")
        self.backend = FakeBackend()
        self.launched: list[str] = []
        self.auto_run = auto_run
        self.n_faces = n_faces
        # A golden character, as the manifest on the artifacts Volume would provide it.
        golden_dir = tmp_path / "artifacts" / "golden"
        golden_dir.mkdir(parents=True)
        self.store.put("ab" * 32, "portrait.png", b"golden-portrait", {})
        (golden_dir / "manifest.json").write_text(
            json.dumps({"c01": {"key": "ab" * 32, "sha256": "ab" * 32, "embedding": [1.0, 0.0], "n_faces": 1}})
        )
        app = create_app(self.state, self.store, tmp_path / "artifacts", self.launch, self.embed, TOKEN)
        self.client = TestClient(app)

    def embed(self, image):
        return {"embedding": [0.0, 1.0] if self.n_faces == 1 else None, "n_faces": self.n_faces}

    def launch(self, request_id):
        self.launched.append(request_id)
        if not self.auto_run:
            return
        run = self.state.get("runs", request_id)
        script = Script.model_validate(run["script"])
        from castbook.characters import resolve_character

        char = resolve_character(self.state, self.store.root, script.character)
        update_run(self.state, request_id, status="running")
        run["status"] = "running"

        def on_event(e):
            apply_event(run, script, e)
            self.state.put("runs", request_id, run)

        ex = Executor(
            load_workflow(run["workflow"]),
            self.backend,
            StepCache(self.store),
            on_event=on_event,
            should_cancel=lambda: is_cancel_requested(self.state, request_id),
        )
        result = ex.run(script, self.store.get(char["portrait_key"]).data, char["embedding"])
        update_run(
            self.state,
            request_id,
            status="succeeded" if result.final_key else "failed",
            final_key=result.final_key,
            billing=billing(result.timings),
        )


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def _post_run(h, headers=None, **body):
    payload = {"character_id": "c01", "shots": SHOTS, "seed": 3, **body}
    return h.client.post("/v1/workflows/keyframe_i2v@1/runs", json=payload, headers={**AUTH, **(headers or {})})


def test_auth_required(h):
    assert h.client.get("/v1/characters").status_code == 401
    assert h.client.get("/v1/characters", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert h.client.get("/v1/health").status_code == 200


def test_run_lifecycle(h):
    r = _post_run(h)
    assert r.status_code == 202
    body = r.json()
    assert body["request_id"].startswith("req_") and body["status_url"].endswith(body["request_id"])
    assert body["estimate"]["usd_low"] < body["estimate"]["usd_high"]

    run = h.client.get(f"/v1/runs/{body['request_id']}", headers=AUTH).json()
    assert run["status"] == "succeeded"
    assert {s["status"] for s in run["shots"].values()} == {"pass"}
    assert run["billing"]["usd"] > 0
    assert "script" not in run

    video = h.client.get(body["result_url"].replace("http://testserver", ""), headers=AUTH)
    assert video.status_code == 200 and video.headers["content-type"] == "video/mp4"


def test_idempotency_key_replays_instead_of_paying_twice(h):
    first = _post_run(h, headers={"Idempotency-Key": "abc"})
    again = _post_run(h, headers={"Idempotency-Key": "abc"})
    assert again.status_code == 200 and again.json()["replayed"] is True
    assert again.json()["request_id"] == first.json()["request_id"]
    assert len(h.launched) == 1
    conflict = _post_run(h, headers={"Idempotency-Key": "abc"}, seed=99)
    assert conflict.status_code == 409


def test_unknown_character_and_workflow(h):
    assert _post_run(h, character_id="nobody").status_code == 404
    r = h.client.post("/v1/workflows/nope@1/runs", json={"character_id": "c01", "shots": SHOTS}, headers=AUTH)
    assert r.status_code == 404


def test_create_character_requires_one_face(tmp_path):
    h = Harness(tmp_path)
    img = base64.b64encode(b"png-bytes").decode()
    r = h.client.post("/v1/characters", json={"name": "Ada Test", "image_base64": img}, headers=AUTH)
    assert r.status_code == 201 and r.json()["id"].startswith("ada-test-") and "embedding" not in r.json()
    two_faces = Harness(tmp_path / "b", n_faces=2)
    r = two_faces.client.post("/v1/characters", json={"name": "x", "image_base64": img}, headers=AUTH)
    assert r.status_code == 422 and "exactly one face" in r.json()["detail"]
    assert h.client.post("/v1/characters", json={"name": "x", "image_base64": "!!"}, headers=AUTH).status_code == 422


def test_uploaded_character_can_be_used_in_a_run(h):
    img = base64.b64encode(b"png-bytes").decode()
    cid = h.client.post("/v1/characters", json={"name": "Ada", "image_base64": img}, headers=AUTH).json()["id"]
    assert _post_run(h, character_id=cid).status_code == 202
    ids = [c["id"] for c in h.client.get("/v1/characters", headers=AUTH).json()["characters"]]
    assert cid in ids and "c01" in ids


def test_cancel_before_start(tmp_path):
    h = Harness(tmp_path, auto_run=False)
    rid = _post_run(h).json()["request_id"]
    assert h.client.post(f"/v1/runs/{rid}/cancel", headers=AUTH).json()["cancel_requested"] is True
    h.auto_run = True
    h.launch(rid)
    run = h.client.get(f"/v1/runs/{rid}", headers=AUTH).json()
    assert run["status"] == "failed" and {s["status"] for s in run["shots"].values()} == {"cancelled"}
    assert h.client.get(f"/v1/runs/{rid}/result", headers=AUTH).status_code == 409


def test_estimate_scales_with_shots(h):
    one = h.client.post(
        "/v1/workflows/keyframe_i2v@1/estimate", json={"character_id": "c01", "shots": SHOTS[:1]}, headers=AUTH
    ).json()
    two = h.client.post(
        "/v1/workflows/keyframe_i2v@1/estimate", json={"character_id": "c01", "shots": SHOTS}, headers=AUTH
    ).json()
    assert two["usd_low"] == pytest.approx(2 * one["usd_low"], rel=0.05)  # rounded to cents


def test_bad_script_rejected(h):
    dup = [SHOTS[0], SHOTS[0]]
    assert _post_run(h, shots=dup).status_code == 422
    assert _post_run(h, shots=[]).status_code == 422
