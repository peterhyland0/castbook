import json
import threading

import pytest

from castbook.dag import Executor, StepCache, billing, shot_seed
from castbook.shots import Script, ShotSpec
from castbook.store import LocalStore
from castbook.workflow import load_workflow

WF = load_workflow("keyframe_i2v@1")
TIMING = {"gpu": "H100", "load_s": 0.0, "infer_s": 10.0, "cold": False, "gpu_seconds": 10.0, "usd": 0.011}


def _verdict(status, value=0.7):
    return {
        "verdict": {
            "status": status,
            "metric": "p10",
            "value": value,
            "threshold": 0.5,
            "coverage": 1.0,
            "reasons": [],
        },
        "score": {"p10": value},
    }


class FakeBackend:
    """Outputs encode (kind, prompt, seed) so the judge can be scripted per attempt.

    `rules` maps a kind to a function (prompt, seed) -> judge result.
    """

    def __init__(self, rules=None, fail_on=None):
        self.rules = rules or {}
        self.fail_on = fail_on or set()
        self.calls = {"keyframe": 0, "clip": 0, "stitch": 0}
        self._lock = threading.Lock()

    def _emit(self, kind, prompt, seed):
        with self._lock:
            self.calls[kind] += 1
        if (kind, seed) in self.fail_on:
            raise RuntimeError(f"{kind} exploded")
        return json.dumps({"kind": kind, "prompt": prompt, "seed": seed}).encode(), dict(TIMING)

    def keyframe(self, refs, prompt, seed, params):
        return self._emit("keyframe", prompt, seed)

    def clip(self, first_frame, prompt, seed, params):
        return self._emit("clip", prompt, seed)

    def _judge(self, data):
        d = json.loads(data)
        return self.rules.get(d["kind"], lambda p, s: _verdict("pass"))(d["prompt"], d["seed"])

    def score_image(self, reference, image, judge):
        return self._judge(image)

    def score_video(self, reference, video, judge):
        return self._judge(video)

    def stitch(self, clips, params):
        with self._lock:
            self.calls["stitch"] += 1
        return b"|".join(clips), {**TIMING, "gpu": "CPU", "usd": 0.0}


def _script(n=3, seed=11):
    return Script(
        character="c01", seed=seed, shots=[ShotSpec(id=f"s{i}", keyframe=f"kf {i}", motion=f"mv {i}") for i in range(n)]
    )


def _run(tmp_path, backend, script=None, **kw):
    ex = Executor(WF, backend, StepCache(LocalStore(tmp_path)), **kw)
    return ex.run(script or _script(), b"portrait", [1.0, 0.0])


def test_all_pass_first_try(tmp_path):
    b = FakeBackend()
    r = _run(tmp_path, b)
    assert [s.status for s in r.shots] == ["pass"] * 3
    assert b.calls == {"keyframe": 3, "clip": 3, "stitch": 1}
    assert r.final_key is not None


def test_failed_keyframe_is_rerolled_with_a_new_seed(tmp_path):
    first = shot_seed(11, 0, 0)
    b = FakeBackend(rules={"keyframe": lambda p, s: _verdict("fail", 0.2) if s == first else _verdict("pass")})
    r = _run(tmp_path, b, _script(1))
    kfs = r.shots[0].keyframe_attempts
    assert [a.verdict["status"] for a in kfs] == ["fail", "pass"]
    assert kfs[0].seed != kfs[1].seed
    assert r.shots[0].keyframe_key == kfs[1].key and r.shots[0].status == "pass"


def test_unverifiable_clip_is_reprompted_before_rerolling(tmp_path):
    suffix = WF.steps["clip"].retry.reprompt_suffix
    b = FakeBackend(
        rules={"clip": lambda p, s: _verdict("pass") if p.endswith(suffix) else _verdict("unverifiable", None)}
    )
    r = _run(tmp_path, b, _script(1))
    clips = r.shots[0].clip_attempts
    assert [a.verdict["status"] for a in clips] == ["unverifiable", "pass"]
    assert clips[1].prompt.endswith(suffix) and not clips[0].prompt.endswith(suffix)


def test_exhausted_attempts_keep_the_best_and_mark_degraded(tmp_path):
    scores = iter([0.30, 0.45])
    b = FakeBackend(rules={"clip": lambda p, s: _verdict("fail", next(scores))})
    r = _run(tmp_path, b, _script(1))
    shot = r.shots[0]
    assert len(shot.clip_attempts) == WF.steps["clip"].retry.max_attempts
    assert shot.status == "degraded"
    assert shot.clip_key == shot.clip_attempts[1].key  # 0.45 beats 0.30
    assert r.final_key is not None  # a degraded shot still makes the cut


def test_pass_beats_higher_scoring_unverifiable_when_keeping_best(tmp_path):
    results = iter([_verdict("unverifiable", 0.9), _verdict("fail", 0.3), _verdict("pass", 0.55)])
    b = FakeBackend(rules={"keyframe": lambda p, s: next(results)})
    r = _run(tmp_path, b, _script(1))
    assert r.shots[0].keyframe_key == r.shots[0].keyframe_attempts[2].key


def test_one_shot_erroring_does_not_fail_the_run(tmp_path):
    b = FakeBackend(fail_on={("clip", shot_seed(11, 1, 0))})
    r = _run(tmp_path, b)
    assert [s.status for s in r.shots] == ["pass", "error", "pass"]
    assert "exploded" in r.shots[1].error
    assert r.final_key is not None


def test_rerun_is_all_cache_hits(tmp_path):
    first = FakeBackend(rules={"keyframe": lambda p, s: _verdict("fail") if s % 1000 == 0 else _verdict("pass")})
    r1 = _run(tmp_path, first)
    again = FakeBackend(rules=first.rules)
    r2 = _run(tmp_path, again)
    assert again.calls == {"keyframe": 0, "clip": 0, "stitch": 0}
    assert r2.final_key == r1.final_key
    assert all(a.cache == "hit" for s in r2.shots for a in s.keyframe_attempts + s.clip_attempts)
    assert r2.gpu_usd == 0


def test_partial_resume_only_computes_the_missing_shot(tmp_path):
    _run(tmp_path, FakeBackend(), _script(2))
    b = FakeBackend()
    _run(tmp_path, b, _script(3))  # s0, s1 cached; s2 is new
    assert b.calls == {"keyframe": 1, "clip": 1, "stitch": 1}


def test_cancel_stops_new_work(tmp_path):
    r = _run(tmp_path, FakeBackend(), should_cancel=lambda: True)
    assert [s.status for s in r.shots] == ["cancelled"] * 3
    assert r.final_key is None


def test_events_report_each_attempt(tmp_path):
    events = []
    _run(tmp_path, FakeBackend(), _script(1), on_event=events.append)
    kinds = [e["type"] for e in events]
    assert kinds.count("attempt") == 2 and "stitched" in kinds


def test_billing_sums_by_gpu():
    b = billing([TIMING, {**TIMING, "load_s": 100.0, "cold": True, "usd": 0.12}])
    assert b["gpu_seconds"]["H100"] == pytest.approx(120.0)
    assert b["usd"] == pytest.approx(0.131)
