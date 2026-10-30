"""Modal wiring for multi-shot runs: the GPU backend, the stitch step, and the
orchestrator function the API spawns."""

import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from castbook.characters import resolve_character
from castbook.dag import Executor, StepCache, billing, judge_config, judge_key
from castbook.runs import apply_event, is_cancel_requested, update_run
from castbook.shots import Script
from castbook.state import ModalDictState
from castbook.store import LocalStore
from castbook.workers.common import ARTIFACTS_DIR, app, artifacts_vol, service_image
from castbook.workers.judge import Judge
from castbook.workers.keyframe import Keyframe
from castbook.workers.video import Video
from castbook.workflow import load_workflow


@app.function(image=service_image, cpu=2, timeout=600)
def stitch_clips(clips: list[bytes], params: dict) -> tuple[bytes, dict]:
    """Concatenate same-codec clips without re-encoding (they share size, fps and codec by construction)."""
    from castbook.costs import StepTiming

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        listing = []
        for i, data in enumerate(clips):
            p = Path(d, f"{i:03d}.mp4")
            p.write_bytes(data)
            listing.append(f"file '{p}'")
        Path(d, "list.txt").write_text("\n".join(listing))
        out = Path(d, "final.mp4")
        cmd = ["ffmpeg", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{d}/list.txt", "-c", "copy"]
        subprocess.run([*cmd, str(out)], check=True)
        data = out.read_bytes()
    timing = StepTiming(gpu="CPU", load_s=0.0, infer_s=time.perf_counter() - t0, cold=False).to_dict()
    return data, timing


@app.function(image=service_image, cpu=1, timeout=300)
def extract_last_frame(video: bytes) -> tuple[bytes, dict]:
    """The clip's final frame as PNG: the next shot's first frame in lastframe_chain."""
    from castbook.costs import StepTiming

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        Path(d, "in.mp4").write_bytes(video)
        # -update 1 keeps overwriting one image, so what's left is the last decoded frame
        cmd = ["ffmpeg", "-loglevel", "error", "-sseof", "-1", "-i", f"{d}/in.mp4", "-update", "1", f"{d}/last.png"]
        subprocess.run(cmd, check=True)
        data = Path(d, "last.png").read_bytes()
    timing = StepTiming(gpu="CPU", load_s=0.0, infer_s=time.perf_counter() - t0, cold=False).to_dict()
    return data, timing


class ModalBackend:
    """dag.Backend over the Modal workers."""

    def __init__(self):
        self.kf, self.video, self.judge = Keyframe(), Video(), Judge()

    def keyframe(self, refs, prompt, seed, params):
        r = self.kf.edit.remote(
            refs=refs,
            prompt=prompt,
            seed=seed,
            width=params["width"],
            height=params["height"],
            lightning=params["lightning"],
        )
        return r["png"], r["timing"]

    def clip(self, first_frame, prompt, seed, params, last_frame=None):
        r = self.video.i2v.remote(
            first_frame=first_frame,
            last_frame=last_frame,
            prompt=prompt,
            seed=seed,
            width=params["width"],
            height=params["height"],
            num_frames=params["num_frames"],
            fps=params["fps"],
            lightning=params["lightning"],
        )
        return r["mp4"], r["timing"]

    def score_image(self, reference, image, judge):
        return self.judge.score_image.remote(
            reference,
            image,
            max_yaw=judge["max_yaw"],
            max_hand_overlap=judge["max_hand_overlap"],
            gate=judge["gate"],
            min_face_px=judge.get("min_face_px"),
        )

    def score_video(self, reference, video, judge):
        return self.judge.score_video.remote(
            reference,
            video,
            judge["sample_every"] or 8,
            max_yaw=judge["max_yaw"],
            max_hand_overlap=judge["max_hand_overlap"],
            gate=judge["gate"],
            min_face_px=judge.get("min_face_px"),
        )

    def last_frame(self, video):
        return extract_last_frame.remote(video)

    def stitch(self, clips, params):
        return stitch_clips.remote(clips, params)


@app.function(image=service_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=2 * 3600)
def run_request(request_id: str, max_parallel: int = 3) -> dict:
    """Execute one queued run end to end, keeping its state record current as it goes."""
    state = ModalDictState()
    run = state.get("runs", request_id)
    wf = load_workflow(run["workflow"])
    script = Script.model_validate(run["script"])
    artifacts_vol.reload()
    store = LocalStore(ARTIFACTS_DIR)
    character = resolve_character(state, Path(ARTIFACTS_DIR), script.character)
    portrait = store.get(character["portrait_key"]).data

    lock = threading.Lock()

    def on_event(event: dict) -> None:
        with lock:
            apply_event(run, script, event)
            state.put("runs", request_id, run)

    commit_lock = threading.Lock()

    def commit() -> None:
        with commit_lock:
            artifacts_vol.commit()

    update_run(state, request_id, status="running")
    run["status"] = "running"
    executor = Executor(
        wf,
        ModalBackend(),
        StepCache(store, commit),
        max_parallel=max_parallel,
        on_event=on_event,
        should_cancel=lambda: is_cancel_requested(state, request_id),
    )
    try:
        result = executor.run(script, portrait, character["embedding"])
    except Exception as e:
        update_run(state, request_id, status="failed", error=f"{type(e).__name__}: {e}")
        raise
    cancelled = is_cancel_requested(state, request_id)
    status = "cancelled" if cancelled else ("succeeded" if result.final_key else "failed")
    record = result.to_dict()
    records = Path(ARTIFACTS_DIR) / "multi" / request_id
    records.mkdir(parents=True, exist_ok=True)
    (records / "record.json").write_text(json.dumps({"request_id": request_id, **record}, indent=2))
    artifacts_vol.commit()
    with lock:
        run.update(
            status=status,
            final_key=result.final_key,
            billing=billing(result.timings),
            shot_results={
                s.shot_id: {
                    "status": s.status,
                    "clip_key": s.clip_key,
                    "keyframe_key": s.keyframe_key,
                    "end_keyframe_key": s.end_keyframe_key,
                    "error": s.error,
                }
                for s in result.shots
            },
            wall_s=result.wall_s,
        )
        state.put("runs", request_id, run)
    return {"request_id": request_id, "status": status, **record}


@app.function(image=service_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=600)
def fetch_artifacts(keys: list[str]) -> dict[str, bytes]:
    artifacts_vol.reload()
    store = LocalStore(ARTIFACTS_DIR)
    return {k: store.get(k).data for k in keys if store.get(k) is not None}


@app.function(image=service_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=1200)
def rejudge(attempts: list[dict], character_id: str, workflow_ref: str) -> list[dict]:
    """Re-score stored artifacts with another workflow's judge settings: CPU only, no generation.

    `attempts` are [{"key", "step"}]. Results land in the judge cache under the same keys the
    executor uses, so a later run of that workflow reuses them.
    """
    wf = load_workflow(workflow_ref)
    artifacts_vol.reload()
    store = LocalStore(ARTIFACTS_DIR)
    character = resolve_character(ModalDictState(), Path(ARTIFACTS_DIR), character_id)
    cfg = judge_config(wf)
    backend = ModalBackend()
    cache = StepCache(store, artifacts_vol.commit)
    ref = character["embedding"]
    out = []
    for a in attempts:
        data = store.get(a["key"]).data
        score = backend.score_video if a["step"] == "clip" else backend.score_image
        result = cache.judged(judge_key(cfg, a["key"]), lambda data=data, score=score: score(ref, data, cfg))
        out.append({**a, **result})
    return out
