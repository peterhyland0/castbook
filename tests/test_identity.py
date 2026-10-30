import numpy as np
import pytest

from castbook.identity import character_embedding, cosine, score_frames


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
