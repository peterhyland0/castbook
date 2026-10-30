import pytest
import yaml

from castbook.adapters.base import CAPABILITIES
from castbook.config import GPU_USD_PER_SECOND, MODELS
from castbook.costs import StepTiming, total_usd
from castbook.workflow import WORKFLOWS_DIR, load_workflow


@pytest.mark.parametrize("path", sorted(WORKFLOWS_DIR.glob("*.yaml")), ids=lambda p: p.name)
def test_every_workflow_loads_and_names_known_models(path):
    wf = load_workflow(path.stem)
    for step in wf.steps.values():
        if step.model:
            assert step.model in MODELS
            assert step.model in CAPABILITIES


def test_workflow_ref_must_match_filename(tmp_path):
    (tmp_path / "x@1.yaml").write_text(yaml.safe_dump({"id": "x", "version": 2, "steps": {}}))
    with pytest.raises(ValueError):
        load_workflow("x@1", tmp_path)


def test_costs_only_charge_load_on_cold_call():
    cold = StepTiming(gpu="H100", load_s=100, infer_s=20, cold=True)
    warm = StepTiming(gpu="H100", load_s=0, infer_s=20, cold=False)
    assert cold.usd == pytest.approx(120 * GPU_USD_PER_SECOND["H100"], abs=1e-6)
    assert total_usd([cold, warm]) == pytest.approx(140 * GPU_USD_PER_SECOND["H100"], abs=1e-5)
