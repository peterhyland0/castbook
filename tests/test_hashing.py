from castbook.hashing import step_key


def _key(**overrides):
    args = dict(step="clip", model="wan", revision="main", params={"a": 1, "b": 0.1}, input_hashes=["x", "y"], seed=7)
    args.update(overrides)
    return step_key(**args)


def test_key_is_deterministic_and_ignores_param_order():
    assert _key() == _key(params={"b": 0.1, "a": 1})


def test_every_determining_field_changes_the_key():
    base = _key()
    for change in (
        {"step": "keyframe"},
        {"model": "ltx"},
        {"revision": "abc123"},
        {"params": {"a": 2, "b": 0.1}},
        {"input_hashes": ["x", "z"]},
        {"seed": 8},
    ):
        assert _key(**change) != base, change


def test_input_order_matters():
    # Reference 1 vs reference 2 are not interchangeable for an edit model.
    assert _key(input_hashes=["y", "x"]) != _key()


def test_float_noise_does_not_change_key():
    assert _key(params={"a": 1, "b": 0.1 + 1e-12}) == _key()
