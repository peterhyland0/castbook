import base64
from pathlib import Path

import pytest

from castbook import site
from castbook.config import GPU_USD_PER_SECOND


def _uri(data: bytes, mime: str = "video/mp4") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def test_media_is_stored_once_per_content(tmp_path):
    media = site.Media(tmp_path)
    assert media.put(b"clip", "final.mp4") == "media/final.mp4"
    clip, png = _uri(b"clip"), _uri(b"png", "image/png")
    page = f'<video src="{clip}"></video><video src="{clip}"></video><img src="{png}">'
    out = media.externalize(page)
    assert "base64" not in out
    assert out.count('src="../media/final.mp4"') == 2  # same bytes as an already stored file: reuse it
    png = [p for p in (tmp_path / "media").iterdir() if p.suffix == ".png"]
    assert len(png) == 1 and png[0].read_bytes() == b"png" and f"../media/{png[0].name}" in out
    assert sorted(p.name for p in (tmp_path / "media").iterdir()) == sorted(["final.mp4", png[0].name])


def _attempt(n, key, framing=None, face=80.0):
    return {"n": n, "key": key, "framing": framing, "face_px": face, "verdict": {"status": "pass", "value": 0.8}}


def test_reframe_pair_is_the_last_small_attempt_and_the_chosen_one():
    shot = {
        "shot_id": "s1",
        "keyframe_key": "k3",
        "keyframe_attempts": [
            _attempt(0, "k0"),
            _attempt(1, "k1", "small"),
            _attempt(2, "k2", "small", 79),
            _attempt(3, "k3", face=244),
        ],
    }
    before, after = site.reframe_pair(shot)
    assert before["key"] == "k2" and after["key"] == "k3"


def test_reframe_pair_rejects_a_shot_that_was_not_reframed():
    shot = {"shot_id": "s1", "keyframe_key": "k0", "keyframe_attempts": [_attempt(0, "k0")]}
    with pytest.raises(ValueError, match="not re-framed"):
        site.reframe_pair(shot)


def _timed(key, infer_s, cold=False):
    return {"key": key, "timing": {"gpu": "H100", "infer_s": infer_s, "cold": cold}}


def test_warm_clip_ratio_compares_warm_clips_by_size():
    small = {
        "clip_size": [832, 480],
        "keyframe_attempts": [],
        "clip_attempts": [_timed("a", 20), _timed("b", 200, cold=True)],
    }
    large = {"clip_size": [1248, 720], "keyframe_attempts": [], "clip_attempts": [_timed("c", 70), _timed("d", 74)]}
    shared = {"clip_size": [832, 480], "keyframe_attempts": [], "clip_attempts": [_timed("a", 20)]}  # counted once
    records = {"keyframe_flf@4": {"shots": [small, large]}, "keyframe_flf@2": {"shots": [shared]}}
    assert site.warm_clip_ratio(records) == pytest.approx(72 / 20)


def test_warm_clip_ratio_needs_two_sizes():
    one = {"clip_size": [832, 480], "clip_attempts": [_timed("a", 20)]}
    with pytest.raises(ValueError, match="two sizes"):
        site.warm_clip_ratio({"keyframe_flf@4": {"shots": [one]}})


def test_warm_keyframe_usd_skips_cold_starts():
    shot = {
        "keyframe_attempts": [_timed("a", 2.0), _timed("b", 50, cold=True)],
        "end_keyframe_attempts": [_timed("c", 3.0)],
    }
    assert site.warm_keyframe_usd({"w": {"shots": [shot]}}) == pytest.approx(2.5 * GPU_USD_PER_SECOND["H100"])


def test_run_dates_span_the_run_directories():
    paths = [Path("cafe_morning_20261030-181634"), Path("20261103T182431-abc"), Path("20261030T014009-x")]
    assert site.run_dates(paths) == "Oct 30 – Nov 3, 2026"
    assert site.run_dates(paths[:1]) == "Oct 30, 2026"


def test_failed_build_keeps_the_previous_site(tmp_path, monkeypatch):
    out = tmp_path / "site"
    out.mkdir()
    (out / "index.html").write_text("previous build")
    monkeypatch.setattr(site, "ARMS_RUN", tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        site.build(out)
    assert (out / "index.html").read_text() == "previous build"
    assert [p.name for p in tmp_path.iterdir()] == ["site"]  # no half-built directory left behind


RUNS = [site.ARMS_RUN, site.FRAMING_RUN, site.POSE_RUN, site.FIRST_RUN]


@pytest.mark.skipif(not all(p.exists() for p in RUNS), reason="needs the saved runs under out/ (not in git)")
def test_build_from_saved_runs(tmp_path):
    index = site.build(tmp_path / "site")
    page = index.read_text()
    assert "base64" not in page and "Did the chained workflow keep the character?" in page
    for deep in (tmp_path / "site/deep").glob("*.html"):
        assert "base64," not in deep.read_text()
