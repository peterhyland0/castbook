"""Multi-shot DAG executor. The workflow's `mode` picks the graph:

    keyframe_i2v       portrait ─┬─ keyframe(s1) ── clip(s1) ─┐
                                 ├─ keyframe(s2) ── clip(s2) ─┼─ stitch
                                 └─ keyframe(s3) ── clip(s3) ─┘

    keyframe_flf       portrait ── keyframe(sN) ── end_keyframe(sN) ── clip(sN, first+last) ── stitch

    lastframe_chain    portrait ── keyframe(s1) ── clip(s1) ── last_frame ── clip(s2) ── last_frame ── … ── stitch

In the keyframe modes shots are independent chains, so they run in parallel
(bounded by `max_parallel`); in lastframe_chain each shot waits for the one
before it. The stitch waits for all of them. Every model call goes
through a content-addressed cache, so re-running a request replays finished
attempts for free and only computes what's missing: resume after a crash and
cheap single-shot edits come from the same mechanism.

The identity gate decides each attempt's fate (see workflow.RetryPolicy):
`pass` stops, `fail` re-rolls with a new seed, `unverifiable` re-prompts once
to keep the face visible and then re-rolls. With a `framing` block, a keyframe
that passes but whose face would be too small in the clip is re-framed the
same way, and each shot's clip size is picked from its keyframes' face size. With a camera check, an end keyframe
whose framing contradicts the shot's `camera` (pulls back on a `closer` beat) is re-framed too. When attempts run
out the best one is kept and the shot is marked degraded; one bad shot never fails the run.

This module has no Modal imports: the GPU work sits behind `Backend`, so the
orchestration logic is tested with fakes.
"""

import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from castbook.config import MODELS
from castbook.costs import StepTiming
from castbook.hashing import sha256_bytes, step_key
from castbook.identity import blocking_cause
from castbook.shots import Camera, Script, ShotSpec
from castbook.store import ArtifactStore
from castbook.workflow import RetryPolicy, Workflow

_RANK = {"pass": 2, "unverifiable": 1, "fail": 0}


class Cancelled(Exception):
    pass


class Backend(Protocol):
    """The GPU (and ffmpeg) work a run needs. Each call returns bytes plus a timing dict."""

    def keyframe(self, refs: list[bytes], prompt: str, seed: int, params: dict) -> tuple[bytes, dict]: ...
    def clip(
        self, first_frame: bytes, prompt: str, seed: int, params: dict, last_frame: bytes | None = None
    ) -> tuple[bytes, dict]: ...
    def last_frame(self, video: bytes) -> tuple[bytes, dict]: ...
    def score_image(self, reference: list[float], image: bytes, judge: dict) -> dict: ...
    def score_video(self, reference: list[float], video: bytes, judge: dict) -> dict: ...
    def stitch(self, clips: list[bytes], params: dict) -> tuple[bytes, dict]: ...


@dataclass
class Attempt:
    step: str
    n: int
    seed: int
    prompt: str
    key: str
    cache: str  # hit | miss
    verdict: dict
    score: dict
    timing: dict | None  # what producing this artifact cost; on a hit, the cost recorded when it was made
    face_px: float | None = None  # keyframes: detected face width, for the framing check
    # set when identity passed but the framing didn't: "small" (the clip's face would be too small to score) or
    # "camera" (the end keyframe's framing contradicts the shot's camera direction)
    framing: str | None = None

    @property
    def rank(self) -> tuple[int, bool, float]:
        value = self.verdict.get("value")
        return (_RANK[self.verdict["status"]], self.framing is None, -1.0 if value is None else value)


@dataclass
class ShotResult:
    shot_id: str
    status: str = "pending"  # pending | running | pass | degraded | cancelled | error
    keyframe_attempts: list[Attempt] = field(default_factory=list)
    end_keyframe_attempts: list[Attempt] = field(default_factory=list)
    clip_attempts: list[Attempt] = field(default_factory=list)
    keyframe_key: str | None = None  # the clip's first frame: a keyframe, or the previous clip's last frame
    end_keyframe_key: str | None = None
    clip_key: str | None = None
    clip_size: tuple[int, int] | None = None  # set when the workflow picks clip size per shot (Framing)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunResult:
    workflow: str
    character: str
    shots: list[ShotResult]
    final_key: str | None
    timings: list[dict]
    wall_s: float

    @property
    def gpu_usd(self) -> float:
        return round(sum(t["usd"] for t in self.timings), 6)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["gpu_usd"] = self.gpu_usd
        return d


def judge_key(judge_cfg: dict, artifact_key: str) -> str:
    """Judge results are keyed by artifact + judge settings, so changing the judge re-scores without regenerating."""
    return step_key("judge", "arcface+hands", "1", judge_cfg, [artifact_key], 0)


def judge_config(workflow: Workflow) -> dict:
    # exclude_none keeps judge keys stable for workflows written before a setting existed
    return workflow.steps["judge"].model_dump(
        include={"sample_every", "max_yaw", "max_hand_overlap", "min_face_px", "gate"}, exclude_none=True
    )


def best(attempts: list[Attempt]) -> Attempt:
    return max(attempts, key=lambda a: a.rank)


def shot_seed(base: int, shot_index: int, attempt: int) -> int:
    """Distinct, reproducible seeds per (shot, attempt): re-running a request replays the same seeds."""
    return base + 1000 * shot_index + attempt


class StepCache:
    """Cache-or-compute over an ArtifactStore. Thread-safe; `commit` persists the store (Volume commit)."""

    def __init__(self, store: ArtifactStore, commit: Callable[[], None] = lambda: None):
        self.store = store
        self._commit = commit
        self._lock = threading.Lock()
        self.timings: list[dict] = []

    def get_or_compute(self, key: str, name: str, meta: dict, compute: Callable[[], tuple[bytes, dict]]):
        hit = self.store.get(key)
        if hit is not None:
            return hit, "hit", None
        data, timing = compute()
        with self._lock:
            art = self.store.put(key, name, data, {**meta, "timing": timing})
            self.timings.append(timing)
            self._commit()
        return art, "miss", timing

    def judged(self, key: str, compute: Callable[[], dict]) -> dict:
        """Judge results are cached as JSON artifacts too, keyed by artifact + judge config."""
        hit = self.store.get(key)
        if hit is not None:
            return json.loads(hit.data)
        result = compute()
        result = {k: v for k, v in result.items() if k != "timing"}
        with self._lock:
            self.store.put(key, "judge.json", json.dumps(result).encode(), {"step": "judge"})
            self._commit()
        return result


class Executor:
    def __init__(
        self,
        workflow: Workflow,
        backend: Backend,
        cache: StepCache,
        max_parallel: int = 3,
        on_event: Callable[[dict], None] = lambda e: None,
        should_cancel: Callable[[], bool] = lambda: False,
    ):
        self.wf = workflow
        self.backend = backend
        self.cache = cache
        self.max_parallel = max_parallel
        self.on_event = on_event
        self.should_cancel = should_cancel
        self.judge_cfg = judge_config(workflow)

    def _check_cancel(self) -> None:
        if self.should_cancel():
            raise Cancelled()

    def _attempts(
        self,
        step: str,
        shot_index: int,
        base_seed: int,
        prompt: str,
        inputs: list[str],
        generate: Callable[[str, int], tuple[bytes, dict]],
        judge: Callable[[bytes], dict],
        name: str,
        framing: Callable[[Attempt], str | None] | None = None,
        framing_suffixes: dict[str, str] | None = None,
    ) -> list[Attempt]:
        """`framing_suffixes` adds re-prompts for framing causes beyond the policy's `reprompt_by_cause`."""
        cfg = self.wf.steps[step]
        policy = cfg.retry or RetryPolicy(max_attempts=1)
        by_cause = {**policy.reprompt_by_cause, **(framing_suffixes or {})}
        attempts: list[Attempt] = []
        reprompts = 0
        for n in range(policy.max_attempts):
            self._check_cancel()
            seed = shot_seed(base_seed, shot_index, n)
            params = {**cfg.params, "prompt": prompt}
            key = step_key(step, cfg.model, MODELS[cfg.model].revision, params, inputs, seed)
            art, cache, timing = self.cache.get_or_compute(
                key,
                name,
                {"step": step, "model": cfg.model, "params": params, "inputs": inputs, "seed": seed},
                lambda prompt=prompt, seed=seed: generate(prompt, seed),
            )
            timing = timing or art.meta.get("timing")
            result = self.cache.judged(judge_key(self.judge_cfg, key), lambda art=art: judge(art.data))
            face = (result.get("frame") or {}).get("face_px")
            attempt = Attempt(
                step, n, seed, prompt, key, cache, result["verdict"], result["score"], timing, face_px=face
            )
            status = attempt.verdict["status"]
            if status == "pass" and framing is not None:
                attempt.framing = framing(attempt)
            attempts.append(attempt)
            self.on_event({"type": "attempt", "step": step, "shot_index": shot_index, **_brief(attempt)})
            if status == "pass" and attempt.framing is None:
                break
            if attempt.framing:  # identity is fine, the framing isn't: only a cause-specific suffix helps
                suffix = by_cause.get(attempt.framing, "")
            elif status == "unverifiable":
                suffix = policy.suffix_for(blocking_cause(attempt.score))
            else:
                suffix = ""
            if suffix and suffix not in prompt and reprompts < policy.max_reprompts:
                prompt = prompt + suffix
                reprompts += 1
        return attempts

    def _run_shot(
        self,
        i: int,
        shot: ShotSpec,
        portrait: bytes,
        portrait_sha: str,
        reference: list[float],
        seed: int,
        first: tuple[str, bytes] | None = None,
    ) -> ShotResult:
        """One shot. `first` is (key, png) of a given first frame (lastframe_chain); otherwise a keyframe is made."""
        result = ShotResult(shot.id, status="running")
        self.on_event({"type": "shot", "shot_id": shot.id, "status": "running"})
        store = self.cache.store

        def score_image(data: bytes) -> dict:
            return self.backend.score_image(reference, data, self.judge_cfg)

        kf_width = self.wf.steps["keyframe"].params.get("width")
        framing = self._framing_check(kf_width)

        try:
            gated: list[Attempt] = []
            if first is None:
                kf_params = self.wf.steps["keyframe"].params
                result.keyframe_attempts = self._attempts(
                    "keyframe",
                    i,
                    seed,
                    shot.keyframe,
                    [portrait_sha],
                    lambda p, s: self.backend.keyframe([portrait], p, s, kf_params),
                    score_image,
                    "keyframe.png",
                    framing,
                )
                gated.append(best(result.keyframe_attempts))
                result.keyframe_key = gated[-1].key
                start = store.get(result.keyframe_key).data
            else:
                result.keyframe_key, start = first

            end = None
            if self.wf.mode == "keyframe_flf":
                end_params = self.wf.steps["end_keyframe"].params
                end_prompt = end_params["prompt_template"].format(end=shot.end)
                end_check, end_suffixes = framing, None
                start_kf = best(result.keyframe_attempts) if result.keyframe_attempts else None
                cam = self.wf.framing.camera if self.wf.framing else None
                if cam and shot.camera and start_kf and start_kf.face_px:
                    end_check = _camera_check(framing, shot.camera, start_kf.face_px, cam.tolerance)
                    end_suffixes = {"camera": cam.suffix.get(shot.camera, "")}
                    if self._reframed(start_kf):  # the script's shot sizes describe the old start: go relative
                        end_prompt += end_suffixes["camera"]
                result.end_keyframe_attempts = self._attempts(
                    "end_keyframe",
                    i,
                    seed,
                    end_prompt,
                    [result.keyframe_key, portrait_sha],
                    lambda p, s: self.backend.keyframe([start, portrait], p, s, end_params),
                    score_image,
                    "end_keyframe.png",
                    end_check,
                    end_suffixes,
                )
                gated.append(best(result.end_keyframe_attempts))
                result.end_keyframe_key = gated[-1].key
                end = store.get(result.end_keyframe_key).data

            clip_params = self.wf.steps["clip"].params
            faces = [best(a).face_px for a in (result.keyframe_attempts, result.end_keyframe_attempts) if a]
            result.clip_size = self._clip_size(faces, kf_width)
            if result.clip_size:
                clip_params = {**clip_params, "width": result.clip_size[0], "height": result.clip_size[1]}
            inputs = [k for k in (result.keyframe_key, result.end_keyframe_key) if k]
            result.clip_attempts = self._attempts(
                "clip",
                i,
                seed,
                shot.motion,
                inputs,
                lambda p, s: self.backend.clip(start, p, s, clip_params, end),
                lambda data: self.backend.score_video(reference, data, self.judge_cfg),
                "clip.mp4",
            )
            gated.append(best(result.clip_attempts))
            result.clip_key = gated[-1].key
            result.status = "pass" if all(a.verdict["status"] == "pass" for a in gated) else "degraded"
        except Cancelled:
            result.status = "cancelled"
        except Exception as e:  # noqa: BLE001 - one shot's failure is recorded, the run continues
            result.status, result.error = "error", f"{type(e).__name__}: {e}"
        self.on_event({"type": "shot", "shot_id": shot.id, "status": result.status})
        return result

    def _framing_check(self, kf_width: int | None) -> Callable[[Attempt], str | None] | None:
        """Keyframe check: would this face still be scorable in the cheapest clip? (see workflow.Framing)"""
        fr = self.wf.framing
        if fr is None or not kf_width:
            return None
        clip_w = fr.clip_sizes[0][0]

        def check(a: Attempt) -> str | None:
            small = a.face_px is not None and a.face_px * clip_w / kf_width < fr.min_clip_face_px
            return "small" if small else None

        return check

    def _reframed(self, keyframe: Attempt) -> bool:
        """Did this keyframe come from a small-face re-prompt?"""
        retry = self.wf.steps["keyframe"].retry
        small = retry.reprompt_by_cause.get("small") if retry else None
        return bool(small) and small in keyframe.prompt

    def _clip_size(self, faces: list[float | None], kf_width: int | None) -> tuple[int, int] | None:
        """Cheapest clip size whose predicted face clears the bar; the largest if none does."""
        fr = self.wf.framing
        if fr is None:
            return None
        known = [f for f in faces if f is not None]
        if not known or not kf_width:
            return tuple(fr.clip_sizes[0])
        for w, h in fr.clip_sizes:
            if min(known) * w / kf_width >= fr.min_clip_face_px:
                return (w, h)
        return tuple(fr.clip_sizes[-1])

    def _last_frame(self, clip_key: str) -> tuple[str, bytes]:
        key = step_key("last_frame", "ffmpeg", "1", {}, [clip_key], 0)
        clip = self.cache.store.get(clip_key).data
        art, _, _ = self.cache.get_or_compute(
            key, "last_frame.png", {"step": "last_frame", "inputs": [clip_key]}, lambda: self.backend.last_frame(clip)
        )
        return art.key, art.data

    def _run_chain(self, script: Script, portrait: bytes, portrait_sha: str, reference: list[float]):
        """lastframe_chain: strictly sequential, each shot starts where the previous clip ended."""
        shots: list[ShotResult] = []
        first = None
        for i, shot in enumerate(script.shots):
            if shots and shots[-1].clip_key is None:
                shots.append(ShotResult(shot.id, status="error", error="previous shot produced no clip to continue"))
                continue
            if shots:
                try:
                    first = self._last_frame(shots[-1].clip_key)
                except Exception as e:  # noqa: BLE001
                    shots.append(ShotResult(shot.id, status="error", error=f"last_frame: {type(e).__name__}: {e}"))
                    continue
            shots.append(self._run_shot(i, shot, portrait, portrait_sha, reference, script.seed, first))
        return shots

    def run(self, script: Script, portrait: bytes, reference: list[float]) -> RunResult:
        t0 = time.perf_counter()
        if self.wf.mode == "keyframe_flf":
            missing = [s.id for s in script.shots if not s.end]
            if missing:
                raise ValueError(f"{self.wf.ref} needs an `end` prompt on every shot; missing on {missing}")
        portrait_sha = sha256_bytes(portrait)
        if self.wf.mode == "lastframe_chain":
            shots = self._run_chain(script, portrait, portrait_sha, reference)
        else:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
                futures = [
                    pool.submit(self._run_shot, i, shot, portrait, portrait_sha, reference, script.seed)
                    for i, shot in enumerate(script.shots)
                ]
                shots = [f.result() for f in futures]

        final_key = None
        usable = [s for s in shots if s.clip_key]
        if usable and not self.should_cancel():
            stitch_params = self.wf.steps["stitch"].params if "stitch" in self.wf.steps else {}
            inputs = [s.clip_key for s in usable]
            key = step_key("stitch", "ffmpeg", "1", stitch_params, inputs, 0)
            clips = [self.cache.store.get(k).data for k in inputs]
            art, _, _ = self.cache.get_or_compute(
                key,
                "final.mp4",
                {"step": "stitch", "inputs": inputs},
                lambda: self.backend.stitch(clips, stitch_params),
            )
            final_key = art.key
            self.on_event({"type": "stitched", "key": final_key, "n_clips": len(inputs)})
        return RunResult(
            workflow=self.wf.ref,
            character=script.character,
            shots=shots,
            final_key=final_key,
            timings=list(self.cache.timings),
            wall_s=round(time.perf_counter() - t0, 1),
        )


def _camera_check(
    small: Callable[[Attempt], str | None] | None, camera: Camera, start_face: float, tolerance: float
) -> Callable[[Attempt], str | None]:
    """End keyframe check (see workflow.CameraCheck): the small-face check first, then the face size ratio to the
    start keyframe against the shot's camera direction."""

    def check(a: Attempt) -> str | None:
        cause = small(a) if small else None
        if cause or a.face_px is None:
            return cause
        ratio = a.face_px / start_face
        reversed_ = {
            "closer": ratio < 1 - tolerance,
            "wider": ratio > 1 + tolerance,
            "steady": abs(ratio - 1) > tolerance,
        }[camera]
        return "camera" if reversed_ else None

    return check


def _brief(a: Attempt) -> dict:
    return {
        "n": a.n,
        "seed": a.seed,
        "cache": a.cache,
        "status": a.verdict["status"],
        "framing": a.framing,
        "value": a.verdict.get("value"),
        "reasons": a.verdict.get("reasons"),
        "usd": None if a.timing is None else a.timing.get("usd"),
    }


def billing(timings: list[dict]) -> dict[str, Any]:
    """The billing block for API responses: attributable GPU time by GPU type, and its $."""
    by_gpu: dict[str, float] = {}
    for t in timings:
        st = StepTiming(gpu=t["gpu"], load_s=t["load_s"], infer_s=t["infer_s"], cold=t["cold"])
        by_gpu[st.gpu] = by_gpu.get(st.gpu, 0.0) + st.gpu_seconds
    return {
        "gpu_seconds": {k: round(v, 1) for k, v in by_gpu.items()},
        "usd": round(sum(t["usd"] for t in timings), 4),
        "note": "attributable GPU time (cold loads + inference); excludes idle scaledown",
    }
