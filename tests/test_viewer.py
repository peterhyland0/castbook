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


def test_profile_frames_get_a_band_and_grey_marker():
    per_frame = [
        {"frame": 0, "sim": 0.7, "yaw": 5.0, "profile": False},
        {"frame": 40, "sim": 0.05, "yaw": 70.0, "profile": True},
        {"frame": 80, "sim": 0.6, "yaw": 10.0, "profile": False},
    ]
    svg = identity_chart_svg(per_frame, 81, 0.8)
    assert 'fill="var(--band)"' in svg
    assert "profile · not scored" in svg
    assert svg.count('fill="var(--text-muted)"') == 1


def test_verdict_chips_and_occlusion_marker(tmp_path):
    d = _run_dir(tmp_path, "r3")
    rec = json.loads((d / "record.json").read_text())
    rec["verdicts"] = {
        "keyframe": {
            "status": "pass",
            "metric": "p10",
            "value": 0.76,
            "threshold": 0.5,
            "coverage": 1.0,
            "reasons": ["p10 0.76 ≥ 0.50"],
        },
        "clip": {
            "status": "unverifiable",
            "metric": "p10",
            "value": 0.6,
            "threshold": 0.5,
            "coverage": 0.24,
            "reasons": ["only 5/21 frames scorable (need 50%)"],
        },
    }
    rec["identity"]["clip"]["occluded_rate"] = 0.5
    rec["identity"]["clip"]["max_yaw"] = 45
    rec["identity"]["clip"]["profile_rate"] = 0.2
    rec["identity"]["clip"]["n_scored"] = 1
    rec["identity"]["clip_per_frame"][2].update({"occluded": True, "hand_overlap": 0.4, "status": "occluded"})
    (d / "record.json").write_text(json.dumps(rec))
    page = render_run(d).read_text()
    assert 'class="chip pass"' in page and 'class="chip unverifiable"' in page
    assert "Re-prompt so the face stays visible" in page
    assert '<path d="M' in page  # diamond marker for the occluded frame
    assert "hand on face 50%" in page
    assert 'class="chip unverifiable"' in render_index(tmp_path).read_text()
