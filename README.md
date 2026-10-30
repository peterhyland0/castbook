# Castbook

Identity-gated, versioned multi-model video pipelines on Modal. You give it a character and a shot, and it chains
open-weights models (keyframe → clip), scores every output against the character's face, and records what each
step cost.

The plan and motivation are in [PLAN.md](PLAN.md); the background research is in [reports/](reports/).

## Status

- **M0 (setup):** weights on a Modal Volume and a 5-character golden set.
- **M1 (single shot end to end):** portrait → Qwen-Image-Edit-2511 keyframe → Wan 2.2 I2V clip, with ArcFace
  identity scores and per-step GPU cost.
- **M2 (in progress):** multi-shot DAG with gate-driven re-rolls and stitching, run on Modal. FastAPI layer built
  and tested locally but not deployed. Run state is a modal.Dict for now (Postgres later); artifacts are still on
  a Modal Volume (GCS later). Not started: LLM shot planner (needs an Anthropic key), moderation gates.
- **M3 (started):** A/B scoreboard across three chain types (`keyframe_i2v`, `lastframe_chain`, `keyframe_flf`) on
  one script and one character. The full golden set and threshold calibration are next.

## First result (2026-10-29, run `20261030T014009-ba3d2d`, character c01)

| Step | Model | Load (cold) | Inference | Attributable $ |
|---|---|---|---|---|
| keyframe | Qwen-Image-Edit-2511, 4-step Lightning, 1248×720 | 56.7 s | 5.4 s | $0.068 |
| clip | Wan 2.2 I2V A14B, 4-step Lightning, 832×480, 81 frames | 227.2 s | 22.4 s | $0.274 |
| **total** | | | | **$0.34** (340 s wall) |

- **Identity:** keyframe vs portrait ArcFace 0.76. The clip scores 0.71 on frame 0, falls to 0.44 by frame 32 and to 0.01–0.05 from frame 56 on.
- **The falloff is mostly head pose, not identity drift.** The motion prompt turns her toward the window, so later frames are near-profile, and ArcFace similarity collapses on profiles even for the right person.
- **Warm cost per clip is about $0.025.** That's 22.4 s on an H100, against Mage's listed Wan 2.2 Fast at 45 Gems / ~23 s. Inference speed is already at parity.
- **The cost is the cold start.** Wan's fp32 weights take 227 s to load and cast. Re-saving the weights in bf16 plus memory snapshots (M4) is the obvious first win.
- **Visible artifact:** a hand-raise gesture appears that wasn't in the prompt. The 4-step distilled model trades motion control for speed, which is something the full-step A/B arm should show.

## Pose-aware judge (`single_shot@2`, run `20261030T022427-2e8cae`)

Workflow @2 changes only the judge: it samples every 4th frame and treats frames turned more than 45° (InsightFace
yaw) as *profile*, which are counted but left out of the score. The keyframe and clip steps are unchanged, so their
content-addressed keys match @1. The rerun was a cache hit on both: **$0 GPU, 15 s wall**, CPU judge only.

| | @1 (all frames) | @2 (frames within ±45°) |
|---|---|---|
| Clip identity mean | 0.33 | **0.67** |
| Clip identity min | 0.01 | **0.61** |
| Frames scored | 11 / 11 | 5 / 21 |
| Profile rate | — | 76% |

- **Yaw is sane:** 21° on frame 0 (she's already angled in the keyframe), about 88° from frame 28 on.
- **Pose isn't the whole story.** Between frames 36 and 56 the yaw holds at about 88° while similarity falls from
  0.37 to 0.02. That's where her hand comes up near her face, so occlusion matters too; a face-visibility check
  belongs next to the yaw check.
- **76% of this clip can't be vouched for.** That's why the gate has three verdicts (below).

## Gate verdicts and occlusion (`single_shot@3`, run `20261030T024303-676f72`)

The judge now returns a verdict per artifact:
- **pass / fail:** a claim about identity, using `p10` over scored frames against `min_score` 0.5. The threshold is
  provisional until calibrated: same-person generated frames have scored 0.60–0.76 so far.
- **unverifiable:** fewer than 50% of sampled frames could be scored, so no claim either way. The next action is a
  re-prompt (less head turn, hands away from the face), not a blind re-roll.

**Occlusion check:** MediaPipe's hand landmarker finds hands, and a frame counts as occluded when hands cover more
than 15% of the face box. Profile and occlusion are counted independently, so a frame can be both.

| Artifact | Verdict | Why |
|---|---|---|
| keyframe | **pass** | p10 0.76 ≥ 0.50 |
| clip | **unverifiable** | only 5/21 frames scorable; 76% profile; hand on face 0% |
| control: clip frame 0 | **pass** | p10 0.71 |
| control: frame 0 with a hand pasted over the face | **unverifiable** | hand covers 17.7% of face box; raw similarity fell to 0.39, which would otherwise have been a false *fail* |

- **The hand in this clip is beside the face, not on it.** MediaPipe finds one or two hands from frame 40 on, at
  x≈456–548, while the face box ends at x≈398–446. My earlier guess that a hand caused the late similarity drop was
  wrong. The drop at constant ~88° yaw is the extreme angle itself, where even the pose estimate becomes unstable
  (pitch and roll swing ±180°).
- **Detection confidence and embedding norm can't separate occlusion from pose on their own.** Both fell across
  the turn (0.89 → 0.67 and 18–20 → 13–15), so they're recorded per frame for calibration but aren't gating.
- **Score any image** with `uv run modal run -m castbook.entry::judge_file --image <path> --character c01`.

## M2: multi-shot run (`keyframe_i2v@1`, request `req_c5c36ab86736`, script `evals/scripts/cafe_morning.yaml`)

Three shots of c01 (street at dawn, café counter, café window), each a keyframe → clip chain with the identity gate
driving re-rolls, then stitched into one 15 s video. **Succeeded: $0.39 attributable GPU, 419 s wall.**

| Shot | Keyframe attempts | Clip attempts | Result |
|---|---|---|---|
| s1 wide street | fail 0.48 → fail 0.48 → **pass 0.52** | fail 0.24 → fail 0.29 | degraded (best clip kept) |
| s2 café counter | **pass 0.67** | unverifiable (67% profile) → **re-prompted, pass 0.50** | pass |
| s3 café window | **pass 0.77** | **pass 0.56** | pass |

- **The retry ladder behaved as designed on real outputs.** Failed keyframes were re-rolled with new seeds. The
  unverifiable clip was re-prompted ("keep the face turned toward the camera") and passed. The exhausted shot kept
  its best attempt and the run still produced a video.
- **Shot 1's *fail* is a false fail from face size.** It's visibly the same person, but small in a wide shot:
  similarity tracks face width (55 px → 0.33, 80 px → 0.52, 135 px → 0.57). That's the third false-fail mode, after
  profile and occlusion. Next: a minimum face size below which frames are *unverifiable*, and an M3 calibration of
  the threshold by face size rather than one global 0.5.
- **Warm step times:** keyframe 2.3–2.4 s, clip 19.8 s. **Cold loads:** 43 s (Qwen-Edit) and 198 s (Wan). One cold
  start per model pool, because each pool is capped at one container.
- **Cost split:** $0.27 of the $0.39 is the two cold loads; the eight warm model calls cost $0.12.

## M3 start: 3-arm scoreboard (script `cafe_morning`, character c01, `out/scoreboard/cafe_morning_20261030-181634/`)

The same 3-shot script through three workflow versions, run back to back on Modal. All three use the judge with
the new minimum face size (`min_face_px: 64`, so narrower faces count as *unverifiable* rather than *fail*).

| Workflow | Accepted | First try | Min p10 | Mean p10 | Attempts | Warm $ | $/accepted s | Billed $ |
|---|---|---|---|---|---|---|---|---|
| `keyframe_i2v@2`: keyframe per shot → I2V (Mage Agent's recipe) | 2/3 | 1/3 | 0.50 | 0.53 | 10 | $0.129 | $0.0127 | $0.141 |
| `lastframe_chain@1`: each shot starts from the previous clip's last frame | **0/3** | 0/3 | – | – | 9 | $0.142 | – | $0.086 |
| `keyframe_flf@1`: start + end keyframe per shot → first-last-frame video | 2/3 | **2/3** | **0.52** | **0.57** | 12 | **$0.117** | **$0.0116** | $0.159 |

*Warm $* is the inference time of every attempt, whether or not it was a cache hit this run; compare arms on that.
*Billed $* depends on run order (the first two arms reused cached shot-1 work and the FLF arm paid the keyframe cold
start). Total billed was $0.39, plus roughly $0.26 of idle time before the workers scaled down.

- **The last-frame chain can't change scenes.** Starting from the street's last frame, shots 2 and 3 never reach the
  café: in the "café window" shot she holds a cup in the middle of the street. Its faces stay wide-shot small, so
  nothing could be verified (s3: 38% of frames scorable, p10 0.11). It's the cheapest arm to *bill* only because
  shot 1 was cached; on warm cost it's the most expensive, and it shipped nothing acceptable.
- **First-last-frame beat Mage Agent's recipe on this script:** both verifiable shots passed first try (the
  keyframe arm needed a re-prompt on s2), identity was higher (s3 p10 0.62 vs 0.56), and warm cost per accepted
  second was 9% lower even with an extra keyframe per shot, because it needed no clip re-roll. This is one character,
  one seed and two scorable shots, so treat it as a direction, not a result.
- **Shot 1 is *unverifiable* in every arm, which is correct.** The face is 52–56 px wide in the 832×480 clip. The
  keyframe for the same shot is 1248×720, where the face is 76–84 px, so the face shrinks by a third between steps.
  The FLF end keyframe framed her closer, but in the clip the face never got past 64 px (0% scorable). Fixes to
  try: render clips at 720p, re-prompt *small*-face shots for tighter framing (the current re-prompt only asks for a
  frontal face), or have the planner avoid wide shots for identity-critical beats.
- **Re-judging is free of GPU.** `rejudge_run` re-scored the M2 run's stored artifacts with the new judge on CPU:
  shot 1's two clips went from *fail* (0.24, 0.29) to *unverifiable*, and every other verdict was unchanged. Judge
  results are cached by artifact + judge settings, so the scoreboard reused them.

## M3: fixing the small face (FLF @1 vs @2 vs @3, `out/scoreboard/cafe_morning_20261030-205510/`)

Shot 1 was *unverifiable* in every arm because its face is too small in the clip. Two fixes, one arm each:

| Workflow | Accepted | First try | s1 verdict | s2 p10 | s3 p10 | Clip infer | $/accepted s |
|---|---|---|---|---|---|---|---|
| `keyframe_flf@1` (baseline) | 2/3 | 2/3 | unverifiable (0% scorable, all < 64 px) | 0.52 | 0.62 | 20 s | **$0.0116** |
| `keyframe_flf@2`: re-prompt *small* faces for tighter framing | 2/3 | 2/3 | unverifiable (0% scorable) | 0.52 | 0.62 | 20 s | $0.0118 |
| `keyframe_flf@3`: @2 + clips at 1248×720 | 2/3 | 2/3 | **fail** (100% scorable, p10 0.44 / 0.44) | **0.59** | 0.62 | 71 s | $0.0341 |

- **Re-prompting by cause works, but not for this cause here.** The retry now picks its suffix from what blocked
  scoring (`reprompt_by_cause`: small / profile / occluded / no face). For a small face in first-last-frame mode,
  though, both ends of the clip are fixed keyframes, so "the camera pushes in" has nothing to move: s1 stayed 0%
  scorable. A small face has to be fixed upstream, in the keyframe or the resolution.
- **720p makes shot 1 measurable, and it doesn't pass.** All 21 frames scored, and both attempts came in at p10
  0.44. This can't yet tell drift from a face-size effect: at ~80 px the M2 run scored the right person at 0.52 vs
  0.57 at 135 px, so a size-aware threshold (calibration) is the next question, not a lower `min_face_px`.
- **720p costs 3.6× per clip** (71 s vs 20 s warm on H100, for 2.25× the pixels), so $/accepted second roughly
  triples. s2's identity rose (0.52 → 0.59). Worth it for identity-critical wide shots, not as the default.
- **720p first ran out of memory.** Both 14B experts and the text encoder stay on the GPU (~70 of 80 GB), leaving
  too little for the fp32 VAE to encode the conditioning video at 1248×720. The worker now tiles the VAE above
  480p (480p stays untiled, so cached clips reproduce). The failed run cost about $0.33; the re-run billed $0.45
  plus idle tail.

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
