"""CLI entrypoints. Run from the repo root:

uv run modal run -m castbook.entry::download_weights
uv run modal run -m castbook.entry::golden
uv run modal run -m castbook.entry::shot --character c01
"""

import json
from pathlib import Path

from castbook.config import MODELS
from castbook.multishot import fetch_artifacts, run_request
from castbook.pipeline import make_golden, single_shot
from castbook.viewer import render_index, render_run
from castbook.workers.common import app
from castbook.workers.download import download
from castbook.workers.smoke import smoke, smoke_judge

OUT = Path("out")


@app.local_entrypoint()
def download_weights(only: str = ""):
    names = [n for n in MODELS if not only or n in only.split(",")]
    for r in download.map(names, order_outputs=False):
        print(json.dumps(r))


@app.local_entrypoint()
def check():
    print(json.dumps({"diffusion": smoke.remote(), "judge": smoke_judge.remote()}, indent=2))


@app.local_entrypoint()
def judge_file(image: str, character: str = "c01", workflow: str = "single_shot@3"):
    """Score one local image against a golden character with a workflow's judge settings."""
    from castbook.pipeline import golden_embedding
    from castbook.workers.judge import Judge
    from castbook.workflow import load_workflow

    cfg = load_workflow(workflow).steps["judge"]
    r = Judge().score_image.remote(
        golden_embedding.remote(character),
        Path(image).read_bytes(),
        max_yaw=cfg.max_yaw,
        max_hand_overlap=cfg.max_hand_overlap,
        gate=cfg.gate,
    )
    print(json.dumps({"verdict": r["verdict"], "frame": r["frame"]}, indent=2))


@app.local_entrypoint()
def golden():
    out = OUT / "golden"
    out.mkdir(parents=True, exist_ok=True)
    for r in make_golden.remote():
        (out / f"{r['id']}.png").write_bytes(r["png"])
        print(f"{r['id']}: faces={r['n_faces']} key={r['key'][:12]}")
    print(f"saved to {out}/")


@app.local_entrypoint()
def shot(
    character: str = "c01",
    keyframe_prompt: str = (
        "The same person from the reference image, sitting at a rain-streaked café window at "
        "dusk, warm tungsten light from the left, medium close-up, cinematic 16:9 still, "
        "same face, same hairstyle, same outfit."
    ),
    motion_prompt: str = (
        "The person turns their head slowly toward the window and smiles softly, rain running "
        "down the glass, gentle camera push-in, cinematic lighting."
    ),
    workflow: str = "single_shot@3",
    seed: int = 7,
):
    r = single_shot.remote(character, keyframe_prompt, motion_prompt, workflow, seed)
    rec = r["record"]
    out = OUT / "runs" / rec["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "portrait.png").write_bytes(r["portrait"])
    (out / "keyframe.png").write_bytes(r["keyframe"])
    (out / "clip.mp4").write_bytes(r["clip"])
    (out / "record.json").write_text(json.dumps(rec, indent=2))
    print(json.dumps({k: rec[k] for k in ("run_id", "workflow", "gpu_usd", "wall_s")}, indent=2))
    print("identity:", json.dumps({k: rec["identity"][k] for k in ("keyframe", "clip")}, indent=2))
    for s in rec["steps"]:
        print(f"  {s['step']:9} cache={s['cache']:4} wall={s['wall_s']}s {s.get('timings', '')}")
    render_run(out)
    render_index(OUT / "runs")
    print(f"saved to {out}/  ·  viewer: {(out / 'index.html').resolve()}")


@app.local_entrypoint()
def multishot(script: str = "evals/scripts/cafe_morning.yaml", workflow: str = "keyframe_i2v@1", max_parallel: int = 3):
    """Run a shot script end to end on Modal (no HTTP), then download the result to out/multi/<request_id>/."""
    from castbook.runs import create_run
    from castbook.shots import load_script
    from castbook.state import ModalDictState
    from castbook.workflow import load_workflow

    state = ModalDictState()
    run, _ = create_run(state, load_workflow(workflow), load_script(script))
    rid = run["request_id"]
    print(f"{rid}: {len(run['shots'])} shots, estimate ${run['estimate']['usd_low']}-{run['estimate']['usd_high']}")
    result = run_request.remote(rid, max_parallel)
    final = state.get("runs", rid)

    out = OUT / "multi" / rid
    out.mkdir(parents=True, exist_ok=True)
    keys = {"final.mp4": result["final_key"]} if result["final_key"] else {}
    for s in result["shots"]:
        for a in s["keyframe_attempts"]:
            keys[f"{s['shot_id']}/keyframe_{a['n']}.png"] = a["key"]
        for a in s["clip_attempts"]:
            keys[f"{s['shot_id']}/clip_{a['n']}.mp4"] = a["key"]
    blobs = fetch_artifacts.remote([k for k in keys.values() if k])
    for name, key in keys.items():
        if key in blobs:
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            (out / name).write_bytes(blobs[key])
    (out / "record.json").write_text(json.dumps({**result, "run": final}, indent=2, default=str))

    print(f"status={result['status']} gpu_usd={final['billing']['usd']} wall={result['wall_s']}s")
    for s in result["shots"]:
        kf = " ".join(f"{a['verdict']['status']}" for a in s["keyframe_attempts"])
        cl = " ".join(f"{a['verdict']['status']}" for a in s["clip_attempts"])
        print(f"  {s['shot_id']}: {s['status']:9} keyframe[{kf}] clip[{cl}] {s['error'] or ''}")
    print(f"saved to {out}/")
