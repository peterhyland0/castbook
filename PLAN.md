# Castbook — project plan

A side project for the Mage (mage.space) Senior AI Infrastructure Engineer role.
Background research: [reports/Mage platform deep dive.md](reports/Mage%20platform%20deep%20dive.md)

## The pitch (what you say to Roi / Greg)

> "You told me Characters across models plus chained workflows is what took off, and you already ship that as Story Studio, Short Drama and the Character Sheet app. The hard part underneath is *knowing* a chain kept the character, and knowing which chain is best for the money. So I built that platform layer as a pipeline service on Modal + FastAPI. It takes a character and a script, runs a versioned multi-model workflow (keyframes → video → stitch), scores every shot for identity drift, and re-rolls shots that drift. Then it A/B tests workflow variants against each other on identity, cost and latency. Here are the side-by-side videos and the scoreboard."

Why it lands with Mage specifically:
- **Mage's own docs admit the problem.** Story Studio says consistency "is less reliable over long sequences". On 5 of their video models you can't use a Character *and* first/last frames in the same generation.
- **No competitor documents output-quality checks or retry-on-drift.** Kling, Runway, Krea, Higgsfield and OpenArt all compete on more canvas and agent features instead.
- **Unlimited plans plus refunds on failed generations** mean every unusable output is GPU spend Mage doesn't get paid for. "$ per accepted second" is a margin metric they'll care about.
- **It copies their API shape:** async `request_id` / `status_url` / `cancel_url`, idempotency keys, a `billing` block. Greg (CTO, likely the interviewer) will recognise his own design.

## Checked in the live product (Peter's account, 2026-10-29)

I clicked through mage.space while signed in: Characters, Models, Agent, API/MCP, Apps, Advanced and the Updates changelog. Nothing was generated and no Gems were spent. What this changes:

1. **Mage already ships the product layer.** The MCP skill `/mage-short-drama` ("scripted vertical dramas with a saved cast who act and speak their lines") is close to Castbook's output. Story Studio, Storyboard and a **Character Sheet app** (Oct 9: one image → face + four full-body views) also exist. → **Don't pitch Castbook as a product.** Pitch it as the *platform layer underneath* Short Drama and Story Studio: measurement, versioned workflows, A/B tests and cost. Mirror their character-sheet format for the sheet step.
2. **The "fruit" models are mostly partner/vendor models, not self-hosted.**
   - The changelog says "we've worked with our partner to lower Gem pricing for the Cherry family".
   - Melon is "developed by one of our partners, and the cost of running them can be unpredictable".
   - Plum is described as having "Seedance 2 and Happy Horse quality".
   - The self-hosted side is open weights: Wan 2.2, LTX, Flux 2, SDXL, Z-Image, Krea 2, Anima, MiniMax H3, plus hundreds of community SDXL checkpoints and imported LoRAs.

   → **Routing one schema across self-hosted GPUs *and* vendor APIs is core to the job.** The vendor-API arm moves from stretch to core.
3. **Serving has two tiers.**
   - **Unlimited** means a "slow" queue at base settings, capped per plan (e.g. Plum Fast: Pro 5 s/480p, Max 15 s/480p).
   - **Fast Mode** is paid in Gems and is "the same model, but powered by multiple premium GPUs" (1×/2×/4× concurrency).

   → **Add a two-lane queue to Castbook:** a cheap, batched, low-priority lane plus a fast multi-GPU lane, with measured latency and cost per lane. This is the JD's "concurrency, autoscaling, latency, and cost" in Mage's own terms.
4. **Real price and latency anchors** come from the Models page, which shows Gem cost and typical generation time for each model:

   | Model | Gems | Typical time | Notes |
   |---|---|---|---|
   | Wan Video 2.2 Fast | 45 | 23 s | 3M plays; self-hosted open weights, the same family Castbook uses |
   | Plum Fast | 173 | 30 s | |
   | Lemon | 245 | 83 s | |
   | Cherry 2 Pro | 618 | 196 s | |
   | Mango 3 | 68 | 28 s | |
   | Nano Banana 2.1 | 51 | 16 s | |
   | Z-Image Turbo | 10 | 3 s | |
   | SDXL community models | 10 | 2–8 s | |

   At ~10k Gems per $10 (from the research; verify), Wan 2.2 Fast sells for about **$0.045 a clip in 23 s**. → **Benchmark Castbook's own Wan 2.2 cost and latency against that number.** If yours is higher, say what Mage must be doing (resolution and frame caps, 4-step distillation, batching, GPU choice). That's a strong interview conversation.
5. **The API and MCP need a payment.** Your account is free tier with 78 Gems. "Keys and connected apps work once your account has a successful payment"; signup Gems are app-only. → Using Mage's API as an arm means buying the smallest Gem pack. That's your call; otherwise use fal for the vendor arm.
6. **Small details worth mirroring:**
   - **"Save Formula"** (saved generation presets) and **Autocreate** (up to 100 variations) in Advanced are the user-facing version of versioned workflows and A/B arms.
   - **`mage-generate` "priced before it runs"** means a cost estimate up front, so Castbook should have an `estimate` endpoint too.
   - **Mage serves MiniMax H3 in the US**, presumably with authorisation. Castbook still shouldn't.

## What Mage's own Agent and Guide said (asked 2026-10-29)

I asked Mage Agent (on its free "Low" setting) to plan a 30 s, 6-shot single-character video *without generating anything*. I asked the Guide assistant about model limits, queues and the API. No Gems were spent. These answers are the strongest evidence for the project.

**1. Mage's own Agent says the gap exists.** Asked whether it detects face drift, it replied: *"There is no built-in face-similarity score and no auto-re-roll loop… nothing in the pipeline compares the rendered shot back to the portrait numerically."* Its QC is a visual checklist the LLM reads off the renders, and it admits that misses mid-clip morphing. It then **recommended exporting frames and running ArcFace/InsightFace outside Mage, calibrating the threshold against your own good shots.** That is Castbook's identity gate, described by their own product. Quote this in the interview.

**2. The Agent's recipe is Castbook's DAG.**

| Step | What it does | Gems |
|---|---|---|
| Character bible | Fixed identity text | free |
| Hero portrait | Mango 3, 2K | 135 |
| Save as `@handle` | | 0 |
| Turnaround sheet | Nano Banana 2.1: front / ¾ / profile / full-body | 51 |
| 6 keyframes | Reference-driven edits of the portrait and sheet, one batched `generateMedia` call | 51 each |
| 6 clips | MiniMax-H3 Turbo 5 s 720p with `first_frame_url` = keyframe | 30 each |
| Stitch | `concat` | 0 |
| Talking shot | Plum with start+end frame, or external TTS + lip sync | 173 for Plum |

- **The quality gate is manual.** The user approves the six stills before any video spend ("a wrong face at 51 gems beats a wrong face at 180").
- **Totals range from ~252 Gems** (lean: GPT Image 2 + H3) **to ~845** (recommended) **to ~4.8k** (Mango + Cherry 2 Pro).
- **The Agent states the H3 limit itself:** start frames and reference images are mutually exclusive, so the keyframe has to go in as the first frame. That's why identity has to be baked into the keyframe.

→ `keyframe_i2v@1` is "Mage Agent's recipe". The scoreboard should run it as the baseline arm and show where the identity gate and FLF beat it.

**3. Retries and failure handling are prose rules the LLM follows, not code.** The Agent described its protocol:
- **Still rendering:** don't re-submit, because "a duplicate submission can produce a divergent take and double the spend". Look the item up in history instead.
- **Hard error:** retry the same item with identical params. On a second failure, degrade once (fewer refs, lower res or duration, or a different model). On a third, fall back to a still + slow push-in.
- **Partial batches:** items succeed independently; re-roll only the failed or flagged item and its dependents. Never re-run the full batch.
- **Escalation:** H3 Turbo (30), then Plum (173), then Cherry Pro (618).

→ Castbook implements this **deterministically in the orchestrator**: idempotency keys stop duplicate submits, the content-addressed cache means only dependents re-run, and the retry ladder is a config (`same → degrade → alternate_model → fallback_shot`) instead of LLM judgement. The pitch is "make your Agent's retry policy code, so it's testable and costs are bounded".

**4. Character + first/last frame conflicts (Guide).**
- **Mutually exclusive:** Lemon, MiniMax-H3/Turbo, Plum/Max/Fast and Melon/Pro. Berry/Berry 2 take up to 9 refs only when no first frame is set.
- **Cherry family:** Characters + one input image + refs, with no first/last-frame inputs.
- **Reference caps:**
  - Cherry 2 Pro: 29 total input images
  - Cherry / Mini / Pro: 8
  - Lemon: 10 + Character
  - Berry: 9
  - H3: 12 refs and a 21 s shared budget
  - Plum: charges per ref after the first 2–5
- → This is what the `ModelAdapter` capability contract has to encode (`max_refs`, `refs_xor_first_frame`, `supports_last_frame`, `ref_cost`). It's also a selling point: the orchestrator picks a valid conditioning plan per model automatically.

**5. Queues (Guide).**
- **Unlimited** (Fast Mode off) is **single-file: one job at a time per user.**
- **Gems mode** runs **1, 2 or 4 concurrent jobs** per user.
- The Guide has no published wait times or queue numbers.
- → In Castbook's two-lane queue, the slow lane is per-user concurrency 1 on cheap capacity; the fast lane is per-user concurrency N on premium GPUs. Measure the fairness/latency trade-off.

**6. API.** The Guide had no information on webhooks or rate limits, and says app-side bots are banned ("automation is meant to go through the API"). Ask Greg whether webhooks are planned. Castbook should offer both polling and an optional webhook.

**7. The Guide is itself a tool-using agent.** It runs "Found relevant Mage docs", "Checked model info" and "Checked membership info". Their docs and model metadata are queryable by tools, so the same model-capability data could drive routing.

## Alternatives considered

| Idea | Verdict |
|---|---|
| **Castbook: identity-gated, versioned workflow pipeline + A/B harness** | **Pick.** Covers almost every line of the JD and is literally "chain workflows, test variants". |
| Model-onboarding harness (adapter + CI eval + cold-start benchmarks) | Folded into Castbook as milestone M4. Too narrow on its own. |
| Character "compiler": one character pack → each model's input format | Folded in as the `ModelAdapter` capability layer. |
| Node-canvas UI or chat-to-video agent | Skip. Crowded (Runway, Krea, Figma Weave, Mage Agent itself) and it's a frontend story, not infra. |

## What the demo looks like

1. **A 30–40 s video** of one generated character across 6 shots: different scenes, angles and lighting, with the same face.
2. **A run viewer** (a plain HTML page): the DAG for a run, each shot's attempts, identity scores per attempt, which ones were re-rolled and why, and GPU-seconds and $ per step.
3. **An A/B scoreboard:** the same script and character through 3–4 workflow versions, side by side.

   | Workflow | ArcFace p10 | DINOv2 body | Judge | p50 latency | $/run | **$/accepted-sec** |
   |---|---|---|---|---|---|---|

4. **A cold-start table:** before and after memory snapshots, per model.
5. **A CI run** that onboards a new model adapter and fails it on an identity or latency regression.

## Architecture

```
            ┌──────────────── FastAPI (Modal asgi_app, CPU, @concurrent) ────────────────┐
 client ──▶ │ POST /v1/characters   POST /v1/workflows/{id}/runs   GET /v1/runs/{id}     │
            │ idempotency keys · request_id/status_url/cancel_url · billing block        │
            └──────────────┬──────────────────────────────────────────────────────────────┘
                           │ spawn
                  ┌────────▼─────────┐   job + step state    ┌──────────────┐
                  │ Orchestrator      │◀────────────────────▶│ Postgres      │
                  │ (CPU Modal fn)    │                       │ (Neon/CloudSQL)│
                  │ walks DAG, gates, │   content-addressed   ┌──────────────┐
                  │ retries, budgets  │◀────────────────────▶│ GCS artifacts │
                  └──┬─────┬─────┬───┘   key=sha256(step,    └──────────────┘
                     │     │     │        model@rev,params,inputs,seed)
         .spawn()    │     │     │
   ┌─────────────────▼┐ ┌──▼──────────────┐ ┌▼───────────────────┐ ┌──────────────────┐
   │ KeyframeWorker    │ │ VideoWorker      │ │ JudgeWorker         │ │ Provider adapters │
   │ Qwen-Image-Edit   │ │ Wan 2.2 I2V/FLF  │ │ InsightFace ArcFace │ │ fal / Mage API /  │
   │ -2511 (H100)      │ │ +LightX2V (H100) │ │ DINOv2, NSFW (L4)   │ │ Nano Banana       │
   └───────────────────┘ └──────────────────┘ └─────────────────────┘ └──────────────────┘
        weights in modal.Volume · @modal.enter load · memory snapshots · max_containers caps
```

Key decisions:
- **One `@app.cls` per model family, sized to VRAM.** The API and orchestrator are CPU-only and scale independently of the GPU workers.
- **Hand-rolled durable steps** (a Postgres step table plus the artifact cache), not Temporal. It's enough for this scale, and you can say why: HeyGen uses Temporal at millions of workflows a day, and this design is the step before that.
- **Content-addressed artifacts.** A cache hit means the step is skipped, which gives free resume after failure and cheap single-shot edits. A/B arms also share upstream work (the character sheet and keyframes) automatically.
- **Per-shot status.** One failed shot degrades the job; it doesn't fail it.

## Workflows are versioned config

```yaml
# workflows/keyframe_flf@3.yaml — immutable once used in a run
id: keyframe_flf
version: 3
steps:
  sheet:    { model: qwen-image-edit-2511, params: { views: [front, 3q_left, 3q_right, full_body] } }
  plan:     { model: claude-sonnet-5-5, params: { shots: 6 } }          # LLM shot planner → typed shot specs
  keyframe: { model: qwen-image-edit-2511, for_each: shot_boundary, inputs: [sheet, shot.spec], gate: identity }
  clip:     { model: wan2.2-i2v-a14b, for_each: shot, mode: flf, params: { steps: 4, lora: lightx2v }, gate: identity }
  stitch:   { model: ffmpeg }
gates:
  identity: { metric: arcface_p10, min: calibrated, max_retries: 2, on_fail: keep_best }
budget:     { max_usd: 3.00 }
```

The A/B arms for the first scoreboard (each one tests a real trade-off):

| Arm | What it tests |
|---|---|
| `lastframe_chain@1` | Baseline: chain each clip off the previous clip's last frame. Expected to drift; shows why the rest exist. |
| `keyframe_i2v@1` | Keyframe per shot, then I2V from the start frame only. **This is Mage Agent's own recipe**, so it's the baseline to beat. |
| `keyframe_flf@3` | Keyframes at both ends, then first/last-frame interpolation. Re-anchors identity at every boundary. |
| `keyframe_flf_full@1` | Same as above with full 40-step Wan instead of 4-step distilled. Distillation is known to weaken identity; is the 20× cost worth it? |
| `api_arm@1` | The same plan through a vendor API (a hosted video model via fal, or Mage's own API if you buy Gems). Self-hosted vs vendor: $ vs quality. This mirrors how Mage mixes its own GPUs with partner models. |

## Model choices (v1)

| Step | Model | Why |
|---|---|---|
| Character sheet + keyframes | Qwen-Image-Edit-2511 (+ Lightning LoRA) | Best open multi-reference editor for identity; Apache-2.0 |
| Video | Wan 2.2 I2V-A14B, FLF2V mode, LightX2V 4-step | Newest open Wan; Mage serves Wan 2.2 too |
| Alt video (M4 onboarding demo) | LTX-2 | Open, joint audio+video. Shows "add a model" is an adapter + CI pass |
| Shot planner | Claude (`claude-sonnet-5-5`) | Script → typed shot specs (subject, framing, action, start/end state) |
| Identity judge | InsightFace ArcFace (buffalo_l) + DINOv2 | Face-ID cosine to the character embedding; DINOv2 catches outfit/body drift |
| Quality judge (M3) | VLM rubric (Claude vision) | Prompt adherence, artifacts |
| Moderation | NSFW image classifier + LLM prompt check | Three gates: prompt, reference upload, sampled output frames |
| TTS / lip sync (M5) | Chatterbox TTS (Modal example) + LatentSync 1.6 | Optional talking shot |

Avoid MiniMax H3: its license bars US deployment without written permission. Use only **generated** characters in the demo, never real people (matches Mage's likeness rules).

## Repo layout

```
castbook/
  api/            FastAPI app: routes, schemas (pydantic), idempotency, billing
  orchestrator/   DAG walker, gates, retry/backoff policy, budget guard
  workers/        modal.cls per model family (keyframe, video, judge, tts)
  adapters/       ModelAdapter interface + one file per model/provider
  store/          GCS artifact cache (content-addressed), Postgres models/migrations
  workflows/      versioned YAML configs
  evals/          golden set (5 characters × 10 shot specs), A/B runner, report generator
  viewer/         static HTML run viewer + scoreboard
  tests/          pytest: DAG semantics, cache keys, retry policy, adapter contract
.github/workflows/  lint + unit tests; adapter-eval job on adapters/** changes
```

## Milestones

**M0: Setup (½ day)**
- [x] Modal project, Volume for weights (GCS bucket + Postgres deferred to M2: no gcloud CLI on this machine yet)
- [x] Download Qwen-Image-Edit-2511, Wan 2.2 I2V A14B and LightX2V LoRA to the Volume
- [x] Generate 5 original characters (portraits) for the golden set (Z-Image Turbo)

**M1: Single shot end to end (2–3 days)**
- [x] `KeyframeWorker` + `VideoWorker` as `@app.cls` with `@modal.enter` loading
- [x] `JudgeWorker`: ArcFace per sampled frame vs the character embedding → min / p10 / mean
- [x] Make the judge pose-aware: skip frames past 45° yaw and report a profile rate (`single_shot@2`; clip min 0.01 → 0.61 on the same cached clip)
- [x] Gate verdicts: pass / fail / *unverifiable* (scorable coverage below 50%) plus a hand-on-face occlusion check (`single_shot@3`). Positive control: a pasted hand turns a 0.71 pass into *unverifiable* instead of a false fail.
- [ ] Calibrate `min_score`, `min_coverage` and `max_hand_overlap` on ~100 hand-labeled frames (M3); all three are provisional.
- [x] One shot: portrait + prompt → keyframe → 5 s clip → identity score
- [x] Log GPU-seconds and $ per step (first run: $0.34, of which $0.025 is warm clip inference; see README)

**M2: Multi-shot pipeline + identity gate + API (4–5 days)**
- [x] Workflow YAML loader, DAG walker with threaded fan-out (shots in parallel; each GPU pool capped at 1 container), run state in a modal.Dict (Postgres later)
- [x] Content-addressed cache with resume (tested: a rerun is all cache hits, a partial run only computes the missing shot). Still a Modal Volume; GCS later
- [x] Identity gate with bounded re-roll (new seed); re-prompt on *unverifiable*; keep best attempt on exhaustion (real run: 1 keyframe re-rolled twice, 1 clip re-prompted to a pass)
- [x] ffmpeg stitch (concat, no re-encode)
- [ ] Shot planner (Claude) → typed shot specs. Needs an Anthropic API key; scripts are hand-written for now
- [x] Minimum face size: frames with a face narrower than 64 px are *unverifiable*, not *fail* (`keyframe_i2v@2`; re-judged on CPU, the M2 wide shot's false fails became *unverifiable*)
- [x] Re-prompt by reason (`reprompt_by_cause`) and a 720p clip arm (`keyframe_flf@2`, `@3`): the re-prompt can't move a face pinned by both FLF keyframes; 720p made s1 scorable (it fails, p10 0.44) at 3.6× clip cost; VAE tiled above 480p after an OOM
- [ ] Size-aware gate: calibrate p10 against face width on labeled frames before trusting verdicts on wide shots (s1 with every frame above 64 px still scored 0.43–0.48, so size isn't the whole story there)
- [x] Small-face fix upstream (`keyframe_flf@4`, `framing`): predict the clip's face from the keyframe, re-frame there, pick clip size per shot. s1 re-framed 79 → 244 px for ~$0.003 and scored at 480p (fails: drift, not size)
- [x] Re-framing keeps the shot coherent (`keyframe_flf@5`, `framing.camera`): scripts declare each shot's `camera` (closer / wider / steady); the end keyframe's face size is checked against the start's and re-framed on a reversal, and a re-framed start prompts the end relative to it. Ran it: the check flagged all 5 of s1's end keyframes (244 → ~120 px on a `closer` beat), but the relative re-prompt barely moved them (108 → 121 px), because the script's absolute "waist-up" end text wins
- [ ] Re-framed end that won't agree: drop the script's absolute end framing for a re-framed start (planner writes a relative end), or degrade the shot to start-frame-only I2V
- [ ] Shot 1 drift: all frames scorable, p10 0.43–0.48 at both sizes; try more clip attempts, a different seed range, or a calmer motion prompt, and look at per-frame similarity over time
- [x] FastAPI: characters, runs, status, cancel, result, estimate; idempotency keys; billing block; bearer auth (tested locally; not deployed)
- [ ] Retry policy:
  - transient (Modal retries), 429/5xx (backoff), OOM (drop resolution)
  - a per-shot ladder as config: `same → degrade (fewer refs / lower res) → alternate_model → fallback_shot`, mirroring Mage Agent's prose protocol
  - never re-submit an in-flight job
- [ ] Three moderation gates
- **Checkpoint:** a 30 s, 6-shot video from one API call. This is the minimum to show.

**M3: A/B harness + scoreboard (2–3 days)**
- [ ] Calibrate the ArcFace threshold on ~100 hand-labeled shots (same/different); plot it
- [x] First scoreboard: 3 arms (`keyframe_i2v@2`, `lastframe_chain@1`, `keyframe_flf@1`) × 1 character × 3 shots, $/accepted-second (FLF 2/3 accepted first try at $0.0116/s; last-frame chain 0/3; see README)
- [ ] Run the arms × the full golden set and several seeds, so the comparison has more than two scorable shots per arm
- [x] Static scoreboard page: metrics table, side-by-side final videos, per-shot verdicts (`castbook/scoreboard.py`)
- [ ] Viewer for one multi-shot run: DAG, every attempt, per-frame identity

**M4: Model onboarding + infra numbers (2 days)**
- [ ] `ModelAdapter` capability contract: `max_refs`, `refs_xor_first_frame`, `supports_last_frame`, `max_duration`, `audio`, `ref_cost`, seeded from the Guide's answers. The orchestrator picks a valid conditioning plan per model.
- [ ] Add LTX-2 as a new adapter; GitHub Actions eval job that fails on regression
- [ ] Memory snapshots on the workers; before/after cold-start table
- [ ] Autoscaling knobs (`min_containers`, `scaledown_window`, `max_containers`) with a short written rationale
- [ ] Two-lane queue, mirroring Mage's Unlimited vs Fast Mode:
  - a slow lane: cheap GPU, batched, low priority, tier caps on duration/resolution
  - a fast lane: H100, higher concurrency, optionally multi-GPU sequence-parallel
  - measure p50/p95 latency and $/clip per lane
- [ ] `POST /v1/estimate`: price a run before it starts, like `mage-generate`
- [ ] Benchmark self-hosted Wan 2.2 $/clip and latency against Mage's listed 45 Gems / 23 s

**M5: Stretch**
- [ ] Talking shot: Chatterbox TTS + LatentSync
- [ ] Mage API as a provider adapter (needs a Gem purchase on your account)
- [ ] A short write-up / blog post with the scoreboard

M0–M2 is about 1.5 weeks of evenings. M3 is what makes it a story. Prioritise M3 over polish.

## Budget (rough; verify as you go)

- **H100 on Modal is about $3.95/hr.** A 4-step Wan 2.2 clip is estimated at $0.07–0.20; the full 40-step version is about $1–2. These are unverified estimates, and measuring them is part of the project.
- **One 6-shot run with re-rolls:** roughly $1–3 distilled.
- **The scoreboard** (4 arms × 5 characters, with the full-step arm on fewer characters): roughly $60–150.
- **Total:** plan for about $150–250 of Modal spend. Set `max_containers` and the per-run `budget.max_usd` guard from day one.

## Risks

- **Wan 2.2 FLF identity may already be good enough** that the gate rarely fires. That's still a result ("the gate fired on 8% of shots; here's the cost of that"). The last-frame-chain baseline guarantees visible drift for contrast.
- **ArcFace on stylised or anime characters is unreliable.** Keep the golden set photoreal or semi-real, and report DINOv2 alongside.
- **Cold-start and weight-loading time on 14B video models** will eat iteration time. Use snapshots early, and keep a `min_containers=0` default for cost.

## Talking points + questions for the interview

Talking points:
- Identity as a number. Workflows as versioned, comparable artifacts. Models onboarded through a tested adapter instead of a one-off integration.
- $/accepted-second as the metric that joins quality and margin under unlimited plans.

Questions for Greg:
- The changelog says partners run Cherry and Melon. How much of the video traffic goes to partner APIs vs your own GPUs, and how do you route and fail over between them?
- Is Fast Mode's "multiple premium GPUs" sequence parallelism (xDiT-style), or just a dedicated pool? How is the slow Unlimited lane scheduled?
- Is the GPU fleet all on Modal, or split across providers?
- How do you cache weights and LoRAs across the long-tail catalog?
- How is moderation staged?
- Do you score identity internally today?
