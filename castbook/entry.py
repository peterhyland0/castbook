"""CLI entrypoints. Run from the repo root:

uv run modal run -m castbook.entry::download_weights
uv run modal run -m castbook.entry::golden
uv run modal run -m castbook.entry::shot --character c01
"""

import json
from pathlib import Path

from castbook.config import MODELS
from castbook.pipeline import make_golden, single_shot
from castbook.viewer import render_index, render_run
from castbook.workers.common import app
from castbook.workers.download import download
from castbook.workers.smoke import smoke

OUT = Path("out")


@app.local_entrypoint()
def download_weights(only: str = ""):
    names = [n for n in MODELS if not only or n in only.split(",")]
    for r in download.map(names, order_outputs=False):
        print(json.dumps(r))


@app.local_entrypoint()
def check():
    print(json.dumps(smoke.remote(), indent=2))


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
    workflow: str = "single_shot@1",
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
