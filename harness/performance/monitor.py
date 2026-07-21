from __future__ import annotations

from collections.abc import Callable
from time import monotonic, sleep
from typing import Any

import psutil
from pydantic import BaseModel, Field


class PerformanceMonitorConfig(BaseModel):
    sample_interval_ms: int = Field(default=100, ge=100, le=250)
    ollama_process_name: str = Field(default="ollama", min_length=1)
    enable_nvml: bool = True


class PerformanceSample(BaseModel):
    timestamp_s: float
    cpu_percent: float | None = None
    ram_used_bytes: int
    ram_percent: float
    ollama_rss_bytes: int | None = None
    vram_used_bytes: int | None = None
    vram_total_bytes: int | None = None
    vram_status: str
    vram_error: str | None = None


class PeakPerformanceMetrics(BaseModel):
    sample_count: int
    peak_cpu_percent: float | None = None
    peak_ram_used_bytes: int | None = None
    peak_ram_percent: float | None = None
    peak_ollama_rss_bytes: int | None = None
    peak_vram_used_bytes: int | None = None
    vram_status: str
    vram_error: str | None = None


class PerformanceMonitor:
    def __init__(
        self,
        config: PerformanceMonitorConfig | None = None,
        system_sampler: Callable[[], tuple[float | None, int, float]] | None = None,
        ollama_rss_sampler: Callable[[str], int | None] | None = None,
        vram_sampler: Callable[[], tuple[str, int | None, int | None, str | None]] | None = None,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.config = config or PerformanceMonitorConfig()
        self._system_sampler = system_sampler or sample_system_usage
        self._ollama_rss_sampler = ollama_rss_sampler or sample_process_rss
        self._vram_sampler = vram_sampler or sample_nvml_vram
        self._clock = clock
        self._sleeper = sleeper

    def sample_once(self) -> PerformanceSample:
        cpu_percent, ram_used_bytes, ram_percent = self._system_sampler()
        vram_status, vram_used_bytes, vram_total_bytes, vram_error = (
            self._vram_sampler()
            if self.config.enable_nvml
            else ("disabled", None, None, None)
        )
        return PerformanceSample(
            timestamp_s=self._clock(),
            cpu_percent=cpu_percent,
            ram_used_bytes=ram_used_bytes,
            ram_percent=ram_percent,
            ollama_rss_bytes=self._ollama_rss_sampler(self.config.ollama_process_name),
            vram_used_bytes=vram_used_bytes,
            vram_total_bytes=vram_total_bytes,
            vram_status=vram_status,
            vram_error=vram_error,
        )

    def sample_for(self, duration_seconds: float) -> list[PerformanceSample]:
        if duration_seconds <= 0:
            return [self.sample_once()]

        samples: list[PerformanceSample] = []
        deadline = self._clock() + duration_seconds
        interval_seconds = self.config.sample_interval_ms / 1000
        while True:
            samples.append(self.sample_once())
            if self._clock() >= deadline:
                break
            self._sleeper(interval_seconds)
        return samples

    @staticmethod
    def summarize(samples: list[PerformanceSample]) -> PeakPerformanceMetrics:
        if not samples:
            return PeakPerformanceMetrics(sample_count=0, vram_status="not_sampled")

        vram_error = next((sample.vram_error for sample in samples if sample.vram_error), None)
        return PeakPerformanceMetrics(
            sample_count=len(samples),
            peak_cpu_percent=_max_optional(sample.cpu_percent for sample in samples),
            peak_ram_used_bytes=max(sample.ram_used_bytes for sample in samples),
            peak_ram_percent=max(sample.ram_percent for sample in samples),
            peak_ollama_rss_bytes=_max_optional(sample.ollama_rss_bytes for sample in samples),
            peak_vram_used_bytes=_max_optional(sample.vram_used_bytes for sample in samples),
            vram_status=_summarize_vram_status(samples),
            vram_error=vram_error,
        )


def sample_system_usage() -> tuple[float | None, int, float]:
    memory = psutil.virtual_memory()
    return psutil.cpu_percent(interval=None), int(memory.used), float(memory.percent)


def sample_process_rss(process_name: str) -> int | None:
    target = process_name.lower()
    total_rss = 0
    found = False
    for process in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (process.info.get("name") or "").lower()
            if name != target and not name.startswith(f"{target}."):
                continue
            memory_info = process.info.get("memory_info") or process.memory_info()
            total_rss += int(memory_info.rss)
            found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return total_rss if found else None


def sample_nvml_vram() -> tuple[str, int | None, int | None, str | None]:
    try:
        import pynvml  # type: ignore[import-not-found]
    except Exception as exc:
        return ("unavailable", None, None, f"NVML import failed: {exc}")

    initialized = False
    try:
        pynvml.nvmlInit()
        initialized = True
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count <= 0:
            return ("unavailable", None, None, "NVML found no GPU devices.")

        used = 0
        total = 0
        for index in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used += int(memory_info.used)
            total += int(memory_info.total)
        return ("ok", used, total, None)
    except Exception as exc:
        return ("unavailable", None, None, f"NVML sampling failed: {exc}")
    finally:
        if initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


def _max_optional(values: Any) -> Any:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _summarize_vram_status(samples: list[PerformanceSample]) -> str:
    statuses = {sample.vram_status for sample in samples}
    if "ok" in statuses:
        return "ok"
    if "unavailable" in statuses:
        return "unavailable"
    if "disabled" in statuses:
        return "disabled"
    return sorted(statuses)[0]

