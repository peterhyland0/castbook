"""Public demo site: one page that shows what Castbook does, built from saved runs under out/.

    uv run python -m castbook.site            # -> site/index.html (+ site/media, site/deep)

The page reads the same records the scoreboard and run viewer read, so every number on it is computed
from a real run (the prose around the numbers is written by hand). Media are copied next to the page
rather than embedded. The deep-dive pages are the existing self-contained scoreboard and run pages, with
their embedded media moved out to content-addressed files, so a clip shown on three pages is stored once.
The build writes to a temporary directory and replaces `site/` only when it finishes, so a missing run
leaves the previous build in place. `site/` is build output (gitignored) and deploys as plain static files.
"""

import base64
import hashlib
import html
import json
import re
import shutil
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

from castbook.config import GPU_USD_PER_SECOND
from castbook.dag import judge_config
from castbook.runs import estimate
from castbook.scoreboard import summarize
from castbook.viewer import CSS, chart_script, identity_chart_svg
from castbook.workflow import load_workflow

OUT = Path("out")
SITE = Path("site")
REPO = "https://github.com/peterhyland0/castbook"

# The runs the page is built from. Each is a real run directory under out/.
ARMS_RUN = OUT / "scoreboard/cafe_morning_20261030-181634"  # 3 chain types, same script
FRAMING_RUN = OUT / "scoreboard/cafe_morning_20261103-182431"  # small-face fixes: @2 / @3 / @4
POSE_RUN = OUT / "runs/20261030T024303-676f72"  # single_shot@3: pose- and occlusion-aware judge
FIRST_RUN = OUT / "runs/20261030T014009-ba3d2d"  # single_shot@1: first run, all frames scored
FRAMING_ARMS = ["keyframe_flf@2", "keyframe_flf@3", "keyframe_flf@4"]  # 480p, 720p, re-framed keyframe
REFRAMED_ARM = "keyframe_flf@4"

ARM_ORDER = ["keyframe_i2v@2", "keyframe_flf@1", "lastframe_chain@1"]
ARM_LABEL = {
    "keyframe_i2v@2": "Keyframe → video (an agent's usual recipe)",
    "keyframe_flf@1": "Start + end keyframes → first/last-frame video",
    "lastframe_chain@1": "Chain each clip off the last frame",
}

PAGE_CSS = """
.hero { display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; align-items: center; margin: 8px 0 20px; }
.hero h1 { font-size: 28px; line-height: 1.2; margin: 0 0 10px; }
.hero p { color: var(--text-secondary); font-size: 15px; margin: 0 0 10px; }
.hero .links a { margin-right: 14px; font-weight: 600; }
.portrait { display: flex; gap: 12px; align-items: center; }
.portrait img { width: 96px; height: 96px; object-fit: cover; border-radius: 8px; }
.portrait p { font-size: 12px; color: var(--text-muted); margin: 0; }
.trio { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.trio figure, .pair figure { margin: 0; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pair img { width: 100%; border-radius: 6px; display: block; }
.lede { color: var(--text-secondary); margin: -4px 0 12px; }
.take { border-left: 3px solid var(--series-1); padding: 2px 0 2px 12px; margin: 12px 0 0; }
td.win { font-weight: 700; color: var(--good-ink); }
.scroll { overflow-x: auto; }
pre { background: var(--surface-0); border: 1px solid var(--border); border-radius: 8px; padding: 12px;
  overflow-x: auto; font-size: 12px; line-height: 1.45; margin: 0; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
ol.steps { margin: 0; padding-left: 20px; } ol.steps li { margin-bottom: 6px; }
.chart-row { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; align-items: start; }
footer { color: var(--text-muted); font-size: 12px; margin-top: 24px; }
.hero > *, .trio > *, .pair > *, .cols > *, .chart-row > *, .stats > * { min-width: 0; }
code { overflow-wrap: anywhere; }
button { font: inherit; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--surface-0); color: var(--text-primary); cursor: pointer; }
@media (max-width: 760px) {
  .hero, .trio, .pair, .cols, .chart-row { grid-template-columns: 1fr; }
}
"""


def _arms(run_dir: Path) -> dict[str, dict]:
    """Scoreboard summaries keyed by workflow, re-summarized from each arm's saved record."""
    summary = json.loads((run_dir / "summary.json").read_text())
    out = {}
    for arm in summary["arms"]:
        record = run_dir / arm["workflow"] / "record.json"
        out[arm["workflow"]] = summarize(json.loads(record.read_text())) if record.exists() else arm
    return out


def _record(run_dir: Path, workflow: str | None = None) -> dict:
    path = run_dir / workflow / "record.json" if workflow else run_dir / "record.json"
    if not path.exists():
        raise FileNotFoundError(f"site: missing run record {path}")
    return json.loads(path.read_text())


def _warm_infer_s(attempts: list[dict]) -> dict[str, float]:
    """Warm inference seconds by artifact key (an artifact shared between arms is counted once)."""
    return {a["key"]: a["timing"]["infer_s"] for a in attempts if a.get("timing") and not a["timing"].get("cold")}


def warm_clip_ratio(records: dict[str, dict]) -> float:
    """Median warm clip inference at the largest clip width over the smallest, across the given arms."""
    by_width: dict[int, dict[str, float]] = {}
    for workflow, record in records.items():
        default = load_workflow(workflow).steps["clip"].params["width"]
        for shot in record["shots"]:
            width = (shot.get("clip_size") or [default])[0]
            by_width.setdefault(width, {}).update(_warm_infer_s(shot["clip_attempts"]))
    widths = [w for w, t in by_width.items() if t]
    if len(widths) < 2:
        raise ValueError("site: need warm clips at two sizes to compare clip cost")
    med = {w: statistics.median(by_width[w].values()) for w in widths}
    return med[max(widths)] / med[min(widths)]


def warm_keyframe_usd(records: dict[str, dict]) -> float:
    """Median warm keyframe inference across the given arms, in $ on the GPU it ran on."""
    timings: dict[str, dict] = {}
    for record in records.values():
        for shot in record["shots"]:
            for a in shot["keyframe_attempts"] + shot.get("end_keyframe_attempts", []):
                if a.get("timing") and not a["timing"].get("cold"):
                    timings[a["key"]] = a["timing"]
    if not timings:
        raise ValueError("site: no warm keyframe timings")
    return statistics.median(t["infer_s"] * GPU_USD_PER_SECOND[t["gpu"]] for t in timings.values())


def reframe_pair(shot: dict) -> tuple[dict, dict]:
    """(before, after) for a shot whose start keyframe was re-framed: the chosen keyframe, and the last attempt
    before it that the framing check flagged as too small."""
    attempts = shot["keyframe_attempts"]
    after = next((a for a in attempts if a["key"] == shot["keyframe_key"]), None)
    if after is None:
        raise ValueError(f"site: shot {shot['shot_id']} has no chosen keyframe")
    small = [a for a in attempts if a["framing"] == "small" and a["n"] < after["n"]]
    if not small:
        raise ValueError(f"site: shot {shot['shot_id']} was not re-framed")
    return small[-1], after


def run_dates(paths: list[Path]) -> str:
    """'Oct 30 – Nov 3, 2026' from the yyyymmdd stamp in each run directory's name (UTC)."""
    days = sorted(datetime.strptime(m.group(1), "%Y%m%d") for p in paths if (m := re.search(r"(20\d{6})", p.name)))
    if not days:
        raise ValueError("site: no dated run directories")
    lo, hi = days[0], days[-1]
    if lo == hi:
        return f"{lo:%b} {lo.day}, {lo.year}"
    return f"{lo:%b} {lo.day} – {hi:%b} {hi.day}, {hi.year}"


_DATA_URI = re.compile(r"data:(video/mp4|image/png|image/jpeg);base64,([A-Za-z0-9+/=]+)")
_EXT = {"video/mp4": "mp4", "image/png": "png", "image/jpeg": "jpg"}


class Media:
    """Files under `<site>/media`, stored once per content: copying the same bytes twice returns the first path."""

    def __init__(self, site: Path):
        self.site, self.paths = site, {}

    def put(self, data: bytes, name: str) -> str:
        """Write `data` as media/<name> unless the same bytes are already stored; return the path used."""
        digest = hashlib.sha256(data).hexdigest()
        if digest not in self.paths:
            dst = self.site / "media" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            self.paths[digest] = f"media/{name}"
        return self.paths[digest]

    def copy(self, src: Path, name: str) -> str:
        return self.put(src.read_bytes(), name)

    def externalize(self, page: str, depth: int = 1) -> str:
        """Replace a self-contained page's base64 media with links to stored files (`depth` dirs below site/)."""

        def sub(m: re.Match) -> str:
            data = base64.b64decode(m.group(2))
            name = f"{hashlib.sha256(data).hexdigest()[:16]}.{_EXT[m.group(1)]}"
            return "../" * depth + self.put(data, name)

        return _DATA_URI.sub(sub, page)


def _jpg(src: Path, dst: Path, width: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale={width}:-2", "-q:v", "3", str(dst)],
        check=True,
    )


def _usd(v: float | None, digits: int = 3) -> str:
    return "–" if v is None else f"${v:.{digits}f}"


def _p(v: float | None) -> str:
    return "–" if v is None else f"{v:.2f}"


def _arms_table(arms: list[dict], cols: list[tuple[str, str, bool | None]]) -> str:
    """cols: (summary key, header, lower_is_better or None for no highlight)."""
    head = "".join(f'<th class="num">{h}</th>' for _, h, _ in cols)
    best = {}
    for key, _, lower in cols:
        vals = [a[key] for a in arms if a[key] is not None]
        if lower is not None and vals:
            best[key] = min(vals) if lower else max(vals)
    rows = []
    for a in arms:
        cells = []
        for key, _, _ in cols:
            v = a[key]
            if key in ("accepted", "first_try"):
                text = f"{v}/{a['n_shots']}"
            elif key in ("min_p10", "mean_p10"):
                text = _p(v)
            elif key == "usd_per_accepted_s":
                text = _usd(v, 4)
            elif key == "warm_usd":
                text = _usd(v)
            else:
                text = str(v)
            win = key in best and v == best[key]
            cells.append(f'<td class="num{" win" if win else ""}">{text}</td>')
        rows.append(f"<tr><td><code>{html.escape(a['workflow'])}</code></td>{''.join(cells)}</tr>")
    return (
        f'<div class="scroll"><table><thead><tr><th>Workflow</th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def build(site: Path = SITE) -> Path:
    """Build into a temporary sibling of `site`, then swap it in; on any error `site` is left as it was."""
    tmp = site.with_name(f".{site.name}.building")
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        _build(tmp)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if site.exists():
        shutil.rmtree(site)
    tmp.rename(site)
    return site / "index.html"


def _build(site: Path) -> None:
    # --- data (read and checked before anything is written) -----------------------------------
    arms = _arms(ARMS_RUN)
    trio = [arms[w] for w in ARM_ORDER]
    framing = _arms(FRAMING_RUN)
    framing_arms = [framing[w] for w in FRAMING_ARMS]
    flf, i2v = arms["keyframe_flf@1"], arms["keyframe_i2v@2"]
    gate = judge_config(load_workflow(i2v["workflow"]))["gate"]
    judge_min_face = judge_config(load_workflow(REFRAMED_ARM))["min_face_px"]

    pose = _record(POSE_RUN)
    first = _record(FIRST_RUN)
    pose_wf = load_workflow(pose["workflow"])
    fps = pose_wf.steps["clip"].params["fps"]
    pose_clip_step = next(s for s in pose["steps"] if s["step"] == "clip")
    n_frames = pose_clip_step.get("n_frames", pose_wf.steps["clip"].params["num_frames"])
    per_frame = pose["identity"]["clip_per_frame"]
    pose_clip, first_clip = pose["identity"]["clip"], first["identity"]["clip"]

    first_clip_step = next(s for s in first["steps"] if s["step"] == "clip")
    first_kf_step = next(s for s in first["steps"] if s["step"] == "keyframe")
    clip_t, kf_t = first_clip_step["timings"][0], first_kf_step["timings"][0]
    warm_clip_usd = clip_t["infer_s"] * GPU_USD_PER_SECOND[clip_t["gpu"]]
    first_clip_params = load_workflow(first["workflow"]).steps["clip"].params

    framing_records = {w: _record(FRAMING_RUN, w) for w in FRAMING_ARMS}
    clip_ratio = warm_clip_ratio(framing_records)
    kf_usd = warm_keyframe_usd(framing_records)
    reframed = framing_records[REFRAMED_ARM]["shots"][0]
    kf_before, kf_after = reframe_pair(reframed)
    reframed_wf = load_workflow(REFRAMED_ARM)
    kf_width = reframed_wf.steps["keyframe"].params["width"]
    small_clip_w, small_clip_h = reframed_wf.framing.clip_sizes[0]
    large_clip_h = reframed_wf.framing.clip_sizes[-1][1]
    before_clip_face = kf_before["face_px"] * small_clip_w / kf_width
    shot_dir = FRAMING_RUN / REFRAMED_ARM / reframed["shot_id"]
    stills = {
        "before": shot_dir / f"keyframe_{kf_before['n']}.png",
        "after": shot_dir / f"keyframe_{kf_after['n']}.png",
        "portrait": OUT / f"golden/{first['character']}.png",
    }
    deep_pages = {
        "scoreboard-chains.html": ARMS_RUN / "index.html",
        "scoreboard-framing.html": FRAMING_RUN / "index.html",
        "run-pose-aware.html": POSE_RUN / "index.html",
    }
    sources = [*stills.values(), *deep_pages.values(), POSE_RUN / "clip.mp4"]
    sources += [ARMS_RUN / w / "final.mp4" for w in ARM_ORDER]
    missing = [str(p) for p in sources if not p.exists()]
    if missing:
        raise FileNotFoundError(f"site: missing inputs {missing}")
    dates = run_dates([ARMS_RUN, FRAMING_RUN, POSE_RUN, FIRST_RUN])

    # --- media --------------------------------------------------------------------------------
    media = Media(site)
    arm_video = {w: media.copy(ARMS_RUN / w / "final.mp4", f"{w.replace('@', '-')}.mp4") for w in ARM_ORDER}
    pose_video = media.copy(POSE_RUN / "clip.mp4", "pose-clip.mp4")
    _jpg(stills["portrait"], site / "media/c01.jpg", 256)
    _jpg(stills["before"], site / "media/s1-before.jpg", 800)
    _jpg(stills["after"], site / "media/s1-after.jpg", 800)
    for name, src in deep_pages.items():
        (site / "deep").mkdir(parents=True, exist_ok=True)
        (site / "deep" / name).write_text(media.externalize(src.read_text()))

    # --- page ---------------------------------------------------------------------------------
    videos = "".join(
        f'<figure><video src="{arm_video[a["workflow"]]}" muted playsinline loop controls autoplay '
        f'preload="auto"></video><figcaption><b>{html.escape(ARM_LABEL[a["workflow"]])}</b><br>'
        f"<code>{html.escape(a['workflow'])}</code> · {a['accepted']}/{a['n_shots']} shots passed the identity gate"
        "</figcaption></figure>"
        for a in trio
    )
    trio_table = _arms_table(
        trio,
        [
            ("accepted", "Accepted", False),
            ("first_try", "First try", False),
            ("min_p10", "Min p10", False),
            ("n_attempts", "Attempts", None),
            ("warm_usd", "Warm $", True),
            ("usd_per_accepted_s", "$ / accepted s", True),
        ],
    )
    framing_table = _arms_table(
        framing_arms,
        [
            ("accepted", "Accepted", None),
            ("warm_usd", "Warm $", True),
            ("usd_per_accepted_s", "$ / accepted s", True),
        ],
    )
    s1_2, s1_3, s1_4 = (framing[w]["shots"][0] for w in FRAMING_ARMS)
    api_wf, api_shots = "keyframe_flf@4", 3
    api_est = estimate(load_workflow(api_wf), api_shots)

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Castbook</title>
<meta name="description" content="Identity-gated, versioned multi-model video pipelines on Modal.">
<style>{CSS}{PAGE_CSS}</style></head><body><main>

<section class="hero">
  <div>
    <h1>Did the chained workflow keep the character?</h1>
    <p><b>Castbook</b> chains open-weights models (keyframe → video → stitch) on Modal GPUs, scores every shot
    against the character's face, re-rolls the shots that drift, and records what each step cost. Workflows are
    versioned configs, so two recipes can be run on the same script and compared on identity, retries and
    <b>dollars per accepted second of video</b>.</p>
    <p class="links"><a href="{REPO}">Code on GitHub</a><a href="#how">How it works</a>
      <a href="#next">What's next</a></p>
  </div>
  <div class="portrait"><img src="media/c01.jpg" alt="Generated character portrait c01">
    <p>Character <code>c01</code>: one generated, front-facing portrait (no real people). Every score below is
    ArcFace similarity to this face.</p></div>
</section>

<div class="stats">
  <div class="stat"><div class="label">Shots passed first try</div>
    <div class="value">{flf["first_try"]}/{flf["n_shots"]} vs {i2v["first_try"]}/{i2v["n_shots"]}</div>
    <div class="sub">first/last-frame vs keyframe → video</div></div>
  <div class="stat"><div class="label">Cost per accepted second</div>
    <div class="value">{_usd(flf["usd_per_accepted_s"], 4)}</div>
    <div class="sub">warm H100 time, every attempt counted</div></div>
  <div class="stat"><div class="label">One 5 s Wan 2.2 clip, warm</div>
    <div class="value">{_usd(warm_clip_usd)}</div>
    <div class="sub">{clip_t["infer_s"]:.0f} s inference · {first_clip_params["width"]}×{first_clip_params["height"]}
    · 4-step</div></div>
  <div class="stat"><div class="label">Fixing a too-small face</div>
    <div class="value">~{_usd(kf_usd)}</div>
    <div class="sub">one re-framed keyframe, vs {clip_ratio:.1f}× clip cost at {large_clip_h}p</div></div>
</div>

<div class="card">
  <h2>Same script, same character, three ways to chain it</h2>
  <p class="lede">A 3-shot script (a street at dawn, a café counter, a café window) through three workflow
  versions. Each shot's clip must pass the identity gate: {gate["metric"]} similarity ≥ {gate["min_score"]} over
  the frames that can be scored.</p>
  <div class="trio">{videos}</div>
  <p class="hint"><button id="play">Play all three from the start</button></p>
  {trio_table}
  <p class="take"><b>Chaining off the last frame can't change scenes.</b> Shots 2 and 3 never reach the café: in
  the "café window" shot she's still on the street. Its faces stay too small to verify, so nothing ships.
  <b>Re-anchoring with start and end keyframes beat the usual keyframe → video recipe:</b> both verifiable shots
  passed on the first try, identity was higher, and cost per accepted second was
  {(1 - flf["usd_per_accepted_s"] / i2v["usd_per_accepted_s"]):.0%} lower even with an extra keyframe per shot,
  because no clip had to be re-rolled. One character and one seed, so read it as a direction, not a result.
  <a href="deep/scoreboard-chains.html">Full scoreboard →</a></p>
</div>

<div class="card">
  <h2>A number you can trust, and knowing when you can't</h2>
  <p class="lede">The first run scored every frame and got a clip mean of {_p(first_clip["mean"])}, min
  {_p(first_clip["min"])}: it looked like the face drifted. It mostly hadn't. She turns toward a window, and
  ArcFace collapses on profiles even for the right person. The judge now leaves out frames turned past
  {pose_clip["max_yaw"]:.0f}°, frames with a hand over the face, and faces under {judge_min_face:.0f} px, and returns
  <b>pass</b>, <b>fail</b> or <b>unverifiable</b> instead of a misleading low score.</p>
  <div class="chart-row">
    <figure style="margin:0"><video id="clip" src="{pose_video}" controls loop muted playsinline></video>
      <figcaption>Same clip, re-judged on CPU (no GPU, $0): mean {_p(first_clip["mean"])} →
      {_p(pose_clip["mean"])}, min {_p(first_clip["min"])} → {_p(pose_clip["min"])},
      {pose_clip["profile_rate"]:.0%} of frames profile.</figcaption></figure>
    <div class="chart-wrap">{identity_chart_svg(per_frame, n_frames, pose["identity"]["keyframe"]["mean"])}
      <div class="tooltip" id="tip"></div>
      <p class="hint">Similarity per sampled frame. Shaded frames are profile and not scored; diamonds mark a hand
      on the face. Hover for values, click to seek. <a href="deep/run-pose-aware.html">Run page →</a></p></div>
  </div>
</div>

<div class="card">
  <h2>Fix it at the cheap step</h2>
  <p class="lede">Shot 1's face was {kf_before["face_px"]:.0f} px wide in the keyframe, about
  {before_clip_face:.0f} px in the {small_clip_h}p clip, so every frame was unverifiable. Rendering clips at
  {large_clip_h}p made it measurable, but at {clip_ratio:.1f}× the clip cost. The framing check predicts the clip's
  face size from the keyframe and re-frames <i>the keyframe</i> instead, for about {_usd(kf_usd)}.</p>
  <div class="pair">
    <figure><img src="media/s1-before.jpg" alt="Wide keyframe, small face"><figcaption>Before: face
      {kf_before["face_px"]:.0f} px, keyframe identity {_p(kf_before["verdict"]["value"])}</figcaption></figure>
    <figure><img src="media/s1-after.jpg" alt="Re-framed keyframe, large face"><figcaption>After one re-frame:
      face {kf_after["face_px"]:.0f} px, keyframe identity {_p(kf_after["verdict"]["value"])}</figcaption></figure>
  </div>
  {framing_table}
  <p class="take">Shot 1 in each: <code>@2</code> {s1_2["clip_status"]} ({s1_2["coverage"]:.0%} scorable),
  <code>@3</code> {s1_3["clip_status"]} at p10 {_p(s1_3["clip_p10"])},
  <code>@4</code> {s1_4["clip_status"]} at p10 {_p(s1_4["clip_p10"])}, the same answer as {large_clip_h}p
  with a {small_clip_h}p clip ({clip_ratio:.1f}× cheaper).
  The answer is honest: once the face is big enough to measure, this shot <i>does</i> drift,
  so lowering the threshold would have shipped a bad clip.
  <a href="deep/scoreboard-framing.html">Full scoreboard →</a></p>
</div>

<div class="card" id="how">
  <h2>How it works</h2>
  <div class="cols">
    <div>
      <ol class="steps">
        <li><b>Character</b>: one portrait → ArcFace embedding.</li>
        <li><b>Keyframes</b>: Qwen-Image-Edit-2511 composes each shot's start (and end) still from the portrait.
          Gated: identity, plus a face-size and camera-direction check, re-rolled or re-prompted by cause.</li>
        <li><b>Clips</b>: Wan 2.2 I2V A14B animates between keyframes. Gated the same way.</li>
        <li><b>Stitch</b>: ffmpeg concat. One failed shot degrades the run; it doesn't fail it.</li>
        <li><b>Every step is content-addressed</b>: <code>sha256(step, model@rev, params, inputs, seed)</code>.
          A re-run or a new workflow version only computes what changed, so A/B arms share upstream work.</li>
        <li><b>On Modal</b>: one GPU class per model family, weights on a Volume, a CPU orchestrator and a FastAPI
          layer that scale on their own. The unit tests run in CI without a GPU.</li>
      </ol>
    </div>
    <div>
<pre>POST /v1/workflows/{api_wf}/runs
Idempotency-Key: cafe-morning-c01-1

202 {{
  "request_id": "req_6e1e633dc910",
  "status": "queued",
  "replayed": false,
  "estimate": {{ "usd_low": {api_est["usd_low"]}, "usd_high": {api_est["usd_high"]} }},
  "status_url": "…/v1/runs/req_6e1e633dc910",
  "cancel_url": "…/v1/runs/req_6e1e633dc910/cancel",
  "result_url": "…/v1/runs/req_6e1e633dc910/result"
}}</pre>
      <p class="hint">Async submit, poll and cancel; an <code>Idempotency-Key</code> replays the original run instead
      of paying twice; the run reports per-shot attempts, verdicts and billed GPU time. The estimate is priced
      from measured timings before anything runs (here for {api_shots} shots: best case vs every retry and a cold
      start).</p>
    </div>
  </div>
</div>

<div class="card">
  <h2>What a run costs</h2>
  <div class="scroll"><table><thead><tr><th>Step</th><th>Model</th><th class="num">Cold load</th>
  <th class="num">Inference</th><th class="num">$ (cold)</th><th class="num">$ (warm)</th></tr></thead><tbody>
  <tr><td>Keyframe</td><td>Qwen-Image-Edit-2511, 4-step Lightning</td><td class="num">{kf_t["load_s"]:.0f} s</td>
    <td class="num">{kf_t["infer_s"]:.1f} s</td><td class="num">{_usd(kf_t["usd"])}</td>
    <td class="num">{_usd(kf_t["infer_s"] * GPU_USD_PER_SECOND[kf_t["gpu"]])}</td></tr>
  <tr><td>Clip</td><td>Wan 2.2 I2V A14B, 4-step Lightning</td><td class="num">{clip_t["load_s"]:.0f} s</td>
    <td class="num">{clip_t["infer_s"]:.1f} s</td><td class="num">{_usd(clip_t["usd"])}</td>
    <td class="num">{_usd(warm_clip_usd)}</td></tr>
  </tbody></table></div>
  <p class="take">Warm inference is already cheap and fast; <b>the cost is the cold start</b>. Wan's weights took
  {clip_t["load_s"]:.0f} s to load and cast in this run, so most of a small run's bill is model loading.
  Re-saved bf16 weights plus Modal memory snapshots are the next step.</p>
</div>

<div class="card" id="next">
  <h2>What's next</h2>
  <ul>
    <li><b>Six shots, one API call.</b> A 30-second script through the API to a stitched video and a run page.</li>
    <li><b>Retry ladder as config:</b> same → degrade → alternate model → fallback shot, so an agent's retry rules
      become testable code with bounded cost.</li>
    <li><b>Calibration:</b> fit the identity threshold to face size on hand-labeled frames, and use the gate to
      measure how often an LLM critic agrees with it.</li>
    <li><b>Cold starts:</b> bf16 weights and memory snapshots, with a before/after table.</li>
    <li><b>More arms:</b> full-step vs 4-step Wan, and hosted video APIs behind the same adapter interface.</li>
  </ul>
</div>

<footer>Built by Peter Hyland. All characters are generated; no real people. Numbers come from runs on
{dates} UTC (one character, one seed per arm) and are regenerated from the run records by
<code>castbook/site.py</code>. <a href="{REPO}">{REPO.removeprefix("https://")}</a></footer>
</main>
{chart_script(per_frame, n_frames, fps)}
<script>
document.getElementById("play").addEventListener("click", () => {{
  document.querySelectorAll(".trio video").forEach(v => {{ v.currentTime = 0; v.play(); }});
}});
</script>
</body></html>
"""
    (site / "index.html").write_text(page)


if __name__ == "__main__":
    print(build())
