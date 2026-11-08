# Castbook

**Did the chained workflow keep the character?** Castbook answers that with a number, per shot, and says what it
cost.

It chains open-weights models (portrait → keyframes → video → stitch) on Modal GPUs, scores every shot against
the character's face with ArcFace, re-rolls the shots that drift, and records the GPU time of every step.
Workflows are versioned configs, so two recipes can run on the same script and be compared on identity, retries
and **dollars per accepted second of video**.

![The same 3-shot script through three workflows](docs/media/three-ways.gif)

*Same character, same script, three ways to chain it. Left: a keyframe per shot, then image-to-video. Middle:
start and end keyframes, then first/last-frame video. Right: each clip starts from the last frame of the one before.*

## What it shows so far

| | |
|---|---|
| **Re-anchoring beats chaining** | Chaining off the last frame never left the street: 0/3 shots usable. Start + end keyframes passed 2/3 shots on the first try, vs 1/3 for keyframe → video, at 9% lower cost per accepted second ($0.0116). |
| **A score you can trust, and an honest "can't tell"** | The first run's clip scored 0.33 mean and looked like drift. It was head pose: re-judged with profile frames left out, the same clip scores 0.67. The gate returns *pass*, *fail* or *unverifiable* (profile, hand on face, face too small) instead of a misleading low number. |
| **Fix problems at the cheap step** | A too-small face is caught at the keyframe and re-framed there for ~$0.003, instead of rendering every clip at 720p (3.6× the cost). Once measurable, that shot really did drift, so a lower threshold would have shipped a bad clip. |
| **Cost** | A warm 5 s Wan 2.2 clip is $0.025 (22 s on an H100). Most of a small run's bill is cold-loading the models, which is the next thing to fix. |

One character and one seed per arm so far, so treat these as directions, not results. Every experiment, with its
run and numbers, is in the [results log](docs/log.md). Build the demo page with `uv run python -m castbook.site`.

## How it works

- **Steps:** Qwen-Image-Edit-2511 composes each shot's keyframes from the portrait; Wan 2.2 I2V A14B animates
  them (image-to-video or first/last-frame); ffmpeg stitches. One failed shot degrades the run; it doesn't fail it.
- **Gates:** each keyframe and clip is scored (ArcFace p10 over scorable frames, plus face size and camera
  direction) and re-rolled or re-prompted by cause, within a per-step attempt budget.
- **Cache:** every step is content-addressed (`sha256(step, model@rev, params, inputs, seed)`), so re-runs and new
  workflow versions only compute what changed, and A/B arms share upstream work.
- **On Modal:** one GPU class per model family with weights on a Volume; a CPU orchestrator; a FastAPI layer with
  async runs (`request_id` / `status_url` / `cancel_url`), idempotency keys, a pre-run cost estimate and a billing
  block. 106 unit tests run in CI without a GPU.

## Status

- **Done:** single shot end to end; pose-, occlusion- and size-aware judge; multi-shot DAG with gate-driven
  re-rolls; versioned workflows; A/B scoreboard across three chain types; framing and camera checks
  (`keyframe_flf@5`); FastAPI layer (tested locally, not deployed).
- **Next:** a 6-shot, 30 s run from one API call; the retry ladder as config (same → degrade → alternate model →
  fallback shot); threshold calibration on hand-labeled frames; bf16 weights and memory snapshots for cold
  starts; more arms (full-step Wan, hosted video APIs).

The plan and motivation are in [PLAN.md](PLAN.md); the background research is in [reports/](reports/).

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
  pipeline.py      single-shot orchestrator (CPU container)
  dag.py           multi-shot executor: keyframe_i2v / keyframe_flf / lastframe_chain, gate-driven retries
  multishot.py     Modal backend, stitch + last-frame steps, run_request, rejudge
  api.py           FastAPI layer (serve.py deploys it)
  scoreboard.py    A/B summary + side-by-side HTML page
  viewer.py        single-run page with the identity-per-frame chart
  site.py          public demo page built from saved runs (-> site/, static)
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
uv run modal run -m castbook.entry::scoreboard --dry-run    # M3: per-arm cost estimates, no GPU
uv run modal run -m castbook.entry::scoreboard              # M3: 3 arms -> out/scoreboard/<script>_<time>/index.html
uv run modal run -m castbook.entry::rejudge_run --request-id req_c5c36ab86736   # re-score stored artifacts, CPU only
uv run modal run -m castbook.entry::multishot --script evals/scripts/cafe_morning.yaml   # M2: -> out/multi/<request_id>/
uv run pytest -q
uv run modal run -m castbook.entry::download_weights   # M0: ~215 GB into the castbook-models Volume
uv run modal run -m castbook.entry::golden             # M0: 5 portraits -> out/golden/
uv run modal run -m castbook.entry::shot --character c01   # M1: -> out/runs/<run_id>/
uv run python -m castbook.site                         # demo page from saved runs -> site/index.html
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
