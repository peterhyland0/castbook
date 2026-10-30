import numpy as np
import pytest

from castbook.identity import (
    GateConfig,
    character_embedding,
    cosine,
    face_px,
    frame_status,
    is_small,
    score_frames,
    verdict,
)


def _unit(*xs):
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_cosine_of_same_and_orthogonal():
    assert cosine(_unit(1, 0), _unit(2, 0)) == pytest.approx(1.0)
    assert cosine(_unit(1, 0), _unit(0, 1)) == pytest.approx(0.0)


def test_character_embedding_is_normalized_mean():
    emb = character_embedding([_unit(1, 0), _unit(0, 1)])
    assert np.linalg.norm(emb) == pytest.approx(1.0)
    assert cosine(emb, _unit(1, 1)) == pytest.approx(1.0)


def test_score_frames_aggregates_and_counts_missing_faces():
    ref = _unit(1, 0)
    frames = [_unit(1, 0), None, _unit(0, 1), _unit(1, 1)]
    s = score_frames(ref, frames)
    assert s.n_frames == 4
    assert s.face_rate == pytest.approx(0.75)
    assert s.min == pytest.approx(0.0)
    assert s.mean == pytest.approx((1.0 + 0.0 + np.sqrt(0.5)) / 3)
    assert s.min <= s.p10 <= s.mean


def test_score_frames_with_no_faces():
    s = score_frames(_unit(1, 0), [None, None])
    assert s.face_rate == 0.0 and s.min is None and s.mean is None


def test_zero_embedding_rejected():
    with pytest.raises(ValueError):
        cosine(np.zeros(3), _unit(1, 0, 0))


def test_profile_frames_are_counted_but_not_scored():
    ref = _unit(1, 0)
    frames = [_unit(1, 0), _unit(1, 0.2), _unit(0, 1), None]
    yaws = [5.0, -30.0, 80.0, None]
    s = score_frames(ref, frames, yaws, max_yaw=45)
    assert s.n_scored == 2
    assert s.profile_rate == pytest.approx(0.25)
    assert s.face_rate == pytest.approx(0.75)
    assert s.min > 0.9  # the 80° frame (cosine 0) no longer drags the minimum down


def test_without_max_yaw_every_face_is_scored():
    s = score_frames(_unit(1, 0), [_unit(1, 0), _unit(0, 1)], [0.0, 80.0])
    assert s.n_scored == 2 and s.profile_rate == 0.0 and s.min == pytest.approx(0.0)


def test_all_profile_is_unscorable_not_zero():
    s = score_frames(_unit(1, 0), [_unit(0, 1)], [-70.0], max_yaw=45)
    assert s.n_scored == 0 and s.mean is None and s.profile_rate == 1.0


def test_yaws_must_align():
    with pytest.raises(ValueError):
        score_frames(_unit(1, 0), [_unit(1, 0)], [0.0, 1.0])


def test_overlap_fraction():
    from castbook.identity import overlap_fraction

    face = (0, 0, 10, 10)
    assert overlap_fraction(face, (5, 0, 15, 10)) == pytest.approx(0.5)
    assert overlap_fraction(face, (20, 20, 30, 30)) == 0.0
    assert overlap_fraction(face, (-5, -5, 20, 20)) == pytest.approx(1.0)


def test_occluded_frames_are_counted_but_not_scored():
    ref = _unit(1, 0)
    s = score_frames(ref, [_unit(1, 0), _unit(0, 1)], [0.0, 0.0], 45, [0.0, 0.6], 0.2)
    assert s.n_scored == 1 and s.occluded_rate == pytest.approx(0.5) and s.min == pytest.approx(1.0)


def test_profile_takes_precedence_over_occlusion():
    from castbook.identity import frame_status

    assert frame_status(True, 80.0, 0.9, 45, 0.2) == "profile"
    assert frame_status(True, 10.0, 0.9, 45, 0.2) == "occluded"
    assert frame_status(False, None, None, 45, 0.2) == "no_face"


def test_verdicts():
    from castbook.identity import GateConfig, verdict

    gate = GateConfig(metric="p10", min_score=0.5, min_coverage=0.5)
    ref = _unit(1, 0)
    good = score_frames(ref, [_unit(1, 0.1)] * 4, [0.0] * 4, 45)
    assert verdict(good, gate).status == "pass"
    bad = score_frames(ref, [_unit(0.3, 1)] * 4, [0.0] * 4, 45)
    assert verdict(bad, gate).status == "fail"
    # 3 of 4 frames in profile: 25% coverage, below the 50% floor, so no claim either way.
    mostly_profile = score_frames(ref, [_unit(0.3, 1)] * 4, [0.0, 80.0, 80.0, 80.0], 45)
    v = verdict(mostly_profile, gate)
    assert v.status == "unverifiable" and any("profile" in r for r in v.reasons)
    assert verdict(score_frames(ref, [None, None]), gate).status == "unverifiable"


def test_profile_and_occlusion_rates_can_overlap():
    s = score_frames(_unit(1, 0), [_unit(1, 0)] * 2, [80.0, 0.0], 45, [0.9, 0.0], 0.2)
    assert s.profile_rate == pytest.approx(0.5) and s.occluded_rate == pytest.approx(0.5) and s.n_scored == 1


def test_small_faces_are_not_scored():
    ref = np.array([1.0, 0.0])
    embs = [np.array([1.0, 0.0]), np.array([0.3, 1.0]), np.array([0.3, 1.0])]
    s = score_frames(ref, embs, widths=[120, 55, 60], min_face_px=64)
    assert s.n_scored == 1 and s.small_rate == pytest.approx(2 / 3) and s.p10 == pytest.approx(1.0)
    assert verdict(s, GateConfig()).status == "unverifiable"
    assert any("narrower than 64 px" in r for r in verdict(s, GateConfig()).reasons)


def test_min_face_px_unset_scores_everything():
    ref = np.array([1.0, 0.0])
    s = score_frames(ref, [np.array([1.0, 0.0])], widths=[10])
    assert s.n_scored == 1 and s.small_rate == 0


def test_small_takes_precedence_over_profile():
    assert frame_status(True, 80, None, 45, None, 40, 64) == "small"
    assert frame_status(True, 80, None, 45, None, 100, 64) == "profile"
    assert face_px((10, 0, 74, 80)) == 64 and not is_small(64, 64) and is_small(63.9, 64)


def test_blocking_cause_picks_the_largest_blocker():
    from castbook.identity import blocking_cause

    assert blocking_cause({"face_rate": 1.0, "small_rate": 1.0, "profile_rate": 0.2}) == "small"
    assert blocking_cause({"face_rate": 1.0, "small_rate": 0.1, "profile_rate": 0.6}) == "profile"
    assert blocking_cause({"face_rate": 0.3}) == "no_face"
    assert blocking_cause({"face_rate": 1.0, "small_rate": 0.5, "profile_rate": 0.5}) == "small"  # tie
    assert blocking_cause({"face_rate": 1.0}) is None and blocking_cause({"p10": 0.7}) is None
