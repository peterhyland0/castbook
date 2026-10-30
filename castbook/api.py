"""HTTP API. Shaped like Mage's own API (api.mage.space/v1): async submits that
return request_id / status_url / cancel_url, Idempotency-Key so retries never
double-charge, and a billing block on every run.

    POST /v1/characters                    save a portrait as a reusable character
    GET  /v1/characters                    list characters
    GET  /v1/workflows                     list workflow versions
    POST /v1/workflows/{ref}/estimate      price a script before running it
    POST /v1/workflows/{ref}/runs          start a run (202)
    GET  /v1/runs/{request_id}             status, per-shot attempts and verdicts, billing
    POST /v1/runs/{request_id}/cancel      cooperative cancel (finishes the current model call)
    GET  /v1/runs/{request_id}/result      the stitched mp4

Everything stateful is injected, so tests run it with in-memory fakes.
"""

import base64
import binascii
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError

from castbook.characters import CharacterError, create_character, golden_ids, public, resolve_character
from castbook.runs import IdempotencyConflict, create_run, estimate, request_cancel
from castbook.shots import Script, ShotSpec
from castbook.state import StateStore
from castbook.store import ArtifactStore
from castbook.workflow import WORKFLOWS_DIR, Workflow, load_workflow


class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    image_base64: str = Field(description="PNG or JPEG bytes, base64-encoded: one clear, front-facing portrait")


class RunIn(BaseModel):
    character_id: str
    shots: list[ShotSpec] = Field(min_length=1, max_length=12)
    seed: int = 7


def create_app(
    state: StateStore,
    store: ArtifactStore,
    artifacts_root: Path,
    launch: Callable[[str], None],
    embed: Callable[[bytes], dict],
    api_token: str | None,
    refresh: Callable[[], None] = lambda: None,
) -> FastAPI:
    """`launch(request_id)` starts the orchestrator; `embed(bytes)` runs the judge on a portrait;
    `refresh()` re-reads the artifact store (Volume reload) before serving stored files."""
    app = FastAPI(title="Castbook", version="0.2.0")
    bearer = HTTPBearer(auto_error=False)

    def auth(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        if api_token and (creds is None or creds.credentials != api_token):
            raise HTTPException(401, "missing or invalid bearer token")

    def workflow_or_404(ref: str) -> Workflow:
        try:
            return load_workflow(ref)
        except FileNotFoundError:
            raise HTTPException(404, f"unknown workflow {ref}") from None

    def run_or_404(request_id: str) -> dict:
        run = state.get("runs", request_id)
        if run is None:
            raise HTTPException(404, f"unknown run {request_id}")
        return run

    def urls(request: Request, request_id: str) -> dict:
        base = str(request.base_url).rstrip("/")
        return {
            "status_url": f"{base}/v1/runs/{request_id}",
            "cancel_url": f"{base}/v1/runs/{request_id}/cancel",
            "result_url": f"{base}/v1/runs/{request_id}/result",
        }

    @app.get("/v1/health")
    def health() -> dict:
        return {"ok": True}

    @app.post("/v1/characters", status_code=201, dependencies=[Depends(auth)])
    def post_character(body: CharacterIn) -> dict:
        try:
            portrait = base64.b64decode(body.image_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(422, "image_base64 is not valid base64") from None
        try:
            return public(create_character(state, store, body.name, portrait, embed))
        except CharacterError as e:
            raise HTTPException(422, str(e)) from None

    @app.get("/v1/characters", dependencies=[Depends(auth)])
    def list_characters() -> dict:
        refresh()
        for cid in golden_ids(artifacts_root):
            resolve_character(state, artifacts_root, cid)
        return {"characters": [public(state.get("characters", k)) for k in sorted(state.keys("characters"))]}

    @app.get("/v1/workflows", dependencies=[Depends(auth)])
    def list_workflows() -> dict:
        return {"workflows": sorted(p.stem for p in WORKFLOWS_DIR.glob("*.yaml"))}

    def _script(body: RunIn) -> Script:
        try:
            resolve_character(state, artifacts_root, body.character_id)
        except CharacterError as e:
            raise HTTPException(404, str(e)) from None
        try:
            return Script(character=body.character_id, seed=body.seed, shots=body.shots)
        except ValidationError as e:
            raise HTTPException(422, [{"loc": list(err["loc"]), "msg": err["msg"]} for err in e.errors()]) from None

    @app.post("/v1/workflows/{ref}/estimate", dependencies=[Depends(auth)])
    def post_estimate(ref: str, body: RunIn) -> dict:
        wf = workflow_or_404(ref)
        _script(body)
        return {"workflow": wf.ref, "shots": len(body.shots), **estimate(wf, len(body.shots))}

    @app.post("/v1/workflows/{ref}/runs", status_code=202, dependencies=[Depends(auth)])
    def post_run(
        ref: str,
        body: RunIn,
        request: Request,
        response: Response,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict:
        wf = workflow_or_404(ref)
        script = _script(body)
        try:
            run, created = create_run(state, wf, script, idempotency_key)
        except IdempotencyConflict:
            raise HTTPException(409, "Idempotency-Key was already used with a different request body") from None
        if created:
            launch(run["request_id"])
        else:
            response.status_code = 200
        return {
            "request_id": run["request_id"],
            "status": run["status"],
            "replayed": not created,
            "estimate": run["estimate"],
            **urls(request, run["request_id"]),
        }

    @app.get("/v1/runs/{request_id}", dependencies=[Depends(auth)])
    def get_run(request_id: str, request: Request) -> dict:
        run = run_or_404(request_id)
        return {**{k: v for k, v in run.items() if k != "script"}, **urls(request, request_id)}

    @app.post("/v1/runs/{request_id}/cancel", status_code=202, dependencies=[Depends(auth)])
    def cancel_run(request_id: str) -> dict:
        run_or_404(request_id)
        run = request_cancel(state, request_id)
        return {"request_id": request_id, "status": run["status"], "cancel_requested": True}

    @app.get("/v1/runs/{request_id}/result", dependencies=[Depends(auth)])
    def get_result(request_id: str) -> Response:
        run = run_or_404(request_id)
        if not run.get("final_key"):
            raise HTTPException(409, f"run is {run['status']}; no result yet")
        refresh()
        art = store.get(run["final_key"])
        if art is None:
            raise HTTPException(404, "result artifact missing")
        return Response(art.data, media_type="video/mp4")

    return app
