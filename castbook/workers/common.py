"""Shared Modal app, images and volumes.

Heavy libraries (torch, diffusers, insightface) are imported inside @modal.enter
or methods, so every image can import this package without carrying them.
"""

import time
from pathlib import Path

import modal

from castbook.config import ARTIFACTS_DIR, ARTIFACTS_VOLUME, MODELS_DIR, MODELS_VOLUME
from castbook.costs import StepTiming

app = modal.App("castbook")

models_vol = modal.Volume.from_name(MODELS_VOLUME, create_if_missing=True, version=2)
artifacts_vol = modal.Volume.from_name(ARTIFACTS_VOLUME, create_if_missing=True, version=2)

_REPO = Path(__file__).resolve().parents[2]
_CORE_DEPS = ("numpy", "pydantic", "pyyaml")


def _with_source(image: modal.Image) -> modal.Image:
    return (
        image.add_local_python_source("castbook")
        .add_local_dir(_REPO / "workflows", "/root/workflows")
        .add_local_dir(_REPO / "evals", "/root/evals")
    )


cpu_image = _with_source(modal.Image.debian_slim(python_version="3.12").uv_pip_install(*_CORE_DEPS))

download_image = _with_source(
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(*_CORE_DEPS, "huggingface_hub[hf_xet]")
    .env({"HF_HUB_DISABLE_TELEMETRY": "1"})
)

diffusion_image = _with_source(
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git")
    .uv_pip_install(
        *_CORE_DEPS,
        "torch>=2.8",
        "torchvision",  # Qwen-Image-Edit's Qwen2.5-VL processor needs it
        "diffusers>=0.36",
        "transformers",
        "accelerate",
        "peft",
        "safetensors",
        "sentencepiece",
        "ftfy",
        "imageio[ffmpeg]",
        "pillow",
        "huggingface_hub[hf_xet]",
    )
    .env({"HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_OFFLINE": "1"})
)

judge_image = _with_source(
    modal.Image.debian_slim(python_version="3.12")
    # libegl1/libgles2: MediaPipe's task runtime links against them even on CPU.
    .apt_install("build-essential", "libgl1", "libglib2.0-0", "libegl1", "libgles2", "ffmpeg")
    .uv_pip_install(
        *_CORE_DEPS,
        "insightface==0.7.3",
        "mediapipe",
        "onnxruntime",
        "opencv-python-headless",
        "imageio",
        "av",
        "pillow",
    )
)


class TimedWorker:
    """Mixin: records model-load time once and reports it on the first call only.

    Subclasses call `self._start_load()` / `self._end_load()` in @modal.enter and
    `self._timing(infer_s)` when returning a result.
    """

    GPU = "CPU"

    def _start_load(self) -> None:
        self._t0 = time.perf_counter()

    def _end_load(self) -> None:
        self._load_s = time.perf_counter() - self._t0
        self._cold = True

    def _timing(self, infer_s: float) -> dict:
        cold = getattr(self, "_cold", False)
        self._cold = False
        load_s = self._load_s if cold else 0.0
        return StepTiming(gpu=self.GPU, load_s=load_s, infer_s=infer_s, cold=cold).to_dict()


__all__ = [
    "app",
    "models_vol",
    "artifacts_vol",
    "cpu_image",
    "download_image",
    "diffusion_image",
    "judge_image",
    "TimedWorker",
    "MODELS_DIR",
    "ARTIFACTS_DIR",
]
