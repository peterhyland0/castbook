# Castbook

Identity-gated, versioned multi-model video pipelines on Modal. You give it a character and a shot, and it chains
open-weights models (keyframe → clip), scores every output against the character's face, and records what each
step cost.

The plan and motivation are in [PLAN.md](PLAN.md); the background research is in [reports/](reports/).

## Status

- **M0 (setup):** weights on a Modal Volume and a 5-character golden set.
- **M1 (single shot end to end):** portrait → Qwen-Image-Edit-2511 keyframe → Wan 2.2 I2V clip, with ArcFace
  identity scores and per-step GPU cost.
- **Next (M2):** multi-shot DAG, identity gate with re-roll, FastAPI, Postgres step table, GCS artifacts.

## First result (2026-10-29, run `20261030T014009-ba3d2d`, character c01)

| Step | Model | Load (cold) | Inference | Attributable $ |
|---|---|---|---|---|
| keyframe | Qwen-Image-Edit-2511, 4-step Lightning, 1248×720 | 56.7 s | 5.4 s | $0.068 |
| clip | Wan 2.2 I2V A14B, 4-step Lightning, 832×480, 81 frames | 227.2 s | 22.4 s | $0.274 |
| **total** | | | | **$0.34** (340 s wall) |

- **Identity:** keyframe vs portrait ArcFace 0.76. The clip scores 0.71 on frame 0, falls to 0.44 by frame 32 and to 0.01–0.05 from frame 56 on.
- **The falloff is head pose, not identity drift.** The motion prompt turns her toward the window, so later frames are near-profile, and ArcFace similarity collapses on profiles even for the right person. The gate must be pose-aware before it can re-roll anything: use InsightFace's yaw estimate to skip or down-weight frames past about 45°, and report a profile rate.
- **Warm cost per clip is about $0.025.** That's 22.4 s on an H100, against Mage's listed Wan 2.2 Fast at 45 Gems / ~23 s. Inference speed is already at parity.
- **The cost is the cold start.** Wan's fp32 weights take 227 s to load and cast. Re-saving the weights in bf16 plus memory snapshots (M4) is the obvious first win.
- **Visible artifact:** a hand-raise gesture appears that wasn't in the prompt. The 4-step distilled model trades motion control for speed, which is something the full-step A/B arm should show.

## Layout

```
castbook/
  config.py        model weights, volumes, GPU $/s
  hashing.py       content-addressed step keys
  store.py         artifact store (Modal Volume now, GCS in M2)
  identity.py      ArcFace scoring math (min / p10 / mean / face rate)
  costs.py         GPU-seconds -> $
  workflow.py      versioned workflow configs (workflows/<id>@<version>.yaml)
  adapters/base.py model capability contract + conditioning planner
  pipeline.py      orchestrator functions (CPU container)
  entry.py         CLI entrypoints
  workers/         one Modal class per model family
    portrait.py    Z-Image Turbo, L40S
    keyframe.py    Qwen-Image-Edit-2511 + Lightning, H100
    video.py       Wan 2.2 I2V A14B + Lightning, H100
    judge.py       InsightFace buffalo_l, CPU
evals/golden.yaml  golden character set (generated people only)
workflows/         immutable workflow versions
tests/             unit tests (no GPU needed)
```

## Run

```bash
uv sync
uv run pytest -q
uv run modal run -m castbook.entry::download_weights   # M0: ~215 GB into the castbook-models Volume
uv run modal run -m castbook.entry::golden             # M0: 5 portraits -> out/golden/
uv run modal run -m castbook.entry::shot --character c01   # M1: -> out/runs/<run_id>/
```

Each `shot` also writes a self-contained viewer page, `out/runs/<run_id>/index.html`, with the media embedded, an
identity-per-frame chart synced to the clip, and the cost table. `out/runs/index.html` lists every run. Re-render them
all with `uv run python -m castbook.viewer`.

Run the same `shot` command twice and the second run is a cache hit on every step: the keys are
`sha256(step, model@revision, params, input hashes, seed)`.

## Cost notes

`gpu_usd` in a run record is *attributable* GPU time: model load on the call that paid for the cold start, plus
inference. Modal also bills idle containers during `scaledown_window` (120 s here), so the invoice will be a little
higher. GPU prices in `config.py` are approximate; check modal.com/pricing.
