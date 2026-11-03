import pytest

from castbook.config import GPU_USD_PER_SECOND, MEASURED
from castbook.runs import estimate
from castbook.workflow import load_workflow


def test_720p_clips_scale_between_linear_and_quadratic():
    lo2, lo3 = (estimate(load_workflow(f"keyframe_flf@{v}"), 3) for v in (2, 3))
    scale = 1248 * 720 / (832 * 480)
    clip = MEASURED["clip"]["infer_s"] * GPU_USD_PER_SECOND["H100"]
    assert lo3["usd_low"] - lo2["usd_low"] == pytest.approx(3 * clip * (scale - 1), abs=1e-3)
    assert lo3["usd_high"] - lo2["usd_high"] == pytest.approx(3 * 2 * clip * (scale**2 - 1), abs=1e-3)


def test_measured_resolution_is_unscaled():
    assert estimate(load_workflow("keyframe_flf@1"), 3) == estimate(load_workflow("keyframe_flf@2"), 3)


def test_per_shot_sizes_price_cheapest_low_and_largest_high():
    e2, e3, e4 = (estimate(load_workflow(f"keyframe_flf@{v}"), 3) for v in (2, 3, 4))
    assert e4["usd_low"] == e2["usd_low"]
    assert e4["usd_high"] > e3["usd_high"]  # same clip ceiling as @3, plus 5 keyframe attempts instead of 3
