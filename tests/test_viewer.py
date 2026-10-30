import json

from castbook.viewer import identity_chart_svg, render_index, render_run


def _record(run_id="r1"):
    return {
        "run_id": run_id,
        "workflow": "single_shot@1",
        "character": "c01",
        "seed": 7,
        "prompts": {"keyframe": "kf <prompt>", "clip": "motion"},
        "steps": [
            {
                "step": "keyframe",
                "cache": "miss",
                "wall_s": 1,
                "timings": [{"gpu": "H100", "load_s": 50.0, "infer_s": 5.0, "cold": True, "usd": 0.06}],
            },
            {"step": "clip", "cache": "hit", "wall_s": 0.1},
        ],
        "identity": {
            "keyframe": {"n_frames": 1, "face_rate": 1.0, "min": 0.8, "p10": 0.8, "mean": 0.8},
            "clip": {"n_frames": 3, "face_rate": 2 / 3, "min": 0.1, "p10": 0.15, "mean": 0.4},
            "clip_per_frame": [{"frame": 0, "sim": 0.7}, {"frame": 40, "sim": None}, {"frame": 80, "sim": 0.1}],
        },
        "gpu_usd": 0.06,
        "wall_s": 12.0,
    }


def _run_dir(tmp_path, run_id="r1"):
    d = tmp_path / run_id
    d.mkdir()
    (d / "record.json").write_text(json.dumps(_record(run_id)))
    for name in ("portrait.png", "keyframe.png", "clip.mp4"):
        (d / name).write_bytes(b"fake")
    return d


def test_run_page_is_self_contained_and_escapes_prompts(tmp_path):
    page = render_run(_run_dir(tmp_path)).read_text()
    assert "data:image/png;base64," in page and "data:video/mp4;base64," in page
    assert 'src="portrait.png"' not in page
    assert "kf &lt;prompt&gt;" in page
    assert "$0.060" in page  # cost table total


def test_missing_face_breaks_the_line_and_gets_a_hollow_marker():
    svg = identity_chart_svg(_record()["identity"]["clip_per_frame"], 81, 0.8)
    assert svg.count("<polyline") == 2  # the gap at frame 40 splits the line
    assert 'fill="var(--surface-1)"' in svg  # hollow no-face marker
    assert "keyframe 0.80" in svg


def test_index_lists_runs(tmp_path):
    _run_dir(tmp_path, "r1")
    _run_dir(tmp_path, "r2")
    page = render_index(tmp_path).read_text()
    assert 'href="r1/index.html"' in page and 'href="r2/index.html"' in page
