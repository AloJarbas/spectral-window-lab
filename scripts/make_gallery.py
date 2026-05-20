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
from windowlab.overlap import (
    normalized_overlap_add_profile,
    normalized_squared_overlap_add_profile,
    normalized_synthesis_gain_profile,
    overlap_add_summary,
    squared_overlap_add_summary,
)
from windowlab.reconstruct import (
    build_reference_signal,
    periodic_same_window_reconstruction,
    reconstruction_condition_summary,
    simulated_relative_noise_gain,
)
from windowlab.recommend import TASK_PROFILES, build_task_metrics, build_task_rankings
from windowlab.svg import PALETTE, chart_svg, stacked_line_panels_svg, task_heatmap_svg, triptych_bar_svg
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
SYNTHESIS_FIGURE_HOP = 32
SYNTHESIS_FIGURE_WINDOWS = (
    ("hann", "Hann"),
    ("blackman", "Blackman"),
    ("blackman-harris", "Blackman-Harris"),
    ("flattop", "Flat-top"),
)
TASK_WINDOW_ORDER = ("rectangular", "hann", "hamming", "blackman", "kaiser-8.6", "blackman-harris", "nuttall", "flattop")
RECONSTRUCTION_ORDER = (
    "hann",
    "hamming",
    "blackman",
    "blackman-harris",
    "nuttall",
    "flattop",
)
RECONSTRUCTION_HOPS = (64, 32, 16, 8)
RECONSTRUCTION_LENGTH = 128
RECONSTRUCTION_PERIODS = 64


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


def build_weighted_overlap_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for hop in OVERLAP_HOPS:
        overlap_fraction = 1.0 - hop / OVERLAP_LENGTH
        for name, builder in builders_for(OVERLAP_ORDER):
            window = builder(OVERLAP_LENGTH)
            raw_summary = overlap_add_summary(window, hop)
            squared_summary = squared_overlap_add_summary(window, hop)
            rows.append(
                {
                    "name": name,
                    "length": OVERLAP_LENGTH,
                    "hop": hop,
                    "overlap_fraction": overlap_fraction,
                    "raw_max_deviation_pct": raw_summary.max_deviation_fraction * 100.0,
                    "squared_max_deviation_pct": squared_summary.max_deviation_fraction * 100.0,
                    "squared_min_sum": squared_summary.min_sum,
                    "squared_max_sum": squared_summary.max_sum,
                    "synthesis_gain_span_db": squared_summary.ripple_db,
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


def build_synthesis_normalization_svg() -> str:
    raw_values: list[float] = []
    squared_values: list[float] = []
    gain_values: list[float] = []
    raw_series = []
    squared_series = []
    gain_series = []
    for name, builder in builders_for(tuple(key for key, _ in SYNTHESIS_FIGURE_WINDOWS)):
        window = builder(OVERLAP_LENGTH)
        display_name = next(label for key, label in SYNTHESIS_FIGURE_WINDOWS if key == name)
        raw_points = normalized_overlap_add_profile(window, SYNTHESIS_FIGURE_HOP)
        squared_points = normalized_squared_overlap_add_profile(window, SYNTHESIS_FIGURE_HOP)
        gain_points = normalized_synthesis_gain_profile(window, SYNTHESIS_FIGURE_HOP)
        raw_values.extend(value for _, value in raw_points)
        squared_values.extend(value for _, value in squared_points)
        gain_values.extend(value for _, value in gain_points)
        raw_series.append({"name": display_name, "stroke": PALETTE.get(name, "#111827"), "points": raw_points, "width": 3})
        squared_series.append({"name": display_name, "stroke": PALETTE.get(name, "#111827"), "points": squared_points, "width": 3})
        gain_series.append({"name": display_name, "stroke": PALETTE.get(name, "#111827"), "points": gain_points, "width": 3})

    panels = [
        {
            "title": f"Quarter-hop raw overlap sum (H = {SYNTHESIS_FIGURE_HOP})",
            "y_label": "normalized raw sum",
            "y_range": _padded_range(raw_values, pad_low=0.08, pad_high=0.1),
            "tick_format": "{:.2f}",
            "x_range": (0.0, 1.0),
            "x_tick_format": "{:.2f}",
            "series": raw_series,
            "references": [{"label": "ideal = 1", "value": 1.0, "stroke": "#6b7280", "dash": "7 7"}],
        },
        {
            "title": "Weighted overlap sum",
            "y_label": "normalized squared sum",
            "y_range": _padded_range(squared_values, pad_low=0.1, pad_high=0.12),
            "tick_format": "{:.2f}",
            "x_range": (0.0, 1.0),
            "x_tick_format": "{:.2f}",
            "series": squared_series,
            "references": [{"label": "ideal = 1", "value": 1.0, "stroke": "#6b7280", "dash": "7 7"}],
        },
        {
            "title": "Implied synthesis gain swing",
            "y_label": "relative synthesis gain",
            "y_range": _padded_range(gain_values, pad_low=0.1, pad_high=0.12),
            "tick_format": "{:.2f}",
            "x_range": (0.0, 1.0),
            "x_tick_format": "{:.2f}",
            "series": gain_series,
            "references": [{"label": "ideal = 1", "value": 1.0, "stroke": "#6b7280", "dash": "7 7"}],
        },
    ]
    return stacked_line_panels_svg(
        "Raw overlap flatness is not the same as the synthesis-normalization rule",
        "Quarter-hop framing is the revealing middle case: raw overlap can look calm while weighted overlap still forces phase-dependent reconstruction gain.",
        "phase in one hop period",
        panels,
        height=1180,
    )


def build_window_selection_rows() -> list[dict[str, float | int | str | bool]]:
    metrics_rows = build_task_metrics(names=TASK_WINDOW_ORDER)
    rankings = build_task_rankings(metrics_rows)
    rows: list[dict[str, float | int | str | bool]] = []
    for task in TASK_PROFILES:
        for ranking in rankings[task.key]:
            rows.append(
                {
                    "task_key": ranking.task_key,
                    "task_title": ranking.task_title,
                    "window": ranking.window,
                    "eligible": ranking.eligible,
                    "rank": ranking.rank,
                    "score": ranking.score,
                    "suitability": ranking.suitability,
                    "enbw_bins": ranking.enbw_bins,
                    "peak_sidelobe_db": ranking.peak_sidelobe_db,
                    "main_lobe_width_bins": ranking.main_lobe_width_bins,
                    "scalloping_loss_db": ranking.scalloping_loss_db,
                    "synthesis_gain_span_db": ranking.synthesis_gain_span_db,
                }
            )
    return rows


def build_window_selection_svg(rows: list[dict[str, float | int | str | bool]]) -> str:
    rankings_by_task: dict[str, list[dict[str, object]]] = {}
    for task in TASK_PROFILES:
        task_rows = [row for row in rows if row["task_key"] == task.key]
        rankings_by_task[task.key] = task_rows
    tasks = [
        {
            "key": task.key,
            "title": task.title,
            "short_label": task.short_label,
            "summary": task.summary,
        }
        for task in TASK_PROFILES
    ]
    return task_heatmap_svg(
        "A bounded window-selection map for actual tasks",
        "This repo now has enough lanes that a single default answer is worse than a short task map. Each column uses guardrails first, then ranks the surviving windows with the repo's existing metrics.",
        list(TASK_WINDOW_ORDER),
        tasks,
        rankings_by_task,
        width=1600,
        height=1600,
    )


def build_reconstruction_condition_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for hop in RECONSTRUCTION_HOPS:
        overlap_fraction = 1.0 - hop / RECONSTRUCTION_LENGTH
        reference_signal = build_reference_signal(RECONSTRUCTION_PERIODS * hop)
        for name, builder in builders_for(RECONSTRUCTION_ORDER):
            window = builder(RECONSTRUCTION_LENGTH)
            summary = reconstruction_condition_summary(window, hop)
            exact = periodic_same_window_reconstruction(reference_signal, window, hop)
            simulated_gain = simulated_relative_noise_gain(window, hop, periods=RECONSTRUCTION_PERIODS, coefficient_noise_std=1e-6, seed=7)
            rows.append(
                {
                    "name": name,
                    "length": RECONSTRUCTION_LENGTH,
                    "hop": hop,
                    "overlap_fraction": overlap_fraction,
                    "min_squared_overlap_fraction": summary.min_denominator_fraction,
                    "max_synthesis_gain": summary.max_synthesis_gain,
                    "mean_relative_noise_gain": summary.mean_relative_noise_gain,
                    "rms_relative_noise_gain": summary.rms_relative_noise_gain,
                    "worst_relative_noise_gain": summary.worst_relative_noise_gain,
                    "simulated_relative_noise_gain": simulated_gain,
                    "exact_reconstruction_rmse": exact.rmse,
                    "exact_reconstruction_max_abs_error": exact.max_abs_error,
                }
            )
    return rows


def build_reconstruction_condition_svg(rows: list[dict[str, float | str]]) -> str:
    x_values = sorted({float(row["overlap_fraction"]) * 100.0 for row in rows})
    panels = []
    configs = [
        (
            "Squared-overlap floor after normalization",
            "minimum d[n] / mean(d)",
            "min_squared_overlap_fraction",
            "{:.2f}",
            1.0,
        ),
        (
            "RMS coefficient-noise gain from normalized overlap-add",
            "relative RMS noise gain",
            "rms_relative_noise_gain",
            "{:.2f}",
            1.0,
        ),
        (
            "Worst-point coefficient-noise gain",
            "relative worst-case noise gain",
            "worst_relative_noise_gain",
            "{:.2f}",
            1.0,
        ),
    ]
    for title, y_label, key, tick_format, reference in configs:
        values: list[float] = [float(row[key]) for row in rows]
        panel_series = []
        for name, _ in builders_for(RECONSTRUCTION_ORDER):
            points = [
                (float(row["overlap_fraction"]) * 100.0, float(row[key]))
                for row in rows
                if row["name"] == name
            ]
            panel_series.append({"name": name, "stroke": PALETTE.get(name, "#111827"), "points": points, "width": 3})
        panels.append(
            {
                "title": title,
                "y_label": y_label,
                "y_range": _padded_range(values + [reference], pad_low=0.08, pad_high=0.1, clamp_min=0.0),
                "tick_format": tick_format,
                "x_range": (min(x_values), max(x_values)),
                "x_tick_format": "{:.1f}",
                "series": panel_series,
                "references": [{"label": "ideal = 1", "value": reference, "stroke": "#6b7280", "dash": "7 7"}],
            }
        )
    return stacked_line_panels_svg(
        "Same-window overlap-add can be exact and still be poorly conditioned",
        "Normalized overlap-add reconstructs perfectly in exact arithmetic whenever the squared-overlap denominator stays positive. The calmer question is different: how much tiny frame-coefficient noise gets amplified after normalization as the hop shrinks or grows?",
        "overlap (%)",
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
    write_svg_asset("window-synthesis-normalization-bill.svg", build_synthesis_normalization_svg())

    reconstruction_rows = build_reconstruction_condition_rows()
    write_svg_asset("window-reconstruction-conditioning.svg", build_reconstruction_condition_svg(reconstruction_rows))

    selection_rows = build_window_selection_rows()
    write_svg_asset("window-selection-map.svg", build_window_selection_svg(selection_rows))

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

    weighted_rows = build_weighted_overlap_rows()
    with (ART / "window-synthesis-normalization-metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "length",
                "hop",
                "overlap_fraction",
                "raw_max_deviation_pct",
                "squared_max_deviation_pct",
                "squared_min_sum",
                "squared_max_sum",
                "synthesis_gain_span_db",
            ],
        )
        writer.writeheader()
        writer.writerows(weighted_rows)

    with (ART / "window-selection-map.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_key",
                "task_title",
                "window",
                "eligible",
                "rank",
                "score",
                "suitability",
                "enbw_bins",
                "peak_sidelobe_db",
                "main_lobe_width_bins",
                "scalloping_loss_db",
                "synthesis_gain_span_db",
            ],
        )
        writer.writeheader()
        writer.writerows(selection_rows)

    with (ART / "window-reconstruction-conditioning.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "length",
                "hop",
                "overlap_fraction",
                "min_squared_overlap_fraction",
                "max_synthesis_gain",
                "mean_relative_noise_gain",
                "rms_relative_noise_gain",
                "worst_relative_noise_gain",
                "simulated_relative_noise_gain",
                "exact_reconstruction_rmse",
                "exact_reconstruction_max_abs_error",
            ],
        )
        writer.writeheader()
        writer.writerows(reconstruction_rows)

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
