"""Static run viewer: one self-contained HTML page per run, plus an index.

Reads out/runs/<run_id>/record.json and writes index.html next to it with the
portrait, keyframe and clip embedded as data URIs, so the page is a single file
you can open from disk or send to someone. No server, no external assets.

    uv run python -m castbook.viewer            # render every run under out/runs
"""

import base64
import html
import json
import sys
from pathlib import Path

from castbook.config import GPU_USD_PER_SECOND
from castbook.workflow import load_workflow

RUNS_DIR = Path("out/runs")

# Chart geometry (SVG user units; the SVG scales to its container width).
W, H = 720, 260
PAD_L, PAD_R, PAD_T, PAD_B = 44, 16, 16, 36

CSS = """
:root {
  --surface-0: #f4f4f2; --surface-1: #fcfcfb; --border: #e3e2dd;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #77766f;
  --grid: #ebeae6; --series-1: #2a78d6; --ref: #77766f; --band: #efeee9;
  --good: #0ca30c; --good-ink: #0a7d0a; --warning: #fab219; --warning-ink: #8a5a00;
  --critical: #d03b3b; --critical-ink: #b02c2c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #96958c;
    --grid: #262624; --series-1: #3987e5; --ref: #96958c; --band: #252523;
    --good: #0ca30c; --good-ink: #5fcf5f; --warning: #fab219; --warning-ink: #fab219;
    --critical: #d03b3b; --critical-ink: #ef7d7d;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 24px 16px 48px; }
a { color: var(--series-1); }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 0 0 12px; }
.meta { color: var(--text-secondary); margin: 0 0 20px; }
.meta code { font-size: 12px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px;
  padding: 16px; margin-bottom: 16px; }
.media { display: grid; grid-template-columns: 1fr 1.6fr; gap: 16px; }
.media img { width: 100%; border-radius: 6px; display: block; }
.media figure { margin: 0; }
figcaption { color: var(--text-secondary); font-size: 12px; margin-top: 6px; }
video { width: 100%; border-radius: 6px; display: block; background: #000; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.stat { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
.stat .label { color: var(--text-secondary); font-size: 12px; }
.stat .value { font-size: 22px; font-variant-numeric: tabular-nums; }
.stat .sub { color: var(--text-muted); font-size: 12px; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--text-secondary); font-weight: 500; font-size: 12px; }
td.num, th.num { text-align: right; }
tfoot td { font-weight: 600; border-bottom: none; }
.chart-wrap { position: relative; }
svg.chart { width: 100%; height: auto; display: block; }
svg.chart text { fill: var(--text-secondary); font-size: 11px; }
.tooltip { position: absolute; pointer-events: none; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font-size: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.12); display: none; white-space: nowrap; }
.hint { color: var(--text-muted); font-size: 12px; margin: 8px 0 0; }
.verdicts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.verdict { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px;
  display: flex; gap: 12px; align-items: flex-start; }
.chip { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 2px 10px 2px 6px;
  font-size: 12px; font-weight: 600; white-space: nowrap; border: 1px solid currentColor; }
.chip .dot { width: 16px; height: 16px; border-radius: 50%; display: inline-flex; align-items: center;
  justify-content: center; color: #fff; font-size: 11px; line-height: 1; }
.chip.pass { color: var(--good-ink); } .chip.pass .dot { background: var(--good); }
.chip.fail { color: var(--critical-ink); } .chip.fail .dot { background: var(--critical); }
.chip.unverifiable { color: var(--warning-ink); } .chip.unverifiable .dot { background: var(--warning); color: #1a1a19; }
.verdict .what { font-weight: 600; } .verdict .why { color: var(--text-secondary); font-size: 13px; }
@media (max-width: 720px) { .verdicts { grid-template-columns: 1fr; } }
details { margin-top: 12px; }
summary { cursor: pointer; color: var(--text-secondary); font-size: 12px; }
.prompt { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }
@media (max-width: 720px) {
  .media { grid-template-columns: 1fr; }
  .stats { grid-template-columns: repeat(2, 1fr); }
}
"""


def _fmt(v: float | None, digits: int = 2) -> str:
    return "—" if v is None else f"{v:.{digits}f}"


def _x(frame: int, n_frames: int) -> float:
    return PAD_L + (W - PAD_L - PAD_R) * (frame / max(n_frames - 1, 1))


def _y(sim: float) -> float:
    # Cosine similarity can be slightly negative; clamp to the 0..1 axis.
    return PAD_T + (H - PAD_T - PAD_B) * (1 - max(0.0, min(1.0, sim)))


def identity_chart_svg(per_frame: list[dict], n_frames: int, keyframe_sim: float | None) -> str:
    """Per-frame ArcFace similarity as a single 2px line with markers.

    Frames with no detected face break the line and get a hollow marker on the
    baseline, so a missing face never reads as a score of zero. Profile frames
    (turned past the judge's max_yaw) sit in a shaded band with grey markers:
    their raw similarity is still drawn, but it is not part of the score.
    """
    parts = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Identity similarity per frame">']
    frames = [p["frame"] for p in per_frame]
    for i, p in enumerate(per_frame):
        if not p.get("profile"):
            continue
        lo = (frames[i - 1] + p["frame"]) / 2 if i > 0 else p["frame"]
        hi = (frames[i + 1] + p["frame"]) / 2 if i + 1 < len(frames) else p["frame"]
        x0, x1 = _x(lo, n_frames), _x(hi, n_frames)
        parts.append(
            f'<rect x="{x0:.1f}" y="{PAD_T}" width="{x1 - x0:.1f}" height="{H - PAD_T - PAD_B}" fill="var(--band)"/>'
        )
    first_profile = next((p for p in per_frame if p.get("profile")), None)
    if first_profile is not None:
        parts.append(
            f'<text x="{_x(first_profile["frame"], n_frames) + 4:.1f}" y="{PAD_T + 12}">profile · not scored</text>'
        )
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = _y(t)
        parts.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--grid)"/>')
        parts.append(f'<text x="{PAD_L - 8}" y="{y + 4:.1f}" text-anchor="end">{t:.2f}</text>')
    for f in sorted({0, n_frames - 1, *[p["frame"] for p in per_frame][:: max(1, len(per_frame) // 6)]}):
        parts.append(f'<text x="{_x(f, n_frames):.1f}" y="{H - 14}" text-anchor="middle">{f}</text>')
    parts.append(f'<text x="{(PAD_L + W - PAD_R) / 2}" y="{H - 1}" text-anchor="middle">frame</text>')

    if keyframe_sim is not None:
        y = _y(keyframe_sim)
        parts.append(
            f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--ref)" '
            f'stroke-width="1" stroke-dasharray="4 4"/>'
        )
        parts.append(f'<text x="{W - PAD_R}" y="{y - 6:.1f}" text-anchor="end">keyframe {keyframe_sim:.2f}</text>')

    segment: list[str] = []
    segments: list[list[str]] = []
    for p in per_frame:
        if p["sim"] is None:
            if segment:
                segments.append(segment)
            segment = []
        else:
            segment.append(f"{_x(p['frame'], n_frames):.1f},{_y(p['sim']):.1f}")
    if segment:
        segments.append(segment)
    for seg in segments:
        parts.append(
            f'<polyline points="{" ".join(seg)}" fill="none" stroke="var(--series-1)" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    for p in per_frame:
        x = _x(p["frame"], n_frames)
        if p["sim"] is None:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{_y(0):.1f}" r="4" fill="var(--surface-1)" stroke="var(--text-muted)" '
                f'stroke-width="1.5"/>'
            )
        else:
            y = _y(p["sim"])
            fill = "var(--text-muted)" if p.get("profile") or p.get("occluded") else "var(--series-1)"
            if p.get("occluded"):
                # Diamond = a hand covers the face, whether or not the frame is also a profile.
                parts.append(
                    f'<path d="M{x:.1f} {y - 5.5:.1f} L{x + 5.5:.1f} {y:.1f} L{x:.1f} {y + 5.5:.1f} L{x - 5.5:.1f} {y:.1f} Z" '
                    f'fill="{fill}" stroke="var(--surface-1)" stroke-width="2"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{fill}" stroke="var(--surface-1)" stroke-width="2"/>'
                )
    parts.append(
        f'<line id="playhead" x1="{PAD_L}" x2="{PAD_L}" y1="{PAD_T}" y2="{H - PAD_B}" stroke="var(--text-primary)" '
        f'stroke-width="1" opacity="0.5"/>'
    )
    parts.append(
        f'<line id="crosshair" x1="0" x2="0" y1="{PAD_T}" y2="{H - PAD_B}" stroke="var(--text-muted)" '
        f'stroke-width="1" visibility="hidden"/>'
    )
    parts.append(
        f'<rect id="hit" x="{PAD_L}" y="{PAD_T}" width="{W - PAD_L - PAD_R}" height="{H - PAD_T - PAD_B}" '
        f'fill="transparent" style="cursor:pointer"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


_VERDICT_ICON = {"pass": "✓", "fail": "✕", "unverifiable": "?"}
_VERDICT_NEXT = {
    "pass": "Keep this take.",
    "fail": "Re-roll with a new seed; escalate the model after repeated fails.",
    "unverifiable": "Re-prompt so the face stays visible (less head turn, hands away), then re-score.",
}


def _frame_status_label(p: dict) -> str:
    if p["sim"] is None:
        return "no face"
    flags = [f for f, on in (("profile", p.get("profile")), ("hand on face", p.get("occluded"))) if on]
    return f"{', '.join(flags)}; not scored" if flags else "scored"


def _verdicts_html(record: dict) -> str:
    verdicts = record.get("verdicts") or {}
    cards = []
    for what in ("keyframe", "clip"):
        v = verdicts.get(what)
        if not v:
            continue
        reasons = "; ".join(html.escape(r) for r in v["reasons"])
        cards.append(
            f'<div class="verdict"><span class="chip {v["status"]}"><span class="dot">{_VERDICT_ICON[v["status"]]}</span>'
            f'{v["status"]}</span><div><div class="what">{what.capitalize()} identity gate</div>'
            f'<div class="why">{reasons}. {_VERDICT_NEXT[v["status"]]}</div></div></div>'
        )
    return f'<div class="verdicts">{"".join(cards)}</div>' if cards else ""


def _gate_cell(record: dict) -> str:
    v = (record.get("verdicts") or {}).get("clip")
    if not v:
        return "—"
    return f'<span class="chip {v["status"]}"><span class="dot">{_VERDICT_ICON[v["status"]]}</span>{v["status"]}</span>'


def _step_rows(record: dict, models: dict[str, str]) -> tuple[str, float]:
    rows, total = [], 0.0
    for s in record["steps"]:
        timings = s.get("timings") or []
        if s["cache"] == "hit" or not timings:
            rows.append(
                f"<tr><td>{s['step']}</td><td>{html.escape(models.get(s['step'], ''))}</td><td>hit</td>"
                f'<td>—</td><td class="num">—</td><td class="num">—</td><td class="num">$0.000</td></tr>'
            )
            continue
        for t in timings:
            total += t["usd"]
            rows.append(
                f"<tr><td>{s['step']}</td><td>{html.escape(models.get(s['step'], ''))}</td><td>miss</td>"
                f"<td>{t['gpu']}{' · cold' if t['cold'] else ''}</td>"
                f'<td class="num">{t["load_s"]:.1f}</td><td class="num">{t["infer_s"]:.1f}</td>'
                f'<td class="num">${t["usd"]:.3f}</td></tr>'
            )
    return "".join(rows), total


_CHART_JS = """
const svg = document.querySelector("svg.chart"), tip = document.getElementById("tip");
const video = document.getElementById("clip"), hit = document.getElementById("hit");
const cross = document.getElementById("crosshair"), play = document.getElementById("playhead");
const span = D.W - D.PAD_L - D.PAD_R;
const xOf = f => D.PAD_L + span * f / Math.max(D.n_frames - 1, 1);
function toFrame(evt) {
  const pt = svg.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
  const p = pt.matrixTransform(svg.getScreenCTM().inverse());
  return Math.max(0, Math.min(D.n_frames - 1, (p.x - D.PAD_L) / span * (D.n_frames - 1)));
}
function nearest(f) {
  return D.per_frame.reduce((a, b) => Math.abs(b.frame - f) < Math.abs(a.frame - f) ? b : a);
}
hit.addEventListener("mousemove", e => {
  const p = nearest(toFrame(e)), x = xOf(p.frame);
  cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("visibility", "visible");
  tip.innerHTML = `<b>frame ${p.frame}</b> · ${(p.frame / D.fps).toFixed(2)} s<br>` +
    (p.sim === null ? "no face detected" : `similarity ${p.sim.toFixed(3)}`) +
    (p.yaw == null ? "" : `<br>yaw ${p.yaw.toFixed(0)}°${p.profile ? " · profile" : ""}`) +
    (p.hand_overlap == null ? "" : `<br>hand covers ${(p.hand_overlap * 100).toFixed(0)}% of face${p.occluded ? " · occluded" : ""}`) +
    (p.status && p.status !== "scored" && p.status !== "no_face" ? "<br><i>not scored</i>" : "");
  const box = svg.getBoundingClientRect(), wrap = svg.parentElement.getBoundingClientRect();
  const px = (x / D.W) * box.width;
  tip.style.display = "block";
  tip.style.left = Math.min(px + 12, box.width - tip.offsetWidth) + "px";
  tip.style.top = (e.clientY - wrap.top - 40) + "px";
});
hit.addEventListener("mouseleave", () => { tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); });
hit.addEventListener("click", e => { video.pause(); video.currentTime = nearest(toFrame(e)).frame / D.fps; });
function tick() {
  const x = xOf(Math.min(D.n_frames - 1, video.currentTime * D.fps));
  play.setAttribute("x1", x); play.setAttribute("x2", x);
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
"""


def chart_script(per_frame: list[dict], n_frames: int, fps: float) -> str:
    """The <script> that syncs an identity_chart_svg with the page's <video id="clip">: hover for values,
    click to seek, and a playhead that follows playback. Expects one chart, one #tip and one #clip per page."""
    data = json.dumps(
        {"fps": fps, "n_frames": n_frames, "per_frame": per_frame, "W": W, "PAD_L": PAD_L, "PAD_R": PAD_R}
    )
    return f"<script>\nconst D = {data};{_CHART_JS}</script>"


def _data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def render_run(run_dir: Path) -> Path:
    record = json.loads((run_dir / "record.json").read_text())
    wf = load_workflow(record["workflow"])
    clip_params = wf.steps["clip"].params
    fps = clip_params["fps"]
    clip_step = next((s for s in record["steps"] if s["step"] == "clip"), {})
    n_frames = clip_step.get("n_frames", clip_params["num_frames"])
    models = {name: step.model or "" for name, step in wf.steps.items()}
    ident = record["identity"]
    kf, clip, per_frame = ident["keyframe"], ident["clip"], ident["clip_per_frame"]
    rows, total = _step_rows(record, models)
    warm_clip = next((t["infer_s"] for t in clip_step.get("timings", [])), None)
    warm_usd = None if warm_clip is None else warm_clip * GPU_USD_PER_SECOND["H100"]
    prompts = record.get("prompts", {})
    frame_rows = "".join(
        f'<tr><td class="num">{p["frame"]}</td><td class="num">{p["frame"] / fps:.2f}</td>'
        f'<td class="num">{"no face" if p["sim"] is None else f"{p['sim']:.3f}"}</td>'
        f'<td class="num">{_fmt(p.get("yaw"), 0)}</td>'
        f'<td class="num">{"—" if p.get("hand_overlap") is None else f"{p['hand_overlap']:.0%}"}</td>'
        f"<td>{_frame_status_label(p)}</td></tr>"
        for p in per_frame
    )
    pose_aware = clip.get("max_yaw") is not None
    clip_label = (
        f"Clip identity (frames within ±{clip['max_yaw']:.0f}°)" if pose_aware else "Clip identity (all frames)"
    )
    clip_sub = f"min {_fmt(clip['min'])} · p10 {_fmt(clip['p10'])} · faces {clip['face_rate']:.0%}"
    if pose_aware:
        clip_sub += f" · profile {clip['profile_rate']:.0%}"
        if "occluded_rate" in clip:
            clip_sub += f" · hand on face {clip['occluded_rate']:.0%}"
        clip_sub += f" · scored {clip['n_scored']}/{clip['n_frames']}"
    hint = (
        f"Shaded frames are turned more than {clip['max_yaw']:.0f}° from the camera; they are counted as profile "
        "and left out of the score, because ArcFace similarity collapses on profiles even for the right person."
        + (" Diamonds mark frames where a hand covers the face." if "occluded_rate" in clip else "")
        if pose_aware
        else "This run predates the pose-aware judge: turned-away frames score low even when the identity is right."
    )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Castbook run {record["run_id"]}</title><style>{CSS}</style></head>
<body><main>
<p><a href="../index.html">← all runs</a></p>
<h1>{html.escape(record["character"])} · {html.escape(record["workflow"])}</h1>
<p class="meta"><code>{record["run_id"]}</code> · seed {record["seed"]} · {record["wall_s"]:.0f} s wall</p>

{_verdicts_html(record)}
<div class="stats">
  <div class="stat"><div class="label">Keyframe identity</div><div class="value">{_fmt(kf["mean"])}</div>
    <div class="sub">ArcFace cosine vs portrait</div></div>
  <div class="stat"><div class="label">{clip_label}</div><div class="value">{_fmt(clip["mean"])}</div>
    <div class="sub">{clip_sub}</div></div>
  <div class="stat"><div class="label">GPU cost this run</div><div class="value">${record["gpu_usd"]:.2f}</div>
    <div class="sub">includes cold-start loads</div></div>
  <div class="stat"><div class="label">Warm clip cost</div>
    <div class="value">{"—" if warm_usd is None else f"${warm_usd:.3f}"}</div>
    <div class="sub">{("cache hit, clip reused" if clip_step.get("cache") == "hit" else "—") if warm_clip is None else f"{warm_clip:.1f} s inference on H100"}</div></div>
</div>

<div class="card media">
  <figure><img src="{_data_uri(run_dir / "portrait.png", "image/png")}" alt="Character portrait"><figcaption>Portrait (identity reference)</figcaption>
    <img src="{_data_uri(run_dir / "keyframe.png", "image/png")}" alt="Keyframe" style="margin-top:12px">
    <figcaption>Keyframe · {html.escape(models.get("keyframe", ""))}</figcaption>
    {f'<p class="prompt">{html.escape(prompts["keyframe"])}</p>' if prompts.get("keyframe") else ""}</figure>
  <figure><video id="clip" src="{_data_uri(run_dir / "clip.mp4", "video/mp4")}" controls loop muted playsinline></video>
    <figcaption>Clip · {html.escape(models.get("clip", ""))} · {n_frames} frames at {fps} fps</figcaption>
    {f'<p class="prompt">{html.escape(prompts["clip"])}</p>' if prompts.get("clip") else ""}</figure>
</div>

<div class="card">
  <h2>Identity per frame</h2>
  <div class="chart-wrap">{identity_chart_svg(per_frame, n_frames, kf["mean"])}<div class="tooltip" id="tip"></div></div>
  <p class="hint">Hover for values; click to jump the clip to that frame. Hollow markers on the baseline are
  frames with no detected face. {hint}</p>
  <details><summary>Table view</summary>
    <table><thead><tr><th class="num">Frame</th><th class="num">Time (s)</th><th class="num">Similarity</th><th class="num">Yaw °</th><th class="num">Hand on face</th><th>Status</th></tr></thead>
    <tbody>{frame_rows}</tbody></table></details>
</div>

<div class="card">
  <h2>Steps and cost</h2>
  <table><thead><tr><th>Step</th><th>Model</th><th>Cache</th><th>GPU</th><th class="num">Load s</th>
    <th class="num">Inference s</th><th class="num">$</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot><tr><td colspan="6">Total (attributable GPU time)</td><td class="num">${total:.3f}</td></tr></tfoot></table>
</div>
</main>
{chart_script(per_frame, n_frames, fps)}
</body></html>
"""
    out = run_dir / "index.html"
    out.write_text(page)
    return out


def render_index(runs_dir: Path = RUNS_DIR) -> Path:
    rows = []
    for d in sorted((p for p in runs_dir.iterdir() if (p / "record.json").exists()), reverse=True):
        r = json.loads((d / "record.json").read_text())
        ident = r["identity"]
        rows.append(
            f'<tr><td><a href="{d.name}/index.html">{r["run_id"]}</a></td><td>{html.escape(r["character"])}</td>'
            f"<td>{html.escape(r['workflow'])}</td>"
            f"<td>{_gate_cell(r)}</td>"
            f'<td class="num">{_fmt(ident["keyframe"]["mean"])}</td><td class="num">{_fmt(ident["clip"]["mean"])}</td>'
            f'<td class="num">{_fmt(ident["clip"]["min"])}</td>'
            f'<td class="num">{"—" if ident["clip"].get("max_yaw") is None else f"{ident['clip']['profile_rate']:.0%}"}</td>'
            f'<td class="num">${r["gpu_usd"]:.2f}</td>'
            f'<td class="num">{r["wall_s"]:.0f}</td></tr>'
        )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Castbook runs</title><style>{CSS}</style></head>
<body><main><h1>Castbook runs</h1><p class="meta">{len(rows)} run(s) in <code>{runs_dir}</code></p>
<div class="card"><table><thead><tr><th>Run</th><th>Character</th><th>Workflow</th>
<th>Gate</th><th class="num">Keyframe ID</th><th class="num">Clip ID mean</th><th class="num">Clip ID min</th><th class="num">Profile</th>
<th class="num">GPU $</th><th class="num">Wall s</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
</main></body></html>
"""
    out = runs_dir / "index.html"
    out.write_text(page)
    return out


def render_all(runs_dir: Path = RUNS_DIR) -> Path:
    for d in runs_dir.iterdir():
        if (d / "record.json").exists():
            render_run(d)
    return render_index(runs_dir)


if __name__ == "__main__":
    print(render_all(Path(sys.argv[1]) if len(sys.argv) > 1 else RUNS_DIR).resolve())
