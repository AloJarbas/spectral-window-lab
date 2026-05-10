from __future__ import annotations

import cmath
import math
from typing import Iterable


DB_FLOOR = -120.0


def coherent_gain(window: Iterable[float]) -> float:
    values = list(window)
    return sum(values) / len(values)


def equivalent_noise_bandwidth_bins(window: Iterable[float]) -> float:
    values = list(window)
    numerator = len(values) * sum(value * value for value in values)
    denominator = sum(values) ** 2
    return numerator / denominator


def coherent_gain_normalized_response(window: Iterable[float], offset_bins: float) -> float:
    values = list(window)
    length = len(values)
    total = sum(values)
    if total == 0.0:
        return 0.0
    acc = 0j
    for n, sample in enumerate(values):
        phase = -2.0 * math.pi * offset_bins * n / length
        acc += sample * cmath.exp(1j * phase)
    return abs(acc) / total


def offset_response_curve(
    window: Iterable[float], *, max_offset: float = 0.5, steps: int = 200
) -> list[tuple[float, float]]:
    if steps < 2:
        raise ValueError("steps must be at least 2")
    values = list(window)
    points: list[tuple[float, float]] = []
    for idx in range(steps + 1):
        offset = max_offset * idx / steps
        response = coherent_gain_normalized_response(values, offset)
        db = 20.0 * math.log10(max(response, 1e-12))
        points.append((offset, max(DB_FLOOR, db)))
    return points


def scalloping_loss_db(window: Iterable[float]) -> float:
    response = coherent_gain_normalized_response(window, 0.5)
    return 20.0 * math.log10(max(response, 1e-12))


def positive_frequency_spectrum(window: Iterable[float], fft_size: int = 4096) -> tuple[list[float], list[float]]:
    values = list(window)
    if fft_size < 8:
        raise ValueError("fft_size must be at least 8")
    freqs: list[float] = []
    mags: list[float] = []
    for k in range(fft_size // 2 + 1):
        omega = 2.0 * math.pi * k / fft_size
        acc = 0j
        for n, sample in enumerate(values):
            acc += sample * cmath.exp(-1j * omega * n)
        freqs.append(k / fft_size)
        mags.append(abs(acc))
    peak = max(mags) or 1.0
    mags = [value / peak for value in mags]
    return freqs, mags


def half_bin_leakage_spectrum(
    window: Iterable[float], *, fft_size: int = 4096, tone_bin: float = 16.5, span_bins: float = 4.0
) -> list[tuple[float, float]]:
    values = list(window)
    length = len(values)
    if fft_size < 8:
        raise ValueError("fft_size must be at least 8")
    if span_bins <= 0.0:
        raise ValueError("span_bins must be positive")
    points: list[tuple[float, float]] = []
    mags: list[float] = []
    rel_bins: list[float] = []
    for k in range(fft_size // 2 + 1):
        freq_bin = k * length / fft_size
        relative_bin = freq_bin - tone_bin
        if abs(relative_bin) > span_bins:
            continue
        acc = 0j
        for n, sample in enumerate(values):
            phase = -2.0 * math.pi * relative_bin * n / length
            acc += sample * cmath.exp(1j * phase)
        rel_bins.append(relative_bin)
        mags.append(abs(acc))
    peak = max(mags) or 1.0
    for relative_bin, mag in zip(rel_bins, mags):
        db = 20.0 * math.log10(max(mag / peak, 1e-12))
        points.append((relative_bin, max(DB_FLOOR, db)))
    return points


def _first_local_minimum(values: list[float]) -> int:
    for idx in range(2, len(values)):
        if values[idx - 1] < values[idx - 2] and values[idx - 1] < values[idx]:
            return idx - 1
    return max(2, len(values) // 16)


def peak_sidelobe_level_db(window: Iterable[float], fft_size: int = 4096) -> float:
    _, mags = positive_frequency_spectrum(window, fft_size=fft_size)
    min_idx = _first_local_minimum(mags)
    sidelobe_peak = max(mags[min_idx + 1 :])
    return 20.0 * math.log10(max(sidelobe_peak, 1e-12))


def null_to_null_main_lobe_width(window: Iterable[float], fft_size: int = 4096) -> float:
    freqs, mags = positive_frequency_spectrum(window, fft_size=fft_size)
    min_idx = _first_local_minimum(mags)
    return 2.0 * freqs[min_idx]


def metrics_row(name: str, window: Iterable[float], fft_size: int = 4096) -> dict[str, float | str]:
    values = list(window)
    return {
        "name": name,
        "coherent_gain": coherent_gain(values),
        "enbw_bins": equivalent_noise_bandwidth_bins(values),
        "peak_sidelobe_db": peak_sidelobe_level_db(values, fft_size=fft_size),
        "main_lobe_width": null_to_null_main_lobe_width(values, fft_size=fft_size),
        "scalloping_loss_db": scalloping_loss_db(values),
    }
