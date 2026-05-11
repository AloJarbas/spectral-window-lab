#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windowlab.metrics import (
    equivalent_noise_bandwidth_bins,
    half_bin_leakage_spectrum,
    metrics_row,
    null_to_null_main_lobe_width,
    offset_response_curve,
    positive_frequency_spectrum,
    scalloping_loss_db,
)
from windowlab.svg import chart_svg, triptych_bar_svg
from windowlab.windows import WINDOW_BUILDERS

ART = ROOT / "art"
LENGTH = 129
FFT_SIZE = 4096
WINDOW_ORDER = tuple(WINDOW_BUILDERS)
SPECTRUM_ORDER = ("rectangular", "hann", "hamming", "blackman", "kaiser-8.6")
AMPLITUDE_SPECIALISTS = ("blackman", "kaiser-8.6", "flattop")


def builders_for(names: tuple[str, ...]) -> list[tuple[str, object]]:
    return [(name, WINDOW_BUILDERS[name]) for name in names]


def build_shapes() -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, builder in builders_for(WINDOW_ORDER):
        window = builder(LENGTH)
        series[name] = [(idx / (LENGTH - 1), value) for idx, value in enumerate(window)]
    return series


def build_spectra() -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, builder in builders_for(SPECTRUM_ORDER):
        freqs, mags = positive_frequency_spectrum(builder(LENGTH), fft_size=FFT_SIZE)
        db = [max(-120.0, 20.0 * math.log10(max(mag, 1e-12))) for mag in mags]
        series[name] = [(freq / 0.08, value) for freq, value in zip(freqs, db) if freq <= 0.08]
    return series


def build_offset_loss() -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, builder in builders_for(WINDOW_ORDER):
        series[name] = offset_response_curve(builder(LENGTH), max_offset=0.5, steps=200)
    return series


def build_half_bin_leakage() -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, builder in builders_for(WINDOW_ORDER):
        series[name] = half_bin_leakage_spectrum(builder(LENGTH), fft_size=FFT_SIZE, tone_bin=16.5, span_bins=4.0)
    return series


def build_metrics() -> list[dict[str, float | str]]:
    rows = []
    for name, builder in builders_for(WINDOW_ORDER):
        rows.append(metrics_row(name, builder(LENGTH), fft_size=FFT_SIZE))
    return rows


def build_amplitude_summary() -> str:
    panels = [
        {
            "title": "Half-bin amplitude loss",
            "y_label": "absolute scalloping loss (dB)",
            "y_range": (0.0, 1.2),
            "tick_format": "{:.2f}",
            "value_format": "{:.3f}",
            "values": {
                name: abs(scalloping_loss_db(WINDOW_BUILDERS[name](LENGTH)))
                for name in AMPLITUDE_SPECIALISTS
            },
        },
        {
            "title": "Equivalent noise bandwidth",
            "y_label": "ENBW (bins)",
            "y_range": (0.0, 4.1),
            "tick_format": "{:.1f}",
            "value_format": "{:.2f}",
            "values": {
                name: equivalent_noise_bandwidth_bins(WINDOW_BUILDERS[name](LENGTH))
                for name in AMPLITUDE_SPECIALISTS
            },
        },
        {
            "title": "Null-to-null main-lobe width",
            "y_label": "width (DFT bins)",
            "y_range": (0.0, 11.0),
            "tick_format": "{:.1f}",
            "value_format": "{:.1f}",
            "values": {
                name: LENGTH * null_to_null_main_lobe_width(WINDOW_BUILDERS[name](LENGTH), fft_size=FFT_SIZE)
                for name in AMPLITUDE_SPECIALISTS
            },
        },
    ]
    return triptych_bar_svg(
        "Flat-top buys amplitude honesty by spending bandwidth",
        "Blackman and Kaiser stay compact; flat-top flattens the peak so hard that ENBW and main-lobe width jump.",
        panels,
    )


def main() -> int:
    ART.mkdir(exist_ok=True)

    shapes_svg = chart_svg(
        "Common windows in the time domain",
        "normalized sample index",
        "amplitude",
        build_shapes(),
        y_range=(0.0, 1.05),
    )
    (ART / "window-shapes.svg").write_text(shapes_svg)

    spectra_svg = chart_svg(
        "Window spectra near DC",
        "normalized frequency / 0.08 cycles per sample",
        "magnitude (dB)",
        build_spectra(),
        y_range=(-120.0, 5.0),
        x_range=(0.0, 1.0),
    )
    (ART / "window-spectra.svg").write_text(spectra_svg)

    offset_loss_svg = chart_svg(
        "Amplitude loss versus bin offset",
        "fractional bin offset",
        "coherent-gain-normalized response (dB)",
        build_offset_loss(),
        y_range=(-4.5, 0.1),
        x_range=(0.0, 0.5),
    )
    (ART / "window-offset-loss.svg").write_text(offset_loss_svg)

    half_bin_svg = chart_svg(
        "Half-bin tone leakage near the peak",
        "bins relative to the true tone",
        "normalized magnitude (dB)",
        build_half_bin_leakage(),
        y_range=(-80.0, 2.0),
        x_range=(-4.0, 4.0),
    )
    (ART / "window-half-bin-leakage.svg").write_text(half_bin_svg)

    (ART / "window-amplitude-specialist-summary.svg").write_text(build_amplitude_summary())

    rows = build_metrics()
    with (ART / "window-metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "coherent_gain",
                "enbw_bins",
                "peak_sidelobe_db",
                "main_lobe_width",
                "scalloping_loss_db",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
