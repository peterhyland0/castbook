"""CPU smoke check for the diffusion image: catches missing libraries and weight-path
mistakes before paying for an H100 cold start that would crash in @modal.enter."""

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, app, diffusion_image, judge_image, models_vol


@app.function(image=diffusion_image, volumes={MODELS_DIR: models_vol}, cpu=2, memory=8192, timeout=900)
def smoke() -> dict:
    import inspect

    import diffusers
    import torch
    import transformers
    from diffusers import (  # noqa: F401
        AutoencoderKLWan,
        QwenImageEditPlusPipeline,
        WanImageToVideoPipeline,
        ZImagePipeline,
    )
    from safetensors import safe_open
    from transformers import AutoProcessor, AutoTokenizer

    report = {
        "torch": str(torch.__version__),
        "diffusers": str(diffusers.__version__),
        "transformers": str(transformers.__version__),
        # keyframe_flf passes the end keyframe as `last_image`; fail here, not after an H100 cold start
        "wan_last_image": "last_image" in inspect.signature(WanImageToVideoPipeline.__call__).parameters,
    }
    AutoProcessor.from_pretrained(f"{MODELS['qwen-image-edit-2511'].local_dir}/processor")
    AutoTokenizer.from_pretrained(f"{MODELS['wan2.2-i2v-a14b'].local_dir}/tokenizer")
    AutoTokenizer.from_pretrained(f"{MODELS['z-image-turbo'].local_dir}/tokenizer")
    for name in ("qwen-image-edit-2511-lightning", "wan2.2-i2v-a14b-lightning"):
        src = MODELS[name]
        for f in src.files:
            with safe_open(f"{src.local_dir}/{f}", framework="pt") as st:
                keys = list(st.keys())
            report[f"{name}:{f.split('/')[-1]}"] = {"n_keys": len(keys), "sample": keys[:2]}
    return report


@app.function(image=judge_image, volumes={MODELS_DIR: models_vol}, cpu=2, memory=4096, timeout=600)
def smoke_judge() -> dict:
    """Same idea for the judge image: InsightFace + MediaPipe import and model setup."""
    from pathlib import Path

    import insightface
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    from castbook.workers.judge import HAND_MODEL_URL

    hand_model = Path(MODELS_DIR, "mediapipe", "hand_landmarker.task")
    if not hand_model.exists():
        import urllib.request

        hand_model.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(HAND_MODEL_URL, hand_model)
        models_vol.commit()
    vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(hand_model)), num_hands=2)
    )
    return {"insightface": str(insightface.__version__), "mediapipe": str(mp.__version__)}
