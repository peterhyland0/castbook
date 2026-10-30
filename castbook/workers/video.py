"""Image-to-video clips (Wan 2.2 I2V A14B, H100).

Wan 2.2 is a two-expert MoE: `transformer` handles high-noise steps and
`transformer_2` low-noise steps, so the Lightning LoRA ships one file per expert.
"""

import io
import tempfile
import time

import modal

from castbook.config import MODELS
from castbook.workers.common import MODELS_DIR, TimedWorker, app, diffusion_image, models_vol

NEGATIVE = (
    "blurry, distorted face, deformed, extra limbs, flicker, low quality, watermark, text, static image, morphing"
)


@app.cls(
    image=diffusion_image,
    gpu="H100",
    volumes={MODELS_DIR: models_vol},
    scaledown_window=120,
    max_containers=1,
    timeout=2400,
)
class Video(TimedWorker):
    GPU = "H100"

    @modal.enter()
    def load(self):
        self._start_load()
        import torch
        from diffusers import AutoencoderKLWan, WanImageToVideoPipeline

        self.torch = torch
        base = MODELS["wan2.2-i2v-a14b"].local_dir
        # The VAE is kept in fp32, as the Wan model card recommends.
        vae = AutoencoderKLWan.from_pretrained(base, subfolder="vae", torch_dtype=torch.float32)
        self.pipe = WanImageToVideoPipeline.from_pretrained(base, vae=vae, torch_dtype=torch.bfloat16).to("cuda")
        lora = MODELS["wan2.2-i2v-a14b-lightning"]
        high, low = lora.files
        self.pipe.load_lora_weights(lora.local_dir, weight_name=high, adapter_name="lightning")
        self.pipe.load_lora_weights(
            lora.local_dir, weight_name=low, adapter_name="lightning_2", load_into_transformer_2=True
        )
        self._end_load()

    @modal.method()
    def i2v(
        self,
        first_frame: bytes,
        prompt: str,
        seed: int,
        width: int,
        height: int,
        num_frames: int,
        fps: int,
        lightning: bool = True,
        last_frame: bytes | None = None,
    ) -> dict:
        from diffusers.utils import export_to_video
        from PIL import Image

        t0 = time.perf_counter()
        image = Image.open(io.BytesIO(first_frame)).convert("RGB").resize((width, height))
        kwargs = {}
        if last_frame is not None:
            kwargs["last_image"] = Image.open(io.BytesIO(last_frame)).convert("RGB").resize((width, height))
        if lightning:
            self.pipe.set_adapters(["lightning", "lightning_2"], adapter_weights=[1.0, 1.0])
            steps, cfg, cfg2 = 4, 1.0, 1.0
        else:
            self.pipe.disable_lora()
            steps, cfg, cfg2 = 40, 3.5, 3.5
        frames = self.pipe(
            image=image,
            prompt=prompt,
            negative_prompt=NEGATIVE,
            width=width,
            height=height,
            num_frames=num_frames,
            num_inference_steps=steps,
            guidance_scale=cfg,
            guidance_scale_2=cfg2,
            generator=self.torch.Generator("cuda").manual_seed(seed),
            **kwargs,
        ).frames[0]
        infer_s = time.perf_counter() - t0
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            export_to_video(frames, f.name, fps=fps)
            mp4 = open(f.name, "rb").read()
        return {"mp4": mp4, "n_frames": len(frames), "timing": self._timing(infer_s)}
