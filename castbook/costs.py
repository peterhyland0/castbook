"""GPU-time accounting. Every worker call reports timings; this turns them into $."""

from dataclasses import asdict, dataclass

from castbook.config import GPU_USD_PER_SECOND


@dataclass(frozen=True)
class StepTiming:
    """What a worker reports about one call.

    `load_s` is non-zero only on the call that paid for a cold start (model
    load in @modal.enter); `infer_s` is the generation itself.
    """

    gpu: str
    load_s: float
    infer_s: float
    cold: bool

    @property
    def gpu_seconds(self) -> float:
        return self.load_s + self.infer_s

    @property
    def usd(self) -> float:
        return round(self.gpu_seconds * GPU_USD_PER_SECOND[self.gpu], 6)

    def to_dict(self) -> dict:
        return {**asdict(self), "gpu_seconds": round(self.gpu_seconds, 3), "usd": self.usd}


def total_usd(timings: list[StepTiming]) -> float:
    return round(sum(t.usd for t in timings), 6)
