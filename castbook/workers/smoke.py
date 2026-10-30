"""CPU smoke check for the diffusion image: catches missing libraries and weight-path
mistakes before paying for an H100 cold start that would crash in @modal.enter."""

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, app, diffusion_image, models_vol


@app.function(image=diffusion_image, volumes={MODELS_DIR: models_vol}, cpu=2, memory=8192, timeout=900)
def smoke() -> dict:
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
