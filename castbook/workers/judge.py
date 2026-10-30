"""Identity judge: ArcFace (InsightFace buffalo_l) plus a hand detector, on CPU.

Detection plus a 512-d embedding per face. For each image or sampled frame we
keep the largest face, which is the subject in a single-character shot. The
buffalo_l pack also estimates head pose (pitch, yaw, roll in degrees) from its
3D landmark model; yaw is what decides whether a frame is a profile.

Occlusion: MediaPipe's hand landmarker finds hands, and we measure how much of
the face box the hand boxes cover. Detection confidence and embedding norm also
drop when a face is covered, but they drop just as much when it turns away
(first clip: 0.89 -> 0.67 and 18-20 -> 13-15 across the turn), so on their own
they can't tell occlusion from pose. They are still reported for calibration.
"""

import io
import tempfile
import time
import urllib.request
from pathlib import Path

import modal

from castbook.identity import GateConfig, frame_status, overlap_fraction, score_frames, verdict
from castbook.workers.common import MODELS_DIR, TimedWorker, app, judge_image, models_vol

HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"


@app.cls(image=judge_image, cpu=4, memory=8192, volumes={MODELS_DIR: models_vol}, scaledown_window=120, timeout=900)
class Judge(TimedWorker):
    GPU = "CPU"

    @modal.enter()
    def load(self):
        self._start_load()
        from insightface.app import FaceAnalysis
        from mediapipe.tasks.python import BaseOptions, vision

        root = f"{MODELS_DIR}/insightface"
        downloaded = not Path(root, "models", "buffalo_l").exists()
        self.fa = FaceAnalysis(name="buffalo_l", root=root, providers=["CPUExecutionProvider"])
        self.fa.prepare(ctx_id=-1, det_size=(640, 640))

        hand_model = Path(MODELS_DIR, "mediapipe", "hand_landmarker.task")
        if not hand_model.exists():
            hand_model.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(HAND_MODEL_URL, hand_model)
            downloaded = True
        self.hands = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(hand_model)),
                running_mode=vision.RunningMode.IMAGE,
                num_hands=2,
            )
        )
        if downloaded:
            models_vol.commit()
        self._end_load()

    def _hand_boxes(self, rgb) -> list[tuple[float, float, float, float]]:
        import mediapipe as mp
        import numpy as np

        h, w = rgb.shape[:2]
        result = self.hands.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        boxes = []
        for landmarks in result.hand_landmarks:
            xs = [lm.x * w for lm in landmarks]
            ys = [lm.y * h for lm in landmarks]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
        return boxes

    def _observe(self, rgb) -> dict:
        """Everything the gate needs about the subject's face in one image."""
        import numpy as np

        faces = self.fa.get(np.ascontiguousarray(rgb[:, :, ::-1]))  # InsightFace expects BGR
        if not faces:
            return {"embedding": None, "n_faces": 0}
        f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        face_box = tuple(float(v) for v in f.bbox)
        hands = self._hand_boxes(rgb)
        pose = getattr(f, "pose", None)
        return {
            "embedding": f.normed_embedding,
            "n_faces": len(faces),
            "yaw": None if pose is None else float(pose[1]),
            "det_score": float(f.det_score),
            "emb_norm": float(np.linalg.norm(f.embedding)),
            "face_box": face_box,
            "n_hands": len(hands),
            "hand_boxes": hands,
            "hand_overlap": max((overlap_fraction(face_box, hb) for hb in hands), default=0.0),
        }

    def _observe_bytes(self, data: bytes) -> dict:
        import numpy as np
        from PIL import Image

        return self._observe(np.array(Image.open(io.BytesIO(data)).convert("RGB")))

    @staticmethod
    def _gate(gate: dict | None) -> GateConfig:
        return GateConfig(**(gate or {}))

    def _summarize(self, reference, observations, max_yaw, max_hand_overlap, gate) -> dict:
        import numpy as np

        ref = np.array(reference)
        score = score_frames(
            ref,
            [o["embedding"] for o in observations],
            [o.get("yaw") for o in observations],
            max_yaw,
            [o.get("hand_overlap") for o in observations],
            max_hand_overlap,
        )
        return {"score": score.to_dict(), "verdict": verdict(score, self._gate(gate)).to_dict()}

    @staticmethod
    def _frame_record(index, obs, reference, max_yaw, max_hand_overlap) -> dict:
        from castbook.identity import cosine, is_occluded, is_profile

        emb = obs["embedding"]
        has_face = emb is not None
        return {
            "frame": index,
            "sim": round(cosine(reference, emb), 4) if has_face else None,
            "yaw": round(obs["yaw"], 1) if obs.get("yaw") is not None else None,
            "hand_overlap": round(obs["hand_overlap"], 3) if has_face else None,
            "n_hands": obs.get("n_hands"),
            "face_box": [round(v) for v in obs["face_box"]] if has_face else None,
            "hand_boxes": [[round(v) for v in b] for b in obs.get("hand_boxes", [])],
            "det_score": round(obs["det_score"], 3) if has_face else None,
            "emb_norm": round(obs["emb_norm"], 2) if has_face else None,
            "profile": has_face and is_profile(obs.get("yaw"), max_yaw),
            "occluded": has_face and is_occluded(obs.get("hand_overlap"), max_hand_overlap),
            "status": frame_status(has_face, obs.get("yaw"), obs.get("hand_overlap"), max_yaw, max_hand_overlap),
        }

    @modal.method()
    def embed(self, image: bytes) -> dict:
        t0 = time.perf_counter()
        obs = self._observe_bytes(image)
        emb = obs["embedding"]
        return {
            "embedding": None if emb is None else emb.tolist(),
            "yaw": obs.get("yaw"),
            "n_faces": obs["n_faces"],
            "timing": self._timing(time.perf_counter() - t0),
        }

    @modal.method()
    def score_image(
        self,
        reference: list[float],
        image: bytes,
        max_yaw: float | None = None,
        max_hand_overlap: float | None = None,
        gate: dict | None = None,
    ) -> dict:
        import numpy as np

        t0 = time.perf_counter()
        obs = self._observe_bytes(image)
        out = self._summarize(reference, [obs], max_yaw, max_hand_overlap, gate)
        out["frame"] = self._frame_record(0, obs, np.array(reference), max_yaw, max_hand_overlap)
        out["timing"] = self._timing(time.perf_counter() - t0)
        return out

    @modal.method()
    def score_video(
        self,
        reference: list[float],
        video: bytes,
        sample_every: int = 8,
        max_yaw: float | None = None,
        max_hand_overlap: float | None = None,
        gate: dict | None = None,
    ) -> dict:
        import imageio.v3 as iio
        import numpy as np

        t0 = time.perf_counter()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            f.write(video)
            f.flush()
            frames = iio.imread(f.name, plugin="pyav")
        sampled = list(range(0, len(frames), sample_every))
        if sampled[-1] != len(frames) - 1:
            sampled.append(len(frames) - 1)  # always judge the last frame: the next shot starts there
        observations = [self._observe(frames[i]) for i in sampled]
        ref = np.array(reference)
        out = self._summarize(reference, observations, max_yaw, max_hand_overlap, gate)
        out["per_frame"] = [
            self._frame_record(i, o, ref, max_yaw, max_hand_overlap) for i, o in zip(sampled, observations, strict=True)
        ]
        out["timing"] = self._timing(time.perf_counter() - t0)
        return out
