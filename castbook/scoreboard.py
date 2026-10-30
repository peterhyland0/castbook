"""A/B scoreboard: the same script and character through several workflow versions, compared on
identity, retries and cost.

Each arm is one multishot run (dag.RunResult as a dict). Cost is reported two ways:

- `warm_usd`: GPU inference seconds of every attempt the arm made, priced warm. This is what the
  workflow itself costs, independent of cache hits and of which arm happened to pay a cold start.
- `billed_usd`: what this run actually paid (cache misses, including cold loads).

`$/accepted s` divides warm cost by seconds of clips whose final identity verdict is `pass`, so a
workflow that's cheap per call but needs re-rolls, or that ships unverifiable clips, pays for it.

    uv run python -m castbook.scoreboard out/scoreboard/<name>    # re-render from saved summaries
"""

import html
import json
import sys
from pathlib import Path

from castbook.config import GPU_USD_PER_SECOND
from castbook.viewer import CSS, _data_uri
from castbook.workflow import load_workflow

_GATED = ("keyframe_attempts", "end_keyframe_attempts", "clip_attempts")
_ICON = {"pass": "✓", "fail": "✕", "unverifiable": "?"}


def _short_error(error: str | None, limit: int = 200) -> str:
    """Last line of an error, which for a remote traceback is the exception itself (e.g. CUDA out of memory)."""
    if not error:
        return "no clip"
    last = [line for line in error.strip().splitlines() if line.strip()][-1].strip()
    return last if len(last) <= limit else last[: limit - 1] + "…"


def _chosen(attempts: list[dict], key: str | None) -> dict | None:
    return next((a for a in attempts if a["key"] == key), None)


def summarize(result: dict) -> dict:
    """Scoreboard numbers for one arm."""
    wf = load_workflow(result["workflow"])
    clip_params = wf.steps["clip"].params
    clip_s = clip_params["num_frames"] / clip_params["fps"]
    attempts = [a for s in result["shots"] for field in _GATED for a in s.get(field, [])]
    warm_s = warm_usd = 0.0
    for a in attempts:
        t = a.get("timing")
        if t and t["gpu"] != "CPU":
            warm_s += t["infer_s"]
            warm_usd += t["infer_s"] * GPU_USD_PER_SECOND[t["gpu"]]

    shots = []
    for s in result["shots"]:
        clip = _chosen(s["clip_attempts"], s.get("clip_key"))
        first_try = all(s.get(f) and s[f][0]["verdict"]["status"] == "pass" for f in _GATED if s.get(f))
        shots.append(
            {
                "shot_id": s["shot_id"],
                "status": s["status"],
                "clip_status": clip["verdict"]["status"] if clip else None,
                "clip_p10": clip["verdict"]["value"] if clip else None,
                "clip_mean": clip["score"].get("mean") if clip else None,
                "coverage": clip["verdict"]["coverage"] if clip else None,
                "reasons": clip["verdict"]["reasons"] if clip else [_short_error(s.get("error"))],
                "first_try_pass": bool(first_try and s["clip_attempts"]),
                "attempts": {f.removesuffix("_attempts"): len(s.get(f, [])) for f in _GATED if s.get(f)},
            }
        )
    accepted = sum(1 for s in shots if s["clip_status"] == "pass")
    p10s = [s["clip_p10"] for s in shots if s["clip_status"] == "pass"]
    return {
        "workflow": result["workflow"],
        "mode": wf.mode,
        "request_id": result.get("request_id"),
        "n_shots": len(shots),
        "accepted": accepted,
        "first_try": sum(s["first_try_pass"] for s in shots),
        "unverifiable": sum(1 for s in shots if s["clip_status"] == "unverifiable"),
        "min_p10": min(p10s) if p10s else None,
        "mean_p10": sum(p10s) / len(p10s) if p10s else None,
        "n_attempts": len(attempts),
        "warm_gpu_s": round(warm_s, 1),
        "warm_usd": round(warm_usd, 4),
        "billed_usd": round(sum(t["usd"] for t in result.get("timings", [])), 4),
        "usd_per_accepted_s": round(warm_usd / (accepted * clip_s), 5) if accepted else None,
        "clip_s": clip_s,
        "wall_s": result.get("wall_s"),
        "shots": shots,
    }


def _f(v: float | None, fmt: str = "{:.2f}") -> str:
    return "–" if v is None else fmt.format(v)


def _chip(status: str | None, label: str) -> str:
    if status is None:
        return '<span class="muted">no clip</span>'
    return f'<span class="chip {status}"><span class="dot">{_ICON[status]}</span>{html.escape(label)}</span>'


def _best(arms: list[dict], key: str, lower: bool = False) -> float | None:
    vals = [a[key] for a in arms if a[key] is not None]
    return (min(vals) if lower else max(vals)) if vals else None


def render(out_dir: Path, arms: list[dict], script: dict) -> Path:
    """Write out_dir/index.html. `arms` are summaries; each arm's final.mp4 is read from out_dir/<workflow>/."""
    best = {
        "accepted": _best(arms, "accepted"),
        "first_try": _best(arms, "first_try"),
        "min_p10": _best(arms, "min_p10"),
        "warm_usd": _best(arms, "warm_usd", lower=True),
        "usd_per_accepted_s": _best(arms, "usd_per_accepted_s", lower=True),
    }

    def cell(arm: dict, key: str, text: str) -> str:
        win = arm[key] is not None and arm[key] == best.get(key) and len(arms) > 1
        return f'<td class="num{" win" if win else ""}">{text}</td>'

    rows = []
    for a in arms:
        n = a["n_shots"]
        rows.append(
            f"<tr><td><code>{html.escape(a['workflow'])}</code></td>"
            + cell(a, "accepted", f"{a['accepted']}/{n}")
            + cell(a, "first_try", f"{a['first_try']}/{n}")
            + f'<td class="num">{a["unverifiable"]}</td>'
            + cell(a, "min_p10", _f(a["min_p10"]))
            + f'<td class="num">{a["n_attempts"]}</td>'
            + f'<td class="num">{a["warm_gpu_s"]:.0f}</td>'
            + cell(a, "warm_usd", f"${a['warm_usd']:.3f}")
            + cell(a, "usd_per_accepted_s", _f(a["usd_per_accepted_s"], "${:.4f}"))
            + f'<td class="num">${a["billed_usd"]:.3f}</td></tr>'
        )

    videos = []
    for a in arms:
        mp4 = out_dir / a["workflow"] / "final.mp4"
        src = _data_uri(mp4, "video/mp4") if mp4.exists() else ""
        videos.append(
            f'<figure><video src="{src}" muted playsinline loop controls preload="auto"></video>'
            f"<figcaption><code>{html.escape(a['workflow'])}</code> · {a['accepted']}/{a['n_shots']} accepted"
            "</figcaption></figure>"
        )

    shot_ids = [s["shot_id"] for s in arms[0]["shots"]] if arms else []
    shot_rows = []
    for i, sid in enumerate(shot_ids):
        spec = next((s for s in script.get("shots", []) if s["id"] == sid), {})
        cells = []
        for a in arms:
            s = a["shots"][i]
            label = f"{_f(s['clip_p10'])} · {_f(s['coverage'], '{:.0%}')} scored"
            tries = " · ".join(f"{k} ×{v}" for k, v in s["attempts"].items())
            why = "; ".join(r for r in s["reasons"] if r)
            cells.append(
                f"<td>{_chip(s['clip_status'], label)}"
                f'<div class="why">{html.escape(tries)}</div>'
                f'<div class="why muted">{html.escape(why)}</div></td>'
            )
        shot_rows.append(
            f'<tr><td><b>{html.escape(sid)}</b><div class="why muted">{html.escape(spec.get("motion", ""))}</div>'
            f"</td>{''.join(cells)}</tr>"
        )

    head = "".join(f"<th><code>{html.escape(a['workflow'])}</code></th>" for a in arms)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Castbook scoreboard</title>
<style>{CSS}
.videos {{ display: grid; grid-template-columns: repeat({max(len(arms), 1)}, 1fr); gap: 12px; }}
.videos figure {{ margin: 0; }}
td.win {{ font-weight: 700; color: var(--good-ink); }}
.why {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
.muted {{ color: var(--text-muted); }}
.scroll {{ overflow-x: auto; }}
button {{ font: inherit; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--surface-0); color: var(--text-primary); cursor: pointer; }}
@media (max-width: 720px) {{ .videos {{ grid-template-columns: 1fr; }} }}
</style></head><body><main>
<h1>Workflow scoreboard</h1>
<p class="meta">Character <code>{html.escape(script.get("character", ""))}</code> · {len(shot_ids)} shots ·
seed {script.get("seed", "")} · same script through {len(arms)} workflow versions</p>

<div class="card"><h2>Results</h2><div class="scroll"><table>
<thead><tr><th>Workflow</th><th class="num">Accepted</th><th class="num">First try</th>
<th class="num">Unverifiable</th><th class="num">Min p10</th><th class="num">Attempts</th>
<th class="num">GPU s</th><th class="num">Warm $</th><th class="num">$/accepted s</th><th class="num">Billed $</th>
</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="hint"><b>Accepted</b>: shots whose final clip passed the identity gate (p10 ≥ 0.5 over ≥ 50% scorable
frames). <b>First try</b>: every gated step passed on attempt 1, i.e. without the gate's re-rolls.
<b>Warm $</b>: inference GPU time of every attempt, priced warm, whether or not it was a cache hit this run.
<b>Billed $</b>: what this run paid, cold loads included; it depends on run order and caching, so compare
arms on warm $. Bold is best in column.</p></div>

<div class="card"><h2>Final videos</h2><div class="videos">{"".join(videos)}</div>
<p class="hint"><button id="play">Play all from start</button></p></div>

<div class="card"><h2>Per shot: final clip identity</h2><div class="scroll"><table>
<thead><tr><th>Shot</th>{head}</tr></thead><tbody>{"".join(shot_rows)}</tbody></table></div>
<p class="hint">p10 of ArcFace similarity over scorable frames · share of sampled frames that were scorable
(not profile, covered or too small) · attempts per step.</p></div>
</main>
<script>
document.getElementById("play").addEventListener("click", () => {{
  document.querySelectorAll("video").forEach(v => {{ v.currentTime = 0; v.play(); }});
}});
</script></body></html>"""
    path = out_dir / "index.html"
    path.write_text(page)
    return path


def main(out_dir: str) -> None:
    """Re-summarize each arm from its saved record (so summary changes apply to old runs), then re-render."""
    d = Path(out_dir)
    summary = json.loads((d / "summary.json").read_text())
    arms = []
    for arm in summary["arms"]:
        record = d / arm["workflow"] / "record.json"
        arms.append(summarize(json.loads(record.read_text())) if record.exists() else arm)
    print(render(d, arms, summary["script"]))


if __name__ == "__main__":
    main(sys.argv[1])
