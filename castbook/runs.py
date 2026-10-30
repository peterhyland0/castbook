"""Run lifecycle shared by the API and the orchestrator: create (idempotently),
apply progress events, cancel, estimate. Pure logic over a StateStore."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from castbook.config import GPU_USD_PER_SECOND, IDLE_TAIL_S, MEASURED
from castbook.shots import Script
from castbook.state import StateStore
from castbook.workflow import Workflow

TERMINAL = {"succeeded", "failed", "cancelled"}


class IdempotencyConflict(Exception):
    """Same Idempotency-Key reused with a different request body."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _body_hash(workflow_ref: str, script: Script) -> str:
    blob = json.dumps({"workflow": workflow_ref, "script": script.model_dump()}, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def create_run(
    state: StateStore, workflow: Workflow, script: Script, idempotency_key: str | None = None
) -> tuple[dict, bool]:
    """Returns (run, created). Replaying an Idempotency-Key with the same body returns
    the original run instead of starting (and paying for) a second one."""
    body = _body_hash(workflow.ref, script)
    if idempotency_key:
        idem_id = hashlib.sha256(idempotency_key.encode()).hexdigest()
        seen = state.get("idempotency", idem_id)
        if seen is not None:
            if seen["body"] != body:
                raise IdempotencyConflict(idempotency_key)
            return state.get("runs", seen["request_id"]), False
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    run = {
        "request_id": request_id,
        "status": "queued",
        "workflow": workflow.ref,
        "character": script.character,
        "script": script.model_dump(),
        "created_at": _now(),
        "updated_at": _now(),
        "shots": {s.id: {"status": "pending", "attempts": []} for s in script.shots},
        "final_key": None,
        "billing": None,
        "estimate": estimate(workflow, len(script.shots)),
        "error": None,
    }
    state.put("runs", request_id, run)
    if idempotency_key:
        state.put("idempotency", idem_id, {"request_id": request_id, "body": body})
    return run, True


def update_run(state: StateStore, request_id: str, **fields: Any) -> dict:
    run = state.get("runs", request_id)
    run.update(fields, updated_at=_now())
    state.put("runs", request_id, run)
    return run


def apply_event(run: dict, script: Script, event: dict) -> None:
    """Fold an executor event into the run record (mutates `run`)."""
    if event["type"] == "shot":
        run["shots"][event["shot_id"]]["status"] = event["status"]
        if run["status"] == "queued":
            run["status"] = "running"
    elif event["type"] == "attempt":
        shot_id = script.shots[event["shot_index"]].id
        brief = {k: v for k, v in event.items() if k not in ("type", "shot_index")}
        run["shots"][shot_id]["attempts"].append(brief)


def request_cancel(state: StateStore, request_id: str) -> dict:
    run = state.get("runs", request_id)
    if run["status"] not in TERMINAL:
        state.put("cancel", request_id, True)
        run = update_run(state, request_id, cancel_requested=True)
    return run


def is_cancel_requested(state: StateStore, request_id: str) -> bool:
    return bool(state.get("cancel", request_id))


def step_calls(workflow: Workflow, n_shots: int) -> dict[str, int]:
    """First-try model calls per step for an n-shot script under the workflow's mode."""
    keyframes = 1 if workflow.mode == "lastframe_chain" else n_shots
    calls = {"keyframe": keyframes, "clip": n_shots}
    if workflow.mode == "keyframe_flf":
        calls["end_keyframe"] = n_shots
    return calls


def estimate(workflow: Workflow, n_shots: int) -> dict:
    """Price a run before it starts, from measured warm/cold step timings.

    `low` assumes warm containers and every step passing first time; `high`
    assumes a cold start per GPU worker (keyframe and end_keyframe share one),
    every attempt the retry policy allows, and the idle tail before scaledown.
    """
    low = high = 0.0
    cold_paid: set[str] = set()
    for step, calls in step_calls(workflow, n_shots).items():
        m = MEASURED[step]
        rate = GPU_USD_PER_SECOND[m["gpu"]]
        retry = workflow.steps[step].retry
        attempts = retry.max_attempts if retry else 1
        worker = workflow.steps[step].model
        load = 0.0 if worker in cold_paid else m["load_s"] + IDLE_TAIL_S
        cold_paid.add(worker)
        low += calls * m["infer_s"] * rate
        high += (load + calls * attempts * m["infer_s"]) * rate
    return {"usd_low": round(low, 3), "usd_high": round(high, 3), "basis": "measured H100 timings, Oct 2026"}
