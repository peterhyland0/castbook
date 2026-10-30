"""Orchestration: runs on a CPU Modal container with the artifacts Volume mounted.

Each step is: compute its content-addressed key, return the cached artifact if
present, otherwise call the GPU worker, store the result, commit the Volume.
"""

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from castbook.config import MODELS
from castbook.costs import StepTiming, total_usd
from castbook.hashing import sha256_bytes, step_key
from castbook.store import Artifact, LocalStore
from castbook.workers.common import ARTIFACTS_DIR, app, artifacts_vol, cpu_image
from castbook.workers.judge import Judge
from castbook.workers.keyframe import Keyframe
from castbook.workers.portrait import Portrait
from castbook.workers.video import Video
from castbook.workflow import load_workflow

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "evals" / "golden.yaml"


def _revision(model: str) -> str:
    return MODELS[model].revision


class StepRunner:
    """Cache-or-compute for one run, recording what each step cost."""

    def __init__(self, store: LocalStore):
        self.store = store
        self.steps: list[dict] = []

    def run(self, step: str, model: str, params: dict, inputs: list[str], seed: int, name: str, compute):
        key = step_key(step, model, _revision(model), params, inputs, seed)
        t0 = time.perf_counter()
        hit = self.store.get(key)
        if hit is not None:
            self.steps.append({"step": step, "key": key, "cache": "hit", "wall_s": round(time.perf_counter() - t0, 3)})
            return hit
        data, meta = compute()
        art = self.store.put(
            key, name, data, {"step": step, "model": model, "params": params, "inputs": inputs, "seed": seed, **meta}
        )
        artifacts_vol.commit()
        self.steps.append(
            {"step": step, "key": key, "cache": "miss", "wall_s": round(time.perf_counter() - t0, 3), **meta}
        )
        return art

    def timings(self) -> list[StepTiming]:
        out = []
        for s in self.steps:
            for t in s.get("timings", []):
                out.append(StepTiming(gpu=t["gpu"], load_s=t["load_s"], infer_s=t["infer_s"], cold=t["cold"]))
        return out


def _golden_manifest(store_root: Path) -> dict:
    p = store_root / "golden" / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


@app.function(image=cpu_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=3600)
def make_golden() -> list[dict]:
    """Generate the golden portraits, keep only ones with exactly one detected face."""
    cfg = yaml.safe_load(GOLDEN_PATH.read_text())
    store = LocalStore(ARTIFACTS_DIR)
    runner = StepRunner(store)
    portrait, judge = Portrait(), Judge()
    manifest, results = {}, []
    for c in cfg["characters"]:
        prompt = f"{cfg['style']} The subject is {c['description']}."
        params = {"prompt": prompt, "width": 1024, "height": 1024}

        def compute(prompt=prompt, seed=c["seed"]):
            r = portrait.generate.remote(prompt, seed)
            return r["png"], {"timings": [r["timing"]]}

        art = runner.run("portrait", "z-image-turbo", params, [], c["seed"], "portrait.png", compute)
        emb = judge.embed.remote(art.data)
        manifest[c["id"]] = {
            "key": art.key,
            "sha256": sha256_bytes(art.data),
            "n_faces": emb["n_faces"],
            "embedding": emb["embedding"],
        }
        results.append({"id": c["id"], "key": art.key, "n_faces": emb["n_faces"], "png": art.data})
    golden_dir = Path(ARTIFACTS_DIR) / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    (golden_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    artifacts_vol.commit()
    return results


@app.function(image=cpu_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=300)
def golden_embedding(character_id: str) -> list[float]:
    golden = _golden_manifest(Path(ARTIFACTS_DIR)).get(character_id)
    if golden is None or golden["embedding"] is None:
        raise ValueError(f"no usable golden portrait for {character_id}")
    return golden["embedding"]


@app.function(image=cpu_image, volumes={ARTIFACTS_DIR: artifacts_vol}, timeout=3600)
def single_shot(
    character_id: str,
    keyframe_prompt: str,
    motion_prompt: str,
    workflow_ref: str = "single_shot@3",
    seed: int = 7,
) -> dict:
    """Portrait -> keyframe -> clip, with identity scores and per-step cost."""
    wf = load_workflow(workflow_ref)
    store = LocalStore(ARTIFACTS_DIR)
    artifacts_vol.reload()
    golden = _golden_manifest(Path(ARTIFACTS_DIR)).get(character_id)
    if golden is None or golden["embedding"] is None:
        raise ValueError(f"no usable golden portrait for {character_id}; run make_golden first")
    portrait = store.get(golden["key"])
    reference = golden["embedding"]
    runner = StepRunner(store)
    judge = Judge()
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    t_run = time.perf_counter()

    kf_cfg = wf.steps["keyframe"]
    kf_params = {**kf_cfg.params, "prompt": keyframe_prompt}

    def compute_keyframe() -> tuple[bytes, dict]:
        r = Keyframe().edit.remote(
            refs=[portrait.data],
            prompt=keyframe_prompt,
            seed=seed,
            width=kf_params["width"],
            height=kf_params["height"],
            lightning=kf_params["lightning"],
        )
        return r["png"], {"timings": [r["timing"]]}

    keyframe: Artifact = runner.run(
        "keyframe", kf_cfg.model, kf_params, [golden["sha256"]], seed, "keyframe.png", compute_keyframe
    )
    judge_cfg = wf.steps["judge"]
    judge_kwargs = {
        "max_yaw": judge_cfg.max_yaw,
        "max_hand_overlap": judge_cfg.max_hand_overlap,
        "gate": judge_cfg.gate,
    }
    kf_score = judge.score_image.remote(reference, keyframe.data, **judge_kwargs)

    clip_cfg = wf.steps["clip"]
    clip_params = {**clip_cfg.params, "prompt": motion_prompt}

    def compute_clip() -> tuple[bytes, dict]:
        p = clip_params
        r = Video().i2v.remote(
            first_frame=keyframe.data,
            prompt=motion_prompt,
            seed=seed,
            width=p["width"],
            height=p["height"],
            num_frames=p["num_frames"],
            fps=p["fps"],
            lightning=p["lightning"],
        )
        return r["mp4"], {"timings": [r["timing"]], "n_frames": r["n_frames"]}

    clip = runner.run("clip", clip_cfg.model, clip_params, [keyframe.key], seed, "clip.mp4", compute_clip)
    clip_score = judge.score_video.remote(reference, clip.data, judge_cfg.sample_every or 8, **judge_kwargs)

    record = {
        "run_id": run_id,
        "workflow": wf.ref,
        "character": character_id,
        "seed": seed,
        "prompts": {"keyframe": keyframe_prompt, "clip": motion_prompt},
        "steps": runner.steps,
        "verdicts": {"keyframe": kf_score.get("verdict"), "clip": clip_score.get("verdict")},
        "identity": {
            "keyframe": kf_score["score"],
            "clip": clip_score["score"],
            "clip_per_frame": clip_score["per_frame"],
            "keyframe_frame": kf_score.get("frame"),
        },
        "gpu_usd": total_usd(runner.timings()),
        "wall_s": round(time.perf_counter() - t_run, 1),
    }
    runs = Path(ARTIFACTS_DIR) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{run_id}.json").write_text(json.dumps(record, indent=2))
    artifacts_vol.commit()
    return {"record": record, "portrait": portrait.data, "keyframe": keyframe.data, "clip": clip.data}
