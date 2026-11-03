import json
import threading

import pytest

from castbook.dag import Executor, StepCache, billing, judge_key, shot_seed
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
        self.clip_inputs: list[tuple[bytes, bytes | None]] = []  # (first_frame, last_frame) per clip call
        self.keyframe_refs: list[list[bytes]] = []
        self.last_frames = 0
        self._lock = threading.Lock()

    def _emit(self, kind, prompt, seed):
        with self._lock:
            self.calls[kind] += 1
        if (kind, seed) in self.fail_on:
            raise RuntimeError(f"{kind} exploded")
        return json.dumps({"kind": kind, "prompt": prompt, "seed": seed}).encode(), dict(TIMING)

    def keyframe(self, refs, prompt, seed, params):
        with self._lock:
            self.keyframe_refs.append(refs)
        return self._emit("keyframe", prompt, seed)

    def clip(self, first_frame, prompt, seed, params, last_frame=None):
        with self._lock:
            self.clip_inputs.append((first_frame, last_frame))
        return self._emit("clip", prompt, seed)

    def last_frame(self, video):
        with self._lock:
            self.last_frames += 1
        return b"last-of:" + video, {**TIMING, "gpu": "CPU", "usd": 0.0}

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


def _script(n=3, seed=11, end=False):
    return Script(
        character="c01",
        seed=seed,
        shots=[
            ShotSpec(id=f"s{i}", keyframe=f"kf {i}", motion=f"mv {i}", end=f"end {i}" if end else None)
            for i in range(n)
        ],
    )


def _run(tmp_path, backend, script=None, wf=WF, **kw):
    ex = Executor(wf, backend, StepCache(LocalStore(tmp_path)), **kw)
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


def test_hits_still_report_what_the_artifact_cost(tmp_path):
    _run(tmp_path, FakeBackend(), _script(1))
    r = _run(tmp_path, FakeBackend(), _script(1))
    a = r.shots[0].clip_attempts[0]
    assert a.cache == "hit" and a.timing["infer_s"] == TIMING["infer_s"]


def test_judge_key_ignores_unset_settings():
    cfg = {"sample_every": 4, "max_yaw": 45}
    wf1 = Executor(WF, FakeBackend(), StepCache(LocalStore("/nonexistent"))).judge_cfg
    assert "min_face_px" not in wf1  # @1 predates min_face_px, so its judge keys are unchanged
    wf2 = Executor(load_workflow("keyframe_i2v@2"), FakeBackend(), StepCache(LocalStore("/nonexistent"))).judge_cfg
    assert wf2["min_face_px"] == 64
    assert judge_key(cfg, "k") != judge_key({**cfg, "min_face_px": 64}, "k")


def test_i2v_v2_reuses_v1_generations(tmp_path):
    _run(tmp_path, FakeBackend(), _script(2))
    b = FakeBackend()
    r = _run(tmp_path, b, _script(2), wf=load_workflow("keyframe_i2v@2"))
    assert b.calls == {"keyframe": 0, "clip": 0, "stitch": 0}  # same generations, re-judged only
    assert r.final_key is not None


def test_flf_makes_an_end_keyframe_from_start_plus_portrait(tmp_path):
    wf = load_workflow("keyframe_flf@1")
    b = FakeBackend()
    r = _run(tmp_path, b, _script(2, end=True), wf=wf)
    assert [s.status for s in r.shots] == ["pass", "pass"]
    assert b.calls == {"keyframe": 4, "clip": 2, "stitch": 1}
    for shot in r.shots:
        assert shot.end_keyframe_key and shot.end_keyframe_attempts[0].prompt.startswith("Picture 1 a few seconds")
    start = LocalStore(tmp_path).get(r.shots[0].keyframe_key).data
    assert [b"portrait"] in b.keyframe_refs and [start, b"portrait"] in b.keyframe_refs
    assert all(last is not None for _, last in b.clip_inputs)


def test_flf_gate_covers_the_end_keyframe(tmp_path):
    def rule(prompt, seed):
        return _verdict("fail", 0.3) if "a few seconds" in prompt else _verdict("pass")

    b = FakeBackend(rules={"keyframe": rule})
    r = _run(tmp_path, b, _script(1, end=True), wf=load_workflow("keyframe_flf@1"))
    assert len(r.shots[0].end_keyframe_attempts) == 3 and r.shots[0].status == "degraded"


def test_flf_rejects_scripts_without_end_prompts(tmp_path):
    with pytest.raises(ValueError, match="end"):
        _run(tmp_path, FakeBackend(), _script(2), wf=load_workflow("keyframe_flf@1"))


def test_lastframe_chain_starts_each_shot_from_the_previous_clip(tmp_path):
    b = FakeBackend()
    r = _run(tmp_path, b, _script(3), wf=load_workflow("lastframe_chain@1"))
    assert [s.status for s in r.shots] == ["pass"] * 3
    assert b.calls == {"keyframe": 1, "clip": 3, "stitch": 1} and b.last_frames == 2
    store = LocalStore(tmp_path)
    for prev, shot in zip(r.shots, r.shots[1:], strict=False):
        assert not shot.keyframe_attempts
        assert store.get(shot.keyframe_key).data == b"last-of:" + store.get(prev.clip_key).data
    assert all(last is None for _, last in b.clip_inputs)


def test_lastframe_chain_stops_after_a_shot_with_no_clip(tmp_path):
    b = FakeBackend(fail_on={("clip", shot_seed(11, 1, 0))})
    r = _run(tmp_path, b, _script(3), wf=load_workflow("lastframe_chain@1"))
    assert [s.status for s in r.shots] == ["pass", "error", "error"]
    assert "previous shot" in r.shots[2].error and r.final_key is not None


def test_small_face_reprompt_asks_for_tighter_framing(tmp_path):
    wf = load_workflow("keyframe_flf@2")
    clip = wf.steps["clip"].retry
    small = clip.reprompt_by_cause["small"]
    assert small != clip.reprompt_suffix

    def judge(p, s):
        if p.endswith(small):
            return _verdict("pass")
        r = _verdict("unverifiable", None)
        r["score"] = {"face_rate": 1.0, "small_rate": 1.0, "profile_rate": 0.0}
        return r

    r = _run(tmp_path, FakeBackend(rules={"clip": judge}), _script(1, end=True), wf=wf)
    clips = r.shots[0].clip_attempts
    assert [a.verdict["status"] for a in clips] == ["unverifiable", "pass"]
    assert clips[1].prompt.endswith(small)


def test_other_causes_keep_the_default_suffix(tmp_path):
    wf = load_workflow("keyframe_flf@2")
    default = wf.steps["clip"].retry.reprompt_suffix

    def judge(p, s):
        if p.endswith(default):
            return _verdict("pass")
        r = _verdict("unverifiable", None)
        r["score"] = {"face_rate": 1.0, "small_rate": 0.0, "profile_rate": 0.8}
        return r

    r = _run(tmp_path, FakeBackend(rules={"clip": judge}), _script(1, end=True), wf=wf)
    assert r.shots[0].clip_attempts[1].prompt.endswith(default)


def test_flf_v2_reuses_v1_first_attempts(tmp_path):
    """Same prompts and params on attempt 0, so @2 only pays for attempts whose re-prompt changed."""
    _run(tmp_path, FakeBackend(), _script(2, end=True), wf=load_workflow("keyframe_flf@1"))
    b = FakeBackend()
    _run(tmp_path, b, _script(2, end=True), wf=load_workflow("keyframe_flf@2"))
    assert b.calls == {"keyframe": 0, "clip": 0, "stitch": 0}


WF4 = load_workflow("keyframe_flf@4")
SMALL_KF = WF4.steps["keyframe"].retry.reprompt_by_cause["small"]


def _face(px):
    """A passing image verdict with a detected face `px` wide."""
    r = _verdict("pass")
    r["frame"] = {"face_px": px}
    return r


def _clip_sizes(backend_calls):
    return [(p["width"], p["height"]) for p in backend_calls]


class SizedBackend(FakeBackend):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.clip_params: list[dict] = []

    def clip(self, first_frame, prompt, seed, params, last_frame=None):
        self.clip_params.append(params)
        return super().clip(first_frame, prompt, seed, params, last_frame)


def test_small_keyframe_is_reframed_before_any_clip(tmp_path):
    # 80 px in a 1248-wide keyframe is ~53 px in an 832 clip: re-frame at the keyframe step.
    kf = {"keyframe": lambda p, s: _face(120 if p.endswith(SMALL_KF) else 80)}
    b = SizedBackend(rules=kf)
    r = _run(tmp_path, b, _script(1, end=True), wf=WF4)
    kfs = r.shots[0].keyframe_attempts
    assert [a.framing for a in kfs] == ["small", None] and kfs[1].prompt.endswith(SMALL_KF)
    assert r.shots[0].keyframe_key == kfs[1].key
    assert _clip_sizes(b.clip_params) == [(832, 480)] and r.shots[0].clip_size == (832, 480)
    assert r.shots[0].status == "pass"


def test_keyframe_that_stays_small_gets_a_720p_clip(tmp_path):
    b = SizedBackend(rules={"keyframe": lambda p, s: _face(80)})
    r = _run(tmp_path, b, _script(1, end=True), wf=WF4)
    assert len(r.shots[0].keyframe_attempts) == WF4.steps["keyframe"].retry.max_attempts
    assert r.shots[0].clip_size == (1248, 720) and _clip_sizes(b.clip_params) == [(1248, 720)]
    assert r.shots[0].status == "pass"  # identity passed; small framing alone doesn't degrade the shot


def test_too_small_even_at_720p_uses_the_largest_size(tmp_path):
    b = SizedBackend(rules={"keyframe": lambda p, s: _face(40)})
    r = _run(tmp_path, b, _script(1, end=True), wf=WF4)
    assert r.shots[0].clip_size == (1248, 720)


def test_clip_size_uses_the_smaller_of_start_and_end_faces(tmp_path):
    rules = {"keyframe": lambda p, s: _face(70 if p.startswith("Picture 1") else 140)}
    b = SizedBackend(rules=rules)
    r = _run(tmp_path, b, _script(1, end=True), wf=WF4)
    assert r.shots[0].clip_size == (1248, 720)


def test_unknown_face_size_keeps_the_cheapest_clip_and_skips_reframing(tmp_path):
    b = SizedBackend()  # verdicts carry no face size
    r = _run(tmp_path, b, _script(1, end=True), wf=WF4)
    assert len(r.shots[0].keyframe_attempts) == 1 and r.shots[0].clip_size == (832, 480)


def test_without_framing_clip_size_is_untouched(tmp_path):
    b = SizedBackend(rules={"keyframe": lambda p, s: _face(40)})
    r = _run(tmp_path, b, _script(1, end=True), wf=load_workflow("keyframe_flf@2"))
    assert r.shots[0].clip_size is None and _clip_sizes(b.clip_params) == [(832, 480)]
    assert len(r.shots[0].keyframe_attempts) == 1


def test_rank_prefers_well_framed_passes():
    from castbook.dag import Attempt, best

    v = {"status": "pass", "value": 0.7}
    small = Attempt("keyframe", 0, 1, "p", "k0", "miss", {**v, "value": 0.9}, {}, None, framing="small")
    ok = Attempt("keyframe", 1, 2, "p", "k1", "miss", v, {}, None)
    assert best([small, ok]) is ok
