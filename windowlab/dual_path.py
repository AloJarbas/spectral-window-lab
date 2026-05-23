from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Sequence

from .reconstruct import (
    DualWindowSummary,
    build_reference_signal,
    canonical_dual_window,
    closest_scaled_constant_dual_window,
    dual_window_summary,
    periodic_dual_window_reconstruction,
)
from .windows import WINDOW_BUILDERS


DEFAULT_DUAL_PATH_CASES: tuple[tuple[str, int, str, str], ...] = (
    ("hann", 64, "Hann", "50% overlap"),
    ("hann", 32, "Hann", "75% overlap"),
    ("blackman-harris", 64, "Blackman-Harris", "50% overlap"),
    ("blackman-harris", 32, "Blackman-Harris", "75% overlap"),
    ("flattop", 64, "Flat-top", "50% overlap"),
    ("flattop", 32, "Flat-top", "75% overlap"),
)
DEFAULT_MIXES: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
WINDOW_COLORS = {
    "hann": "#ff7f0e",
    "blackman-harris": "#0f766e",
    "flattop": "#8b5cf6",
}
OVERLAP_STROKES = {
    64: "#2563eb",
    32: "#dc2626",
}
OVERLAP_LABELS = {
    64: "50% overlap",
    32: "75% overlap",
}


@dataclass(frozen=True)
class DualPathRow:
    name: str
    label: str
    hop: int
    overlap_label: str
    mix: float
    relative_constant_rmse: float
    rms_noise_gain: float
    worst_noise_gain: float
    energy_ratio: float
    exact_rmse: float
    exact_max_abs_error: float
    flatness_gap_fraction: float
    noise_ratio_to_canonical: float
    energy_ratio_to_canonical: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "name": self.name,
            "label": self.label,
            "hop": self.hop,
            "overlap_label": self.overlap_label,
            "mix": self.mix,
            "relative_constant_rmse": self.relative_constant_rmse,
            "rms_noise_gain": self.rms_noise_gain,
            "worst_noise_gain": self.worst_noise_gain,
            "energy_ratio": self.energy_ratio,
            "exact_rmse": self.exact_rmse,
            "exact_max_abs_error": self.exact_max_abs_error,
            "flatness_gap_fraction": self.flatness_gap_fraction,
            "noise_ratio_to_canonical": self.noise_ratio_to_canonical,
            "energy_ratio_to_canonical": self.energy_ratio_to_canonical,
        }


def interpolate_dual_windows(first: Iterable[float], second: Iterable[float], mix: float) -> list[float]:
    if not 0.0 <= mix <= 1.0:
        raise ValueError("mix must lie in [0, 1]")
    left = list(first)
    right = list(second)
    if len(left) != len(right):
        raise ValueError("dual windows must have the same length")
    return [(1.0 - mix) * a + mix * b for a, b in zip(left, right)]


def _summary_for_dual(analysis: Sequence[float], dual: Sequence[float], hop: int) -> DualWindowSummary:
    analysis_energy = sum(value * value for value in analysis)
    summary = dual_window_summary(dual, hop)
    return DualWindowSummary(
        hop=summary.hop,
        mean_window_value=summary.mean_window_value,
        relative_constant_rmse=summary.relative_constant_rmse,
        l2_energy=summary.l2_energy / analysis_energy,
        rms_noise_gain=summary.rms_noise_gain,
        worst_noise_gain=summary.worst_noise_gain,
    )


def study_dual_window_paths(
    *,
    cases: Sequence[tuple[str, int, str, str]] = DEFAULT_DUAL_PATH_CASES,
    mixes: Sequence[float] = DEFAULT_MIXES,
    length: int = 128,
    periods: int = 64,
) -> tuple[DualPathRow, ...]:
    rows: list[DualPathRow] = []
    for name, hop, label, overlap_label in cases:
        analysis = WINDOW_BUILDERS[name](length)
        canonical = canonical_dual_window(analysis, hop)
        closest_constant, _ = closest_scaled_constant_dual_window(analysis, hop)
        reference_signal = build_reference_signal(periods * hop)
        endpoint_summaries = {
            0.0: _summary_for_dual(analysis, canonical, hop),
            1.0: _summary_for_dual(analysis, closest_constant, hop),
        }
        canonical_summary = endpoint_summaries[0.0]
        constant_summary = endpoint_summaries[1.0]
        flatness_span = canonical_summary.relative_constant_rmse - constant_summary.relative_constant_rmse
        for mix in mixes:
            dual = interpolate_dual_windows(canonical, closest_constant, mix)
            summary = _summary_for_dual(analysis, dual, hop)
            run = periodic_dual_window_reconstruction(reference_signal, analysis, dual, hop)
            if abs(flatness_span) <= 1e-12:
                flatness_gap_fraction = 0.0
            else:
                flatness_gap_fraction = (summary.relative_constant_rmse - constant_summary.relative_constant_rmse) / flatness_span
            rows.append(
                DualPathRow(
                    name=name,
                    label=label,
                    hop=hop,
                    overlap_label=overlap_label,
                    mix=float(mix),
                    relative_constant_rmse=summary.relative_constant_rmse,
                    rms_noise_gain=summary.rms_noise_gain,
                    worst_noise_gain=summary.worst_noise_gain,
                    energy_ratio=summary.l2_energy,
                    exact_rmse=run.rmse,
                    exact_max_abs_error=run.max_abs_error,
                    flatness_gap_fraction=flatness_gap_fraction,
                    noise_ratio_to_canonical=summary.rms_noise_gain / canonical_summary.rms_noise_gain,
                    energy_ratio_to_canonical=summary.l2_energy / canonical_summary.l2_energy,
                )
            )
    return tuple(rows)


def _case_rows(rows: Sequence[DualPathRow], name: str) -> tuple[tuple[DualPathRow, ...], tuple[DualPathRow, ...]]:
    half = tuple(row for row in rows if row.name == name and row.hop == 64)
    quarter = tuple(row for row in rows if row.name == name and row.hop == 32)
    return half, quarter


def _midpoint_row(rows: Sequence[DualPathRow], name: str, hop: int) -> DualPathRow:
    return next(row for row in rows if row.name == name and row.hop == hop and abs(row.mix - 0.5) < 1e-12)


def _svg_text(x: float, y: float, text: str, *, size: int = 16, fill: str = "#111827", anchor: str = "start", weight: str = "400") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">{escape(text)}</text>'
    )


def _svg_paragraph(x: float, y: float, text: str, *, width: int, size: int = 15, fill: str = "#4b5563", line_height: float = 19.0, anchor: str = "start") -> str:
    lines = wrap(text, width=width) or [text]
    spans = [f'<tspan x="{x:.1f}" dy="0" text-anchor="{anchor}">{escape(lines[0])}</tspan>']
    spans.extend(f'<tspan x="{x:.1f}" dy="{line_height:.1f}" text-anchor="{anchor}">{escape(line)}</tspan>' for line in lines[1:])
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif">{"".join(spans)}</text>'
    )


def render_dual_window_path_svg(rows: Sequence[DualPathRow]) -> str:
    width = 1440
    height = 1440
    left = 70
    right = width - 70
    top = 200
    bottom = height - 72
    panel_gap = 32
    panel_width = (right - left - panel_gap) / 2
    panel_height = (bottom - top - panel_gap) / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _svg_text(width / 2, 44, "Dual-window tradeoff paths: some middle lanes are real, some are not", size=30, anchor="middle", weight="700"),
        _svg_paragraph(
            width / 2,
            78,
            "The old sidecar compared two exact duals: the calm canonical dual and the flattest constant-looking dual. This follow-up traces the whole exact path between them. Because the dual constraint is linear, every convex mix is still exact, so the real question is how quickly the noise bill rises once you start flattening the synthesis window.",
            width=132,
            size=16,
            anchor="middle",
        ),
        '<rect x="72" y="156" width="380" height="28" rx="14" fill="#eff6ff" stroke="#bfdbfe"/>',
        '<rect x="468" y="156" width="380" height="28" rx="14" fill="#fef2f2" stroke="#fecaca"/>',
        _svg_text(262, 175, "blue = 50% overlap", size=14, anchor="middle", fill="#1d4ed8", weight="600"),
        _svg_text(658, 175, "red = 75% overlap", size=14, anchor="middle", fill="#dc2626", weight="600"),
        _svg_text(1110, 175, "each path uses λ = 0, 0.25, 0.5, 0.75, 1", size=14, anchor="middle", fill="#374151", weight="600"),
    ]

    chart_specs = [
        ("hann", 0, 0, "Hann", "The 75% overlap path buys a lot of flatness before the noise bill gets serious."),
        ("blackman-harris", 1, 0, "Blackman-Harris", "Quarter-hop is the strongest compromise lane in the whole set."),
        ("flattop", 0, 1, "Flat-top", "The 75% overlap path has a middle lane, but the 50% case still never becomes calm."),
    ]

    def panel_rect(col: int, row: int) -> tuple[float, float]:
        return (
            left + col * (panel_width + panel_gap),
            top + row * (panel_height + panel_gap),
        )

    for name, col, row, title, subtitle in chart_specs:
        panel_left, panel_top = panel_rect(col, row)
        plot_left = panel_left + 66
        plot_right = panel_left + panel_width - 26
        plot_top = panel_top + 122
        plot_bottom = panel_top + panel_height - 66
        half_rows, quarter_rows = _case_rows(rows, name)
        panel_rows = list(half_rows + quarter_rows)
        x_values = [entry.rms_noise_gain for entry in panel_rows]
        y_values = [entry.relative_constant_rmse for entry in panel_rows]
        x_min = min(x_values)
        x_max = max(x_values)
        y_min = 0.0
        y_max = max(y_values) * 1.12
        x_pad = max(0.05 * (x_max - x_min), 0.05)
        x_min -= x_pad
        x_max += x_pad

        def map_x(value: float) -> float:
            return plot_left + (value - x_min) / (x_max - x_min) * (plot_right - plot_left)

        def map_y(value: float) -> float:
            return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

        parts.append(f'<rect x="{panel_left:.1f}" y="{panel_top:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="18"/>')
        parts.append(_svg_text(panel_left + 24, panel_top + 32, title, size=20, weight="700"))
        parts.append(_svg_paragraph(panel_left + 24, panel_top + 58, subtitle, width=52, size=14))
        parts.append(_svg_text(plot_left, panel_top + 102, "relative constant RMSE", size=13, fill="#374151", weight="600"))
        for case_rows, color, label_x in ((half_rows, OVERLAP_STROKES[64], plot_left), (quarter_rows, OVERLAP_STROKES[32], plot_left + 150)):
            y = panel_top + 102
            parts.append(f'<line x1="{label_x:.1f}" y1="{y + 18:.1f}" x2="{label_x + 24:.1f}" y2="{y + 18:.1f}" stroke="{color}" stroke-width="4"/>')
            parts.append(_svg_text(label_x + 34, y + 23, OVERLAP_LABELS[case_rows[0].hop], size=12, fill=color, weight="600"))

        for step in range(5):
            frac = step / 4
            value = y_min + frac * (y_max - y_min)
            y = map_y(value)
            parts.append(f'<line x1="{plot_left:.1f}" y1="{y:.1f}" x2="{plot_right:.1f}" y2="{y:.1f}" stroke="#e5e7eb" stroke-dasharray="4 6"/>')
            parts.append(_svg_text(plot_left - 10, y + 5, f"{value:.2f}", size=12, anchor="end", fill="#6b7280"))
        for step in range(5):
            frac = step / 4
            value = x_min + frac * (x_max - x_min)
            x = map_x(value)
            parts.append(f'<line x1="{x:.1f}" y1="{plot_top:.1f}" x2="{x:.1f}" y2="{plot_bottom:.1f}" stroke="#f1f5f9" stroke-dasharray="4 6"/>')
            parts.append(_svg_text(x, plot_bottom + 24, f"{value:.2f}", size=12, anchor="middle", fill="#6b7280"))
        parts.append(f'<line x1="{plot_left:.1f}" y1="{plot_top:.1f}" x2="{plot_left:.1f}" y2="{plot_bottom:.1f}" stroke="#334155" stroke-width="1.5"/>')
        parts.append(f'<line x1="{plot_left:.1f}" y1="{plot_bottom:.1f}" x2="{plot_right:.1f}" y2="{plot_bottom:.1f}" stroke="#334155" stroke-width="1.5"/>')
        parts.append(_svg_text((plot_left + plot_right) / 2, plot_bottom + 48, "RMS coefficient-noise gain", size=14, anchor="middle", fill="#374151", weight="600"))

        for case_rows, color in ((half_rows, OVERLAP_STROKES[64]), (quarter_rows, OVERLAP_STROKES[32])):
            points = [(map_x(entry.rms_noise_gain), map_y(entry.relative_constant_rmse)) for entry in case_rows]
            parts.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '"/>'
            )
            for entry, (x, y) in zip(case_rows, points):
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.3" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
                if entry.mix in (0.0, 0.5, 1.0):
                    dx = -8 if entry.mix == 0.0 else (10 if entry.mix == 1.0 else 0)
                    anchor = "end" if entry.mix == 0.0 else ("start" if entry.mix == 1.0 else "middle")
                    parts.append(_svg_text(x + dx, y - 10, f"λ={entry.mix:.1f}", size=11, fill=color, anchor=anchor, weight="700"))

    table_left, table_top = panel_rect(1, 1)
    parts.append(f'<rect x="{table_left:.1f}" y="{table_top:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="18"/>')
    parts.append(_svg_text(table_left + 24, table_top + 32, "Midpoint snapshot (λ = 0.5)", size=20, weight="700"))
    parts.append(_svg_paragraph(table_left + 24, table_top + 58, "Compact read: exactness survives everywhere, so the midpoint rows only track how much flatness the path buys before noise and energy climb.", width=54, size=14))

    headers = [
        (table_left + 24, "case"),
        (table_left + 252, "% gap left"),
        (table_left + 378, "noise×"),
        (table_left + 470, "energy×"),
        (table_left + 564, "flatness"),
    ]
    for x, label in headers:
        parts.append(_svg_text(x, table_top + 132, label, size=12, fill="#6b7280", weight="700"))
    parts.append(f'<line x1="{table_left + 22}" y1="{table_top + 144}" x2="{table_left + panel_width - 22}" y2="{table_top + 144}" stroke="#cbd5e1" stroke-width="1.4"/>')

    midpoint_rows = [
        _midpoint_row(rows, "hann", 64),
        _midpoint_row(rows, "hann", 32),
        _midpoint_row(rows, "blackman-harris", 64),
        _midpoint_row(rows, "blackman-harris", 32),
        _midpoint_row(rows, "flattop", 64),
        _midpoint_row(rows, "flattop", 32),
    ]
    for index, entry in enumerate(midpoint_rows):
        y = table_top + 186 + index * 44
        if index % 2 == 0:
            parts.append(f'<rect x="{table_left + 18}" y="{y - 20:.1f}" width="{panel_width - 36:.1f}" height="34" fill="#f8fafc" rx="8"/>')
        parts.append(_svg_text(table_left + 24, y, f"{entry.label}", size=13, weight="600"))
        parts.append(_svg_text(table_left + 24, y + 16, entry.overlap_label, size=12, fill="#6b7280"))
        parts.append(_svg_text(table_left + 286, y + 8, f"{100.0 * entry.flatness_gap_fraction:.0f}%", size=13))
        parts.append(_svg_text(table_left + 394, y + 8, f"{entry.noise_ratio_to_canonical:.2f}", size=13))
        parts.append(_svg_text(table_left + 484, y + 8, f"{entry.energy_ratio_to_canonical:.2f}", size=13))
        parts.append(_svg_text(table_left + 578, y + 8, f"{entry.relative_constant_rmse:.2f}", size=13))

    parts.append(_svg_paragraph(table_left + 24, table_top + panel_height - 72, "Best middle lane: Blackman-Harris at 75% overlap. Worst rescue attempt: flat-top at 50% overlap.", width=56, size=14))
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def render_dual_window_path_report(rows: Sequence[DualPathRow]) -> str:
    def midpoint(name: str, hop: int) -> DualPathRow:
        return _midpoint_row(rows, name, hop)

    hann_half = midpoint("hann", 64)
    hann_quarter = midpoint("hann", 32)
    bh_half = midpoint("blackman-harris", 64)
    bh_quarter = midpoint("blackman-harris", 32)
    flat_half = midpoint("flattop", 64)
    flat_quarter = midpoint("flattop", 32)

    def gap_closed(row: DualPathRow) -> float:
        return 100.0 * (1.0 - row.flatness_gap_fraction)

    lines = [
        "# Dual-window tradeoff paths",
        "",
        "The last sidecar asked a binary question: canonical dual or closest constant-looking dual?",
        "",
        "This follow-up asks the sharper one:",
        "",
        "**if both endpoints reconstruct exactly, is there a useful middle lane between them, or does the noise bill turn ugly as soon as you start flattening the dual?**",
        "",
        "## Bounded setup",
        "",
        "- frame length `N = 128`",
        "- windows: Hann, Blackman-Harris, flat-top",
        "- hops: `H = 64` and `H = 32`",
        "- mixes: `λ = 0, 0.25, 0.5, 0.75, 1`, where `λ = 0` is the canonical dual and `λ = 1` is the closest constant-looking dual",
        "",
        "Because the dual constraint is linear, every convex mix along that path is still an exact dual. So exact reconstruction is not the story here. The story is how the flatness-versus-noise tradeoff bends between the two endpoints.",
        "",
        "## Main read",
        "",
        f"- **Hann / 75% overlap:** the midpoint already closes about `{gap_closed(hann_quarter):.0f}%` of the flatness gap while raising RMS noise gain by only about `{100.0 * (hann_quarter.noise_ratio_to_canonical - 1.0):.0f}%`",
        f"- **Blackman-Harris / 75% overlap:** this is the strongest compromise lane in the set; the midpoint closes about `{gap_closed(bh_quarter):.0f}%` of the flatness gap for only about `{100.0 * (bh_quarter.noise_ratio_to_canonical - 1.0):.0f}%` more RMS noise",
        f"- **Flat-top / 50% overlap:** even the midpoint stays ugly in absolute terms (`flatness = {flat_half.relative_constant_rmse:.2f}`, `noise = {flat_half.rms_noise_gain:.2f}`), because the whole path lives between two already-hostile endpoints",
        "",
        "So the right lesson is not just “canonical calm, constant noisy.”",
        "",
        "The sharper lesson is this:",
        "",
        "- some windows really do have a usable middle lane between the two exact dual endpoints",
        "- some windows do not, because the starting case is already too hostile for synthesis-window retuning to count as a rescue",
        "",
        "## Midpoint table (`λ = 0.5`)",
        "",
        "| case | gap closed | noise / canonical | energy / canonical | midpoint flatness | midpoint noise |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| Hann / 50% overlap | {gap_closed(hann_half):.0f}% | {hann_half.noise_ratio_to_canonical:.2f}× | {hann_half.energy_ratio_to_canonical:.2f}× | {hann_half.relative_constant_rmse:.3f} | {hann_half.rms_noise_gain:.3f} |",
        f"| Hann / 75% overlap | {gap_closed(hann_quarter):.0f}% | {hann_quarter.noise_ratio_to_canonical:.2f}× | {hann_quarter.energy_ratio_to_canonical:.2f}× | {hann_quarter.relative_constant_rmse:.3f} | {hann_quarter.rms_noise_gain:.3f} |",
        f"| Blackman-Harris / 50% overlap | {gap_closed(bh_half):.0f}% | {bh_half.noise_ratio_to_canonical:.2f}× | {bh_half.energy_ratio_to_canonical:.2f}× | {bh_half.relative_constant_rmse:.3f} | {bh_half.rms_noise_gain:.3f} |",
        f"| Blackman-Harris / 75% overlap | {gap_closed(bh_quarter):.0f}% | {bh_quarter.noise_ratio_to_canonical:.2f}× | {bh_quarter.energy_ratio_to_canonical:.2f}× | {bh_quarter.relative_constant_rmse:.3f} | {bh_quarter.rms_noise_gain:.3f} |",
        f"| Flat-top / 50% overlap | {gap_closed(flat_half):.0f}% | {flat_half.noise_ratio_to_canonical:.2f}× | {flat_half.energy_ratio_to_canonical:.2f}× | {flat_half.relative_constant_rmse:.3f} | {flat_half.rms_noise_gain:.3f} |",
        f"| Flat-top / 75% overlap | {gap_closed(flat_quarter):.0f}% | {flat_quarter.noise_ratio_to_canonical:.2f}× | {flat_quarter.energy_ratio_to_canonical:.2f}× | {flat_quarter.relative_constant_rmse:.3f} | {flat_quarter.rms_noise_gain:.3f} |",
        "",
        "## Practical read",
        "",
        "If the analysis window and hop are already only mildly uncomfortable, there may be a real design lane between the calm minimum-energy dual and the flattest constant-looking dual.",
        "",
        "If the starting case is already hostile, the path is still informative, but it stops being a rescue plan. In those cases the repo's older advice survives unchanged: shrink the hop, or stop insisting on a window that is fighting the framing job.",
        "",
        "## Artifacts",
        "",
        "- `art/window-dual-tradeoff-paths.svg`",
        "- `art/window-dual-tradeoff-paths.png`",
        "- `art/window-dual-tradeoff-paths.csv`",
        "- `notes/dual-window-tradeoff-paths.md`",
        "- `notebooks/dual_window_tradeoff_paths.ipynb`",
    ]
    return "\n".join(lines) + "\n"


def write_dual_window_path_report(rows: Sequence[DualPathRow], output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dual_window_path_report(rows))
    return path


def write_dual_window_path_notebook(output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Dual-window tradeoff paths\n",
                    "\n",
                    "The last sidecar compared two exact duals. This notebook slows down the better question: if both endpoints reconstruct exactly, is there a useful middle lane between them?\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 1. Why every point on the path is still exact\n",
                    "\n",
                    "If `g_c` and `g_f` are both valid duals for the same analysis window `a`, then any convex mix\n",
                    "\n",
                    "`g_λ = (1 - λ) g_c + λ g_f`\n",
                    "\n",
                    "is still a valid dual because the reconstruction constraint is linear in the synthesis window. That means exactness drops out of the comparison and the real question becomes flatness versus noise.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from windowlab.dual_path import study_dual_window_paths\n",
                    "\n",
                    "rows = study_dual_window_paths()\n",
                    "[row for row in rows if row.mix == 0.5]\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 2. The figure\n",
                    "\n",
                    "![Dual-window tradeoff paths](../art/window-dual-tradeoff-paths.png)\n",
                    "\n",
                    "Read each panel left to right. Rightward motion buys flatter-looking synthesis only by paying more coefficient-noise gain. The question is how quickly that price rises.\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 3. Three small problems\n",
                    "\n",
                    "1. Show directly from the overlap-add constraint why any convex combination of two exact duals is still exact.\n",
                    "2. For Blackman-Harris at quarter-hop, decide whether the midpoint is a genuinely useful engineering compromise or only a prettier-looking one. Use the noise and energy columns, not just the plotted curve.\n",
                    "3. Explain why flat-top at half-overlap does not count as 'fixed' even though the midpoint closes part of the flatness gap.\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(notebook, indent=2) + "\n")
    return path


def write_dual_window_path_csv(rows: Sequence[DualPathRow], output: str | Path) -> Path:
    import csv

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "label",
        "hop",
        "overlap_label",
        "mix",
        "relative_constant_rmse",
        "rms_noise_gain",
        "worst_noise_gain",
        "energy_ratio",
        "exact_rmse",
        "exact_max_abs_error",
        "flatness_gap_fraction",
        "noise_ratio_to_canonical",
        "energy_ratio_to_canonical",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(row.as_dict() for row in rows)
    return path
