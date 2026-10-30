"""Weight downloads into the models Volume (CPU only)."""

import time
from pathlib import Path

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, app, download_image, models_vol


@app.function(image=download_image, volumes={MODELS_DIR: models_vol}, cpu=4, memory=8192, timeout=3 * 3600)
def download(name: str) -> dict:
    from huggingface_hub import hf_hub_download, snapshot_download

    src = MODELS[name]
    t0 = time.perf_counter()
    if src.files:
        for f in src.files:
            hf_hub_download(src.repo_id, f, revision=src.revision, local_dir=src.local_dir)
    else:
        snapshot_download(
            src.repo_id,
            revision=src.revision,
            local_dir=src.local_dir,
            ignore_patterns=["*.mp4", "*.gif", "*.pdf", "examples/*", "assets/*"],
        )
    models_vol.commit()
    size = sum(p.stat().st_size for p in Path(src.local_dir).rglob("*") if p.is_file())
    return {
        "name": name,
        "repo": src.repo_id,
        "gb": round(size / 1e9, 2),
        "seconds": round(time.perf_counter() - t0, 1),
    }
