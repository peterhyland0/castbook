"""Modal wiring for multi-shot runs: the GPU backend, the stitch step, and the
orchestrator function the API spawns."""

import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from castbook.characters import resolve_character
from castbook.dag import Executor, StepCache, billing
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

    def clip(self, first_frame, prompt, seed, params):
        r = self.video.i2v.remote(
            first_frame=first_frame,
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
            reference, image, max_yaw=judge["max_yaw"], max_hand_overlap=judge["max_hand_overlap"], gate=judge["gate"]
        )

    def score_video(self, reference, video, judge):
        return self.judge.score_video.remote(
            reference,
            video,
            judge["sample_every"] or 8,
            max_yaw=judge["max_yaw"],
            max_hand_overlap=judge["max_hand_overlap"],
            gate=judge["gate"],
        )

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
