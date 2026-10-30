import pytest

from castbook.adapters.base import CAPABILITIES, Capabilities, ConditioningError, Kind, plan_conditioning

LEMON_LIKE = Capabilities(
    kind=Kind.IMAGE_TO_VIDEO,
    max_refs=10,
    refs_xor_first_frame=True,
    supports_first_frame=True,
    supports_last_frame=True,
)
CHERRY_LIKE = Capabilities(kind=Kind.IMAGE_TO_VIDEO, max_refs=8)


def test_first_frame_wins_when_exclusive():
    c = plan_conditioning(LEMON_LIKE, refs=("char", "outfit"), first_frame="kf")
    assert c.refs == () and c.first_frame == "kf"


def test_refs_kept_without_first_frame_and_capped():
    c = plan_conditioning(LEMON_LIKE, refs=tuple(f"r{i}" for i in range(12)))
    assert len(c.refs) == 10


def test_models_without_frame_inputs_reject_frames():
    with pytest.raises(ConditioningError):
        plan_conditioning(CHERRY_LIKE, refs=("char",), first_frame="kf")


def test_last_frame_needs_first_frame():
    with pytest.raises(ConditioningError):
        plan_conditioning(LEMON_LIKE, last_frame="end")


def test_wan_supports_first_last_frame():
    c = plan_conditioning(CAPABILITIES["wan2.2-i2v-a14b"], first_frame="a", last_frame="b")
    assert (c.first_frame, c.last_frame) == ("a", "b")
