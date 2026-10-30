"""Multi-reference keyframes (Qwen-Image-Edit-2511, H100)."""

import io
import math
import time

import modal

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, TimedWorker, app, diffusion_image, models_vol

# Scheduler settings from the Qwen-Image-Lightning README for the 4-step LoRA.
_LIGHTNING_SCHEDULER = {
    "base_image_seq_len": 256,
    "base_shift": math.log(3),
    "invert_sigmas": False,
    "max_image_seq_len": 8192,
    "max_shift": math.log(3),
    "num_train_timesteps": 1000,
    "shift": 1.0,
    "shift_terminal": None,
    "stochastic_sampling": False,
    "time_shift_type": "exponential",
    "use_beta_sigmas": False,
    "use_dynamic_shifting": True,
    "use_exponential_sigmas": False,
    "use_karras_sigmas": False,
}


@app.cls(image=diffusion_image, gpu="H100", volumes={MODELS_DIR: models_vol}, scaledown_window=120, timeout=1800)
class Keyframe(TimedWorker):
    GPU = "H100"

    @modal.enter()
    def load(self):
        self._start_load()
        import torch
        from diffusers import FlowMatchEulerDiscreteScheduler, QwenImageEditPlusPipeline

        self.torch = torch
        self.pipe = QwenImageEditPlusPipeline.from_pretrained(
            MODELS["qwen-image-edit-2511"].local_dir, torch_dtype=torch.bfloat16
        ).to("cuda")
        self.full_scheduler = self.pipe.scheduler
        self.lightning_scheduler = FlowMatchEulerDiscreteScheduler.from_config(_LIGHTNING_SCHEDULER)
        lora = MODELS["qwen-image-edit-2511-lightning"]
        self.pipe.load_lora_weights(lora.local_dir, weight_name=lora.files[0], adapter_name="lightning")
        self._end_load()

    @modal.method()
    def edit(
        self,
        refs: list[bytes],
        prompt: str,
        seed: int,
        width: int,
        height: int,
        lightning: bool = True,
    ) -> dict:
        from PIL import Image

        t0 = time.perf_counter()
        images = [Image.open(io.BytesIO(b)).convert("RGB") for b in refs]
        if lightning:
            self.pipe.enable_lora()
            self.pipe.scheduler = self.lightning_scheduler
            steps, true_cfg = 4, 1.0
        else:
            self.pipe.disable_lora()
            self.pipe.scheduler = self.full_scheduler
            steps, true_cfg = 40, 4.0
        out = self.pipe(
            image=images,
            prompt=prompt,
            negative_prompt=" ",
            true_cfg_scale=true_cfg,
            guidance_scale=1.0,
            num_inference_steps=steps,
            width=width,
            height=height,
            generator=self.torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return {"png": buf.getvalue(), "timing": self._timing(time.perf_counter() - t0)}
