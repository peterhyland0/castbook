from castbook.store import LocalStore


def test_put_get_roundtrip(tmp_path):
    store = LocalStore(tmp_path)
    assert store.get("ab" * 32) is None
    store.put("ab" * 32, "clip.mp4", b"video", {"step": "clip"})
    art = store.get("ab" * 32)
    assert art.data == b"video"
    assert art.meta["step"] == "clip" and art.meta["name"] == "clip.mp4"


def test_partial_write_is_not_a_cache_hit(tmp_path):
    # Data file present but no meta.json, e.g. the container died mid-write.
    key = "cd" * 32
    d = tmp_path / key[:2] / key
    d.mkdir(parents=True)
    (d / "clip.mp4").write_bytes(b"half")
    assert LocalStore(tmp_path).get(key) is None
