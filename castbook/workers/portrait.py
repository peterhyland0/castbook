"""Text-to-image portraits for the golden character set (Z-Image Turbo, L40S)."""

import io
import time

import modal

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, TimedWorker, app, diffusion_image, models_vol


@app.cls(image=diffusion_image, gpu="L40S", volumes={MODELS_DIR: models_vol}, scaledown_window=120, timeout=1200)
class Portrait(TimedWorker):
    GPU = "L40S"

    @modal.enter()
    def load(self):
        self._start_load()
        import torch
        from diffusers import ZImagePipeline

        self.torch = torch
        self.pipe = ZImagePipeline.from_pretrained(MODELS["z-image-turbo"].local_dir, torch_dtype=torch.bfloat16).to(
            "cuda"
        )
        self._end_load()

    @modal.method()
    def generate(self, prompt: str, seed: int, width: int = 1024, height: int = 1024) -> dict:
        t0 = time.perf_counter()
        image = self.pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=9,  # Turbo: 8 DiT forwards
            guidance_scale=0.0,
            generator=self.torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return {"png": buf.getvalue(), "timing": self._timing(time.perf_counter() - t0)}
