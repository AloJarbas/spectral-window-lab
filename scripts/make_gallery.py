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
    coherent_gain,
    equivalent_noise_bandwidth_bins,
    half_bin_leakage_spectrum,
    metrics_row,
    null_to_null_main_lobe_width,
    offset_response_curve,
    peak_sidelobe_level_db,
    positive_frequency_spectrum,
    scalloping_loss_db,
)
from windowlab.svg import chart_svg, stacked_line_panels_svg, triptych_bar_svg
from windowlab.windows import WINDOW_BUILDERS, kaiser

ART = ROOT / "art"
LENGTH = 129
FFT_SIZE = 4096
WINDOW_ORDER = tuple(WINDOW_BUILDERS)
SPECTRUM_ORDER = ("rectangular", "hann", "hamming", "blackman", "kaiser-8.6")
AMPLITUDE_SPECIALISTS = ("blackman", "kaiser-8.6", "flattop")
KAISER_SWEEP_BETAS = tuple(sorted({step / 2 for step in range(29)} | {8.6}))
KAISER_HIGHLIGHTS = (0.0, 5.0, 8.6, 14.0)


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


def build_kaiser_sweep_rows() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for beta in KAISER_SWEEP_BETAS:
        window = kaiser(LENGTH, beta)
        rows.append(
            {
                "beta": beta,
                "coherent_gain": coherent_gain(window),
                "enbw_bins": equivalent_noise_bandwidth_bins(window),
                "peak_sidelobe_db": peak_sidelobe_level_db(window, fft_size=FFT_SIZE),
                "main_lobe_width_bins": LENGTH * null_to_null_main_lobe_width(window, fft_size=FFT_SIZE),
                "scalloping_loss_db": abs(scalloping_loss_db(window)),
            }
        )
    return rows


def _padded_range(values: list[float], *, pad_low: float = 0.08, pad_high: float = 0.12, clamp_min: float | None = None) -> tuple[float, float]:
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi > lo else max(abs(hi), 1.0)
    lo -= span * pad_low
    hi += span * pad_high
    if clamp_min is not None:
        lo = max(clamp_min, lo)
    return lo, hi


def build_kaiser_sweep_svg(rows: list[dict[str, float]]) -> str:
    blackman = WINDOW_BUILDERS["blackman"](LENGTH)
    flattop = WINDOW_BUILDERS["flattop"](LENGTH)
    series = {
        "ENBW": [(row["beta"], row["enbw_bins"]) for row in rows],
        "Main-lobe width": [(row["beta"], row["main_lobe_width_bins"]) for row in rows],
        "Peak sidelobe": [(row["beta"], row["peak_sidelobe_db"]) for row in rows],
    }
    highlight_rows = {row["beta"]: row for row in rows if row["beta"] in KAISER_HIGHLIGHTS}

    panels = [
        {
            "title": "Equivalent noise bandwidth rises with beta",
            "y_label": "ENBW (bins)",
            "y_range": _padded_range(
                [row["enbw_bins"] for row in rows]
                + [
                    equivalent_noise_bandwidth_bins(blackman),
                    equivalent_noise_bandwidth_bins(flattop),
                ],
                clamp_min=0.0,
            ),
            "tick_format": "{:.2f}",
            "x_range": (KAISER_SWEEP_BETAS[0], KAISER_SWEEP_BETAS[-1]),
            "x_tick_format": "{:.0f}",
            "series": [
                {"name": "Kaiser family", "stroke": "#7c3aed", "points": series["ENBW"], "width": 3},
            ],
            "references": [
                {"label": "blackman", "value": equivalent_noise_bandwidth_bins(blackman), "stroke": "#d62728", "dash": "6 6"},
                {"label": "flat-top", "value": equivalent_noise_bandwidth_bins(flattop), "stroke": "#8b5cf6", "dash": "2 7"},
            ],
            "markers": [
                {"label": f"β={beta:g}", "x": beta, "y": highlight_rows[beta]["enbw_bins"], "fill": "#ede9fe", "stroke": "#7c3aed"}
                for beta in KAISER_HIGHLIGHTS
            ],
        },
        {
            "title": "Main-lobe width keeps widening",
            "y_label": "null-to-null width (DFT bins)",
            "y_range": _padded_range(
                [row["main_lobe_width_bins"] for row in rows]
                + [
                    LENGTH * null_to_null_main_lobe_width(blackman, fft_size=FFT_SIZE),
                    LENGTH * null_to_null_main_lobe_width(flattop, fft_size=FFT_SIZE),
                ],
                clamp_min=0.0,
            ),
            "tick_format": "{:.1f}",
            "x_range": (KAISER_SWEEP_BETAS[0], KAISER_SWEEP_BETAS[-1]),
            "x_tick_format": "{:.0f}",
            "series": [
                {"name": "Kaiser family", "stroke": "#7c3aed", "points": series["Main-lobe width"], "width": 3},
            ],
            "references": [
                {"label": "blackman", "value": LENGTH * null_to_null_main_lobe_width(blackman, fft_size=FFT_SIZE), "stroke": "#d62728", "dash": "6 6"},
                {"label": "flat-top", "value": LENGTH * null_to_null_main_lobe_width(flattop, fft_size=FFT_SIZE), "stroke": "#8b5cf6", "dash": "2 7"},
            ],
            "markers": [
                {"label": f"β={beta:g}", "x": beta, "y": highlight_rows[beta]["main_lobe_width_bins"], "fill": "#ede9fe", "stroke": "#7c3aed"}
                for beta in KAISER_HIGHLIGHTS
            ],
        },
        {
            "title": "Peak sidelobes drop as beta climbs",
            "y_label": "peak sidelobe (dB)",
            "y_range": _padded_range(
                [row["peak_sidelobe_db"] for row in rows]
                + [
                    peak_sidelobe_level_db(blackman, fft_size=FFT_SIZE),
                    peak_sidelobe_level_db(flattop, fft_size=FFT_SIZE),
                ]
            ),
            "tick_format": "{:.0f}",
            "x_range": (KAISER_SWEEP_BETAS[0], KAISER_SWEEP_BETAS[-1]),
            "x_tick_format": "{:.0f}",
            "series": [
                {"name": "Kaiser family", "stroke": "#7c3aed", "points": series["Peak sidelobe"], "width": 3},
            ],
            "references": [
                {"label": "blackman", "value": peak_sidelobe_level_db(blackman, fft_size=FFT_SIZE), "stroke": "#d62728", "dash": "6 6"},
                {"label": "flat-top", "value": peak_sidelobe_level_db(flattop, fft_size=FFT_SIZE), "stroke": "#8b5cf6", "dash": "2 7"},
            ],
            "markers": [
                {"label": f"β={beta:g}", "x": beta, "y": highlight_rows[beta]["peak_sidelobe_db"], "fill": "#ede9fe", "stroke": "#7c3aed"}
                for beta in KAISER_HIGHLIGHTS
            ],
        },
    ]

    return stacked_line_panels_svg(
        "Kaiser beta sweep: one knob, three visible tradeoffs",
        "The family moves smoothly. Blackman sits near β≈8.6. Flat-top is still a separate amplitude specialist, not the end of the Kaiser curve.",
        "Kaiser β",
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

    kaiser_rows = build_kaiser_sweep_rows()
    (ART / "window-kaiser-beta-sweep.svg").write_text(build_kaiser_sweep_svg(kaiser_rows))
    with (ART / "kaiser-beta-sweep.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "beta",
                "coherent_gain",
                "enbw_bins",
                "peak_sidelobe_db",
                "main_lobe_width_bins",
                "scalloping_loss_db",
            ],
        )
        writer.writeheader()
        writer.writerows(kaiser_rows)

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
