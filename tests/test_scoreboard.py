import json

import pytest

from castbook.dag import Executor, StepCache, shot_seed
from castbook.scoreboard import render, summarize
from castbook.store import LocalStore
from castbook.workflow import load_workflow
from tests.test_dag import FakeBackend, _script, _verdict


def _arm(tmp_path, ref, backend=None, **kw):
    r = Executor(load_workflow(ref), backend or FakeBackend(), StepCache(LocalStore(tmp_path / "store"))).run(
        _script(3, end=True), b"portrait", [1.0, 0.0]
    )
    return {**r.to_dict(), "request_id": f"req_{ref}"}


def test_summary_counts_acceptance_first_try_and_warm_cost(tmp_path):
    def clip_rule(prompt, seed):
        return _verdict("fail", 0.3) if seed == shot_seed(11, 1, 0) else _verdict("pass", 0.6)

    s = summarize(_arm(tmp_path, "keyframe_i2v@2", FakeBackend(rules={"clip": clip_rule})))
    assert s["accepted"] == 3 and s["first_try"] == 2  # shot 2's clip passed on the re-roll
    assert s["n_attempts"] == 3 + 4  # 3 keyframes, 4 clips
    assert s["warm_gpu_s"] == pytest.approx(70.0)
    assert s["usd_per_accepted_s"] == pytest.approx(s["warm_usd"] / (3 * 81 / 16), rel=1e-2)  # rounded
    assert s["min_p10"] == pytest.approx(0.6)


def test_warm_cost_counts_cache_hits(tmp_path):
    a = summarize(_arm(tmp_path, "keyframe_i2v@2"))
    b = summarize(_arm(tmp_path, "keyframe_i2v@2"))  # second run: all hits, billed nothing
    assert b["billed_usd"] == 0 and b["warm_usd"] == a["warm_usd"] > 0


def test_unverifiable_clips_are_not_accepted(tmp_path):
    rules = {"clip": lambda p, s: _verdict("unverifiable", None)}
    s = summarize(_arm(tmp_path, "lastframe_chain@1", FakeBackend(rules=rules)))
    assert s["accepted"] == 0 and s["unverifiable"] == 3 and s["usd_per_accepted_s"] is None


def test_render_writes_one_page_with_every_arm(tmp_path):
    arms = [summarize(_arm(tmp_path, ref)) for ref in ("keyframe_i2v@2", "lastframe_chain@1", "keyframe_flf@1")]
    (tmp_path / "keyframe_i2v@2").mkdir()
    (tmp_path / "keyframe_i2v@2" / "final.mp4").write_bytes(b"\x00mp4")
    page = render(tmp_path, arms, _script(3, end=True).model_dump()).read_text()
    for ref in ("keyframe_i2v@2", "lastframe_chain@1", "keyframe_flf@1"):
        assert ref in page
    assert page.count("<video") == 3 and "data:video/mp4;base64," in page
    json.dumps(arms)  # summaries are what summary.json stores


def test_short_error_keeps_the_last_line():
    from castbook.scoreboard import _short_error

    tb = "ExecutionError: remote failed\nTraceback (most recent call last):\n  File x\n\n"
    tb += "torch.OutOfMemoryError: CUDA out of memory.\n"
    assert _short_error(tb) == "torch.OutOfMemoryError: CUDA out of memory."
    assert _short_error(None) == "no clip"
    assert len(_short_error("x" * 500)) == 200
