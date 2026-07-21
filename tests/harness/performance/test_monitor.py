import pytest
from pydantic import ValidationError

from harness.performance.monitor import (
    PerformanceMonitor,
    PerformanceMonitorConfig,
    PerformanceSample,
)


def test_sample_interval_must_be_between_100ms_and_250ms():
    assert PerformanceMonitorConfig(sample_interval_ms=100).sample_interval_ms == 100
    assert PerformanceMonitorConfig(sample_interval_ms=250).sample_interval_ms == 250

    with pytest.raises(ValidationError):
        PerformanceMonitorConfig(sample_interval_ms=99)
    with pytest.raises(ValidationError):
        PerformanceMonitorConfig(sample_interval_ms=251)


def test_system_ram_and_ollama_rss_are_sampled_when_available():
    monitor = PerformanceMonitor(
        system_sampler=lambda: (12.5, 1024, 50.0),
        ollama_rss_sampler=lambda process_name: 2048,
        vram_sampler=lambda: ("disabled", None, None, None),
    )

    sample = monitor.sample_once()

    assert sample.cpu_percent == 12.5
    assert sample.ram_used_bytes == 1024
    assert sample.ram_percent == 50.0
    assert sample.ollama_rss_bytes == 2048


def test_ollama_rss_is_none_when_process_is_missing():
    monitor = PerformanceMonitor(
        system_sampler=lambda: (1.0, 100, 10.0),
        ollama_rss_sampler=lambda process_name: None,
        vram_sampler=lambda: ("disabled", None, None, None),
    )

    sample = monitor.sample_once()

    assert sample.ollama_rss_bytes is None


def test_vram_is_sampled_when_nvml_is_available():
    monitor = PerformanceMonitor(
        system_sampler=lambda: (1.0, 100, 10.0),
        ollama_rss_sampler=lambda process_name: None,
        vram_sampler=lambda: ("ok", 4096, 8192, None),
    )

    sample = monitor.sample_once()

    assert sample.vram_status == "ok"
    assert sample.vram_used_bytes == 4096
    assert sample.vram_total_bytes == 8192
    assert sample.vram_error is None


def test_missing_nvml_degrades_without_failing():
    monitor = PerformanceMonitor(
        system_sampler=lambda: (1.0, 100, 10.0),
        ollama_rss_sampler=lambda process_name: None,
        vram_sampler=lambda: ("unavailable", None, None, "NVML import failed"),
    )

    sample = monitor.sample_once()

    assert sample.vram_status == "unavailable"
    assert sample.vram_used_bytes is None
    assert sample.vram_error == "NVML import failed"


def test_peak_metrics_are_calculated():
    samples = [
        PerformanceSample(
            timestamp_s=1,
            cpu_percent=10.0,
            ram_used_bytes=100,
            ram_percent=10.0,
            ollama_rss_bytes=None,
            vram_used_bytes=None,
            vram_total_bytes=None,
            vram_status="unavailable",
            vram_error="NVML unavailable",
        ),
        PerformanceSample(
            timestamp_s=2,
            cpu_percent=30.0,
            ram_used_bytes=300,
            ram_percent=30.0,
            ollama_rss_bytes=400,
            vram_used_bytes=500,
            vram_total_bytes=1000,
            vram_status="ok",
            vram_error=None,
        ),
    ]

    summary = PerformanceMonitor.summarize(samples)

    assert summary.sample_count == 2
    assert summary.peak_cpu_percent == 30.0
    assert summary.peak_ram_used_bytes == 300
    assert summary.peak_ram_percent == 30.0
    assert summary.peak_ollama_rss_bytes == 400
    assert summary.peak_vram_used_bytes == 500
    assert summary.vram_status == "ok"
    assert summary.vram_error == "NVML unavailable"

