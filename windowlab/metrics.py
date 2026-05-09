from __future__ import annotations

import cmath
import math
from typing import Iterable


def coherent_gain(window: Iterable[float]) -> float:
    values = list(window)
    return sum(values) / len(values)


def equivalent_noise_bandwidth_bins(window: Iterable[float]) -> float:
    values = list(window)
    numerator = len(values) * sum(value * value for value in values)
    denominator = sum(values) ** 2
    return numerator / denominator


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
    }
