"""Identity judge: ArcFace (InsightFace buffalo_l) on CPU.

Detection plus a 512-d embedding per face. For each image or sampled frame we
keep the largest face, which is the subject in a single-character shot.
"""

import io
import tempfile
import time

import modal

from castbook.identity import score_frames
from castbook.workers.common import MODELS_DIR, TimedWorker, app, judge_image, models_vol


@app.cls(image=judge_image, cpu=4, memory=8192, volumes={MODELS_DIR: models_vol}, scaledown_window=120, timeout=900)
class Judge(TimedWorker):
    GPU = "CPU"

    @modal.enter()
    def load(self):
        self._start_load()
        from pathlib import Path

        from insightface.app import FaceAnalysis

        root = f"{MODELS_DIR}/insightface"
        first_time = not Path(root, "models", "buffalo_l").exists()
        self.fa = FaceAnalysis(name="buffalo_l", root=root, providers=["CPUExecutionProvider"])
        self.fa.prepare(ctx_id=-1, det_size=(640, 640))
        if first_time:
            models_vol.commit()
        self._end_load()

    def _embed_rgb(self, rgb):
        import numpy as np

        faces = self.fa.get(np.ascontiguousarray(rgb[:, :, ::-1]))  # InsightFace expects BGR
        if not faces:
            return None, 0
        f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return f.normed_embedding, len(faces)

    def _embed_bytes(self, data: bytes):
        import numpy as np
        from PIL import Image

        return self._embed_rgb(np.array(Image.open(io.BytesIO(data)).convert("RGB")))

    @modal.method()
    def embed(self, image: bytes) -> dict:
        t0 = time.perf_counter()
        emb, n_faces = self._embed_bytes(image)
        return {
            "embedding": None if emb is None else emb.tolist(),
            "n_faces": n_faces,
            "timing": self._timing(time.perf_counter() - t0),
        }

    @modal.method()
    def score_image(self, reference: list[float], image: bytes) -> dict:
        import numpy as np

        t0 = time.perf_counter()
        emb, n_faces = self._embed_bytes(image)
        score = score_frames(np.array(reference), [emb])
        return {"score": score.to_dict(), "n_faces": n_faces, "timing": self._timing(time.perf_counter() - t0)}

    @modal.method()
    def score_video(self, reference: list[float], video: bytes, sample_every: int = 8) -> dict:
        import imageio.v3 as iio
        import numpy as np

        from castbook.identity import cosine

        t0 = time.perf_counter()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            f.write(video)
            f.flush()
            frames = iio.imread(f.name, plugin="pyav")
        sampled = list(range(0, len(frames), sample_every))
        if sampled[-1] != len(frames) - 1:
            sampled.append(len(frames) - 1)  # always judge the last frame: the next shot starts there
        embs = [self._embed_rgb(frames[i])[0] for i in sampled]
        ref = np.array(reference)
        per_frame = [
            {"frame": i, "sim": None if e is None else round(cosine(ref, e), 4)}
            for i, e in zip(sampled, embs, strict=True)
        ]
        score = score_frames(ref, embs)
        return {"score": score.to_dict(), "per_frame": per_frame, "timing": self._timing(time.perf_counter() - t0)}
