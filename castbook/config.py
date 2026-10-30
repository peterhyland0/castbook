"""Static configuration: model weights, volumes, GPU prices.

Everything a worker needs to find its weights lives here, so adding a model is
one entry in MODELS plus an adapter.
"""

from dataclasses import dataclass

MODELS_VOLUME = "castbook-models"
ARTIFACTS_VOLUME = "castbook-artifacts"
MODELS_DIR = "/models"
ARTIFACTS_DIR = "/artifacts"


@dataclass(frozen=True)
class WeightSource:
    repo_id: str
    revision: str = "main"
    # None = whole repo snapshot; otherwise just these files.
    files: tuple[str, ...] | None = None

    @property
    def local_dir(self) -> str:
        return f"{MODELS_DIR}/{self.repo_id}"


MODELS: dict[str, WeightSource] = {
    # Portraits for the golden set (text-to-image). Mage serves Z-Image Turbo too.
    "z-image-turbo": WeightSource("Tongyi-MAI/Z-Image-Turbo"),
    # Character sheet + keyframes (multi-reference edit).
    "qwen-image-edit-2511": WeightSource("Qwen/Qwen-Image-Edit-2511"),
    "qwen-image-edit-2511-lightning": WeightSource(
        "lightx2v/Qwen-Image-Edit-2511-Lightning",
        files=("Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",),
    ),
    # Image-to-video, MoE: transformer (high noise) + transformer_2 (low noise).
    "wan2.2-i2v-a14b": WeightSource("Wan-AI/Wan2.2-I2V-A14B-Diffusers"),
    "wan2.2-i2v-a14b-lightning": WeightSource(
        "lightx2v/Wan2.2-Lightning",
        files=(
            "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors",
            "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/low_noise_model.safetensors",
        ),
    ),
}

# Approximate Modal on-demand prices, USD per GPU-second (late 2026, from
# third-party aggregators). Verify against modal.com/pricing before quoting.
GPU_USD_PER_SECOND: dict[str, float] = {
    "H100": 0.001097,
    "A100-80GB": 0.000694,
    "L40S": 0.000542,
    "L4": 0.000222,
    "CPU": 0.0000131,  # ~1 physical core
}

# Measured step timings from the first single-shot run (H100, 4-step Lightning). Used to price runs before
# they start; update when the workers or settings change.
MEASURED: dict[str, dict] = {
    "keyframe": {"gpu": "H100", "load_s": 56.7, "infer_s": 5.4},
    "clip": {"gpu": "H100", "load_s": 227.2, "infer_s": 22.4},
}
