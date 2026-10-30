"""CLI entrypoints. Run from the repo root:

uv run modal run -m castbook.entry::download_weights
uv run modal run -m castbook.entry::golden
uv run modal run -m castbook.entry::shot --character c01
"""

import json
from pathlib import Path

from castbook.config import MODELS
from castbook.multishot import fetch_artifacts, rejudge, run_request
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
    _download(result, final, out)
    print(f"saved to {out}/")


def _download(result: dict, final: dict, out: Path) -> None:
    """Fetch a run's final video and every attempt's artifact into `out`, and print a per-shot summary."""
    out.mkdir(parents=True, exist_ok=True)
    keys = {"final.mp4": result["final_key"]} if result["final_key"] else {}
    for s in result["shots"]:
        if s.get("keyframe_key") and not s["keyframe_attempts"]:
            keys[f"{s['shot_id']}/first_frame.png"] = s["keyframe_key"]  # lastframe_chain: previous clip's end
        for field, name in (("keyframe", "keyframe"), ("end_keyframe", "end_keyframe"), ("clip", "clip")):
            ext = "mp4" if field == "clip" else "png"
            for a in s.get(f"{field}_attempts", []):
                keys[f"{s['shot_id']}/{name}_{a['n']}.{ext}"] = a["key"]
    blobs = fetch_artifacts.remote([k for k in keys.values() if k])
    for name, key in keys.items():
        if key in blobs:
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            (out / name).write_bytes(blobs[key])
    (out / "record.json").write_text(json.dumps({**result, "run": final}, indent=2, default=str))

    print(f"{result['workflow']}: status={result['status']} billed=${final['billing']['usd']} wall={result['wall_s']}s")
    for s in result["shots"]:
        steps = []
        for field in ("keyframe", "end_keyframe", "clip"):
            if s.get(f"{field}_attempts"):
                steps.append(f"{field}[{' '.join(a['verdict']['status'] for a in s[f'{field}_attempts'])}]")
        print(f"  {s['shot_id']}: {s['status']:9} {' '.join(steps)} {s['error'] or ''}")


@app.local_entrypoint()
def scoreboard(
    script: str = "evals/scripts/cafe_morning.yaml",
    arms: str = "keyframe_i2v@2,lastframe_chain@1,keyframe_flf@1",
    max_parallel: int = 3,
    dry_run: bool = False,
):
    """Run one script through several workflow versions, one after another, and render the comparison.

    Arms run sequentially so they don't queue behind each other on the single-container GPU pools, and
    so each worker stays warm from one arm to the next. --dry-run prints the per-arm estimates only.
    """
    from datetime import UTC, datetime

    from castbook.runs import create_run, estimate
    from castbook.scoreboard import render, summarize
    from castbook.shots import load_script
    from castbook.state import ModalDictState
    from castbook.workflow import load_workflow

    spec = load_script(script)
    refs = [a.strip() for a in arms.split(",") if a.strip()]
    for ref in refs:
        e = estimate(load_workflow(ref), len(spec.shots))
        print(f"{ref:20} estimate ${e['usd_low']:.3f}-{e['usd_high']:.3f} (no cache hits assumed)")
    if dry_run:
        return

    name = f"{Path(script).stem}_{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    out = OUT / "scoreboard" / name
    state = ModalDictState()
    summaries = []
    for ref in refs:
        run, _ = create_run(state, load_workflow(ref), spec)
        result = run_request.remote(run["request_id"], max_parallel)
        _download(result, state.get("runs", run["request_id"]), out / ref)
        summaries.append(summarize(result))
    (out / "summary.json").write_text(json.dumps({"script": spec.model_dump(), "arms": summaries}, indent=2))
    page = render(out, summaries, spec.model_dump())
    for a in summaries:
        print(
            f"{a['workflow']:20} accepted {a['accepted']}/{a['n_shots']}  first-try {a['first_try']}  "
            f"min p10 {a['min_p10']}  warm ${a['warm_usd']:.3f}  $/acc-s {a['usd_per_accepted_s']}  "
            f"billed ${a['billed_usd']:.3f}"
        )
    print(f"scoreboard: {page.resolve()}")


@app.local_entrypoint()
def rejudge_run(request_id: str = "req_c5c36ab86736", workflow: str = "keyframe_i2v@2"):
    """Re-score a finished multishot run's attempts with another workflow's judge (CPU only), old vs new."""
    out = OUT / "multi" / request_id
    rec = json.loads((out / "record.json").read_text())
    old = {}
    for s in rec["shots"]:
        for a in s["keyframe_attempts"] + s.get("end_keyframe_attempts", []) + s["clip_attempts"]:
            old[a["key"]] = {"shot": s["shot_id"], "step": a["step"], "n": a["n"], "verdict": a["verdict"]}
    results = rejudge.remote([{"key": k, "step": v["step"]} for k, v in old.items()], rec["character"], workflow)
    for r in results:
        o = old[r["key"]]
        was, now = o["verdict"], r["verdict"]
        print(
            f"{o['shot']} {o['step']:12} #{o['n']}  {was['status']:12} {_fmt(was['value'])} -> "
            f"{now['status']:12} {_fmt(now['value'])}  cov {now['coverage']:.0%}  {'; '.join(now['reasons'])}"
        )
        frames = r.get("per_frame") or [r.get("frame")]
        sizes = " ".join(f"{f['face_px']}px:{_fmt(f['sim'])}" for f in frames if f and f.get("face_px"))
        print(f"      face width:sim  {sizes}")
    (out / f"rejudge_{workflow}.json").write_text(json.dumps(results, indent=2))


def _fmt(v: float | None) -> str:
    return "  -  " if v is None else f"{v:.2f}"
