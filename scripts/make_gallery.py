#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import shutil
import subprocess
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
from windowlab.overlap import normalized_overlap_add_profile, overlap_add_summary
from windowlab.svg import PALETTE, chart_svg, stacked_line_panels_svg, triptych_bar_svg
from windowlab.windows import WINDOW_BUILDERS, kaiser

ART = ROOT / "art"
LENGTH = 129
FFT_SIZE = 4096
PNG_PREVIEW_SIZE = 2400
WINDOW_ORDER = ("rectangular", "hann", "hamming", "blackman", "kaiser-8.6", "flattop")
METRICS_ORDER = WINDOW_ORDER + ("blackman-harris", "nuttall")
SPECTRUM_ORDER = ("rectangular", "hann", "hamming", "blackman", "kaiser-8.6")
AMPLITUDE_SPECIALISTS = ("blackman", "kaiser-8.6", "flattop")
SPECIALIST_ORDER = ("blackman", "kaiser-8.6", "blackman-harris", "nuttall", "flattop")
KAISER_SWEEP_BETAS = tuple(sorted({step / 2 for step in range(29)} | {8.6}))
KAISER_HIGHLIGHTS = (0.0, 5.0, 8.6, 14.0)
OVERLAP_LENGTH = 128
OVERLAP_ORDER = (
    "rectangular",
    "hann",
    "hamming",
    "blackman",
    "kaiser-8.6",
    "blackman-harris",
    "nuttall",
    "flattop",
)
OVERLAP_FIGURE_WINDOWS = (
    ("rectangular", "rectangular"),
    ("hann", "hann"),
    ("hamming", "hamming"),
    ("blackman", "blackman"),
    ("kaiser-8.6", "kaiser β=8.6"),
    ("blackman-harris", "Blackman-Harris"),
    ("flattop", "flat-top"),
)
OVERLAP_HOPS = (64, 32, 16)


def builders_for(names: tuple[str, ...]) -> list[tuple[str, object]]:
    return [(name, WINDOW_BUILDERS[name]) for name in names]


def export_png_preview(svg_path: Path) -> None:
    if sys.platform != "darwin":
        return
    qlmanage = shutil.which("qlmanage")
    sips = shutil.which("sips")
    if not qlmanage or not sips:
        return

    temp_png_path = svg_path.parent / f"{svg_path.name}.png"
    png_path = svg_path.with_suffix(".png")
    try:
        subprocess.run(
            [qlmanage, "-t", "-s", str(PNG_PREVIEW_SIZE), "-o", str(svg_path.parent), str(svg_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not temp_png_path.exists():
            return
        temp_png_path.replace(png_path)
        subprocess.run(
            [sips, "-s", "dpiHeight", "300", "-s", "dpiWidth", "300", str(png_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        if temp_png_path.exists():
            temp_png_path.unlink()


def write_svg_asset(filename: str, payload: str) -> None:
    path = ART / filename
    path.write_text(payload)
    export_png_preview(path)


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


def build_specialist_offset_loss() -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, builder in builders_for(SPECIALIST_ORDER):
        series[name] = offset_response_curve(builder(LENGTH), max_offset=0.5, steps=200)
    return series


def build_metrics() -> list[dict[str, float | str]]:
    rows = []
    for name, builder in builders_for(METRICS_ORDER):
        rows.append(metrics_row(name, builder(LENGTH), fft_size=FFT_SIZE))
    return rows


def build_specialist_metrics_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for name, builder in builders_for(SPECIALIST_ORDER):
        window = builder(LENGTH)
        rows.append(
            {
                "name": name,
                "coherent_gain": coherent_gain(window),
                "enbw_bins": equivalent_noise_bandwidth_bins(window),
                "peak_sidelobe_db": peak_sidelobe_level_db(window, fft_size=FFT_SIZE),
                "main_lobe_width_bins": LENGTH * null_to_null_main_lobe_width(window, fft_size=FFT_SIZE),
                "scalloping_loss_db": scalloping_loss_db(window),
            }
        )
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


def build_specialist_tradeoff_summary() -> str:
    panels = [
        {
            "title": "Peak sidelobe suppression",
            "y_label": "absolute peak sidelobe (dB)",
            "y_range": (0.0, 102.0),
            "tick_format": "{:.0f}",
            "value_format": "{:.1f}",
            "values": {
                name: abs(peak_sidelobe_level_db(WINDOW_BUILDERS[name](LENGTH), fft_size=FFT_SIZE))
                for name in SPECIALIST_ORDER
            },
        },
        {
            "title": "Half-bin amplitude loss",
            "y_label": "absolute scalloping loss (dB)",
            "y_range": (0.0, 1.2),
            "tick_format": "{:.2f}",
            "value_format": "{:.3f}",
            "values": {
                name: abs(scalloping_loss_db(WINDOW_BUILDERS[name](LENGTH)))
                for name in SPECIALIST_ORDER
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
                for name in SPECIALIST_ORDER
            },
        },
    ]
    return triptych_bar_svg(
        "Deep-sidelobe specialists are not the same as amplitude specialists",
        "Blackman-Harris and Nuttall drive sidelobes much lower than Blackman or Kaiser, but flat-top still owns between-bin amplitude honesty and pays far more ENBW for it.",
        panels,
        width=1520,
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


def build_overlap_add_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for hop in OVERLAP_HOPS:
        overlap_fraction = 1.0 - hop / OVERLAP_LENGTH
        for name, builder in builders_for(OVERLAP_ORDER):
            summary = overlap_add_summary(builder(OVERLAP_LENGTH), hop)
            rows.append(
                {
                    "name": name,
                    "length": OVERLAP_LENGTH,
                    "hop": hop,
                    "overlap_fraction": overlap_fraction,
                    "mean_sum": summary.mean_sum,
                    "min_sum": summary.min_sum,
                    "max_sum": summary.max_sum,
                    "max_deviation_pct": summary.max_deviation_fraction * 100.0,
                    "ripple_db": summary.ripple_db,
                }
            )
    return rows


def build_overlap_add_svg() -> str:
    panels = []
    for hop in OVERLAP_HOPS:
        overlap_fraction = (1.0 - hop / OVERLAP_LENGTH) * 100.0
        values_for_range: list[float] = []
        panel_series = []
        for name, builder in builders_for(tuple(key for key, _ in OVERLAP_FIGURE_WINDOWS)):
            points = normalized_overlap_add_profile(builder(OVERLAP_LENGTH), hop)
            values_for_range.extend(value for _, value in points)
            display_name = next(label for key, label in OVERLAP_FIGURE_WINDOWS if key == name)
            panel_series.append({"name": display_name, "stroke": PALETTE.get(name, "#111827"), "points": points, "width": 3})
        y_range = _padded_range(values_for_range, pad_low=0.08, pad_high=0.1)
        if y_range[0] > 0.94:
            y_range = (min(y_range[0], 0.998), max(y_range[1], 1.002))
        panels.append(
            {
                "title": f"Hop = {hop} samples ({overlap_fraction:.1f}% overlap)",
                "y_label": "normalized overlap sum",
                "y_range": y_range,
                "tick_format": "{:.2f}",
                "x_range": (0.0, 1.0),
                "x_tick_format": "{:.2f}",
                "series": panel_series,
                "references": [
                    {"label": "ideal flat sum", "value": 1.0, "stroke": "#111827", "dash": "7 7"},
                ],
            }
        )
    return stacked_line_panels_svg(
        "Overlap-add flatness is a second window bill, not a footnote",
        "The same window can look fine in one-shot FFT plots and still demand a smaller STFT hop before its overlap sum becomes flat. This pass uses the repo's symmetric window tables at frame length 128; each panel has its own y-scale so the flatter cases stay visible.",
        "phase inside one hop period",
        panels,
        height=1180,
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
    write_svg_asset("window-shapes.svg", shapes_svg)

    spectra_svg = chart_svg(
        "Window spectra near DC",
        "normalized frequency / 0.08 cycles per sample",
        "magnitude (dB)",
        build_spectra(),
        y_range=(-120.0, 5.0),
        x_range=(0.0, 1.0),
    )
    write_svg_asset("window-spectra.svg", spectra_svg)

    offset_loss_svg = chart_svg(
        "Amplitude loss versus bin offset",
        "fractional bin offset",
        "coherent-gain-normalized response (dB)",
        build_offset_loss(),
        y_range=(-4.5, 0.1),
        x_range=(0.0, 0.5),
    )
    write_svg_asset("window-offset-loss.svg", offset_loss_svg)

    half_bin_svg = chart_svg(
        "Half-bin tone leakage near the peak",
        "bins relative to the true tone",
        "normalized magnitude (dB)",
        build_half_bin_leakage(),
        y_range=(-80.0, 2.0),
        x_range=(-4.0, 4.0),
    )
    write_svg_asset("window-half-bin-leakage.svg", half_bin_svg)

    specialist_offset_svg = chart_svg(
        "Blackman-Harris and Nuttall help between bins, but they do not become flat-top",
        "fractional bin offset",
        "coherent-gain-normalized response (dB)",
        build_specialist_offset_loss(),
        y_range=(-1.25, 0.05),
        x_range=(0.0, 0.5),
        height=800,
    )
    write_svg_asset("window-specialist-offset-loss.svg", specialist_offset_svg)

    write_svg_asset("window-amplitude-specialist-summary.svg", build_amplitude_summary())
    write_svg_asset("window-specialist-tradeoffs.svg", build_specialist_tradeoff_summary())
    write_svg_asset("window-overlap-add-flatness.svg", build_overlap_add_svg())

    kaiser_rows = build_kaiser_sweep_rows()
    write_svg_asset("window-kaiser-beta-sweep.svg", build_kaiser_sweep_svg(kaiser_rows))
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

    specialist_rows = build_specialist_metrics_rows()
    with (ART / "window-specialist-metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "coherent_gain",
                "enbw_bins",
                "peak_sidelobe_db",
                "main_lobe_width_bins",
                "scalloping_loss_db",
            ],
        )
        writer.writeheader()
        writer.writerows(specialist_rows)

    overlap_rows = build_overlap_add_rows()
    with (ART / "window-overlap-add-metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "length",
                "hop",
                "overlap_fraction",
                "mean_sum",
                "min_sum",
                "max_sum",
                "max_deviation_pct",
                "ripple_db",
            ],
        )
        writer.writeheader()
        writer.writerows(overlap_rows)

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
