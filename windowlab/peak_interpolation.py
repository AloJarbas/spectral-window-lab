from __future__ import annotations

from dataclasses import dataclass
from html import escape
import csv
import json
import math
from pathlib import Path
from textwrap import wrap
from typing import Sequence

from .metrics import (
    coherent_gain_normalized_response,
    equivalent_noise_bandwidth_bins,
    null_to_null_main_lobe_width,
    scalloping_loss_db,
)
from .windows import build_window

DEFAULT_WINDOWS: tuple[str, ...] = ("blackman", "blackman-harris", "flattop")
DEFAULT_PROBE_FFTS: tuple[int, ...] = (256, 512, 1024, 2048, 4096)
DEFAULT_PHASE_STEPS = 2400
DEFAULT_LENGTH = 129
DEFAULT_HIGHLIGHT_FFT = 256
ESTIMATOR_ORDER: tuple[str, ...] = ("sampled", "parabolic-linear", "parabolic-log")
ESTIMATOR_LABELS = {
    "sampled": "sampled peak",
    "parabolic-linear": "3-point parabola on magnitude",
    "parabolic-log": "3-point parabola on log magnitude",
}
ESTIMATOR_COLORS = {
    "sampled": "#dc2626",
    "parabolic-linear": "#2563eb",
    "parabolic-log": "#059669",
}
WINDOW_LABELS = {
    "blackman": "Blackman",
    "blackman-harris": "Blackman-Harris",
    "flattop": "Flat-top",
}


@dataclass(frozen=True)
class PeakInterpolationRow:
    window: str
    estimator: str
    fft_size: int
    length: int
    bin_step_bins: float
    worst_underread_db: float
    worst_overread_db: float
    rms_bias_db: float
    mean_abs_bias_db: float
    p95_abs_bias_db: float
    enbw_bins: float
    scalloping_loss_db: float
    main_lobe_width_bins: float

    @property
    def worst_abs_bias_db(self) -> float:
        return max(self.worst_underread_db, self.worst_overread_db)

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "window": self.window,
            "estimator": self.estimator,
            "fft_size": self.fft_size,
            "length": self.length,
            "bin_step_bins": self.bin_step_bins,
            "worst_underread_db": self.worst_underread_db,
            "worst_overread_db": self.worst_overread_db,
            "worst_abs_bias_db": self.worst_abs_bias_db,
            "rms_bias_db": self.rms_bias_db,
            "mean_abs_bias_db": self.mean_abs_bias_db,
            "p95_abs_bias_db": self.p95_abs_bias_db,
            "enbw_bins": self.enbw_bins,
            "scalloping_loss_db": self.scalloping_loss_db,
            "main_lobe_width_bins": self.main_lobe_width_bins,
        }


@dataclass(frozen=True)
class PeakInterpolationStudy:
    length: int
    probe_ffts: tuple[int, ...]
    phase_steps: int
    windows: tuple[str, ...]
    estimators: tuple[str, ...]
    highlight_fft: int
    rows: tuple[PeakInterpolationRow, ...]


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(values)
    index = int(round(q * (len(ordered) - 1)))
    index = max(0, min(len(ordered) - 1, index))
    return ordered[index]


def _parabolic_peak(left: float, center: float, right: float) -> tuple[float, float]:
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-15:
        return 0.0, center
    peak_offset = 0.5 * (left - right) / denominator
    peak_offset = max(-1.0, min(1.0, peak_offset))
    peak_value = center - 0.25 * (left - right) * peak_offset
    return peak_offset, peak_value


def _estimate_amplitude(window: Sequence[float], mismatch: float, *, bin_step_bins: float, estimator: str) -> float:
    center = coherent_gain_normalized_response(window, mismatch)
    if estimator == "sampled":
        return center

    left = coherent_gain_normalized_response(window, bin_step_bins + mismatch)
    right = coherent_gain_normalized_response(window, abs(bin_step_bins - mismatch))
    if estimator == "parabolic-linear":
        _, estimate = _parabolic_peak(left, center, right)
        return estimate
    if estimator == "parabolic-log":
        _, estimate_log = _parabolic_peak(
            math.log(max(left, 1e-15)),
            math.log(max(center, 1e-15)),
            math.log(max(right, 1e-15)),
        )
        return math.exp(estimate_log)
    raise ValueError(f"unknown estimator: {estimator}")


def study_peak_interpolation(
    *,
    length: int = DEFAULT_LENGTH,
    probe_ffts: Sequence[int] = DEFAULT_PROBE_FFTS,
    phase_steps: int = DEFAULT_PHASE_STEPS,
    windows: Sequence[str] = DEFAULT_WINDOWS,
    estimators: Sequence[str] = ESTIMATOR_ORDER,
    highlight_fft: int = DEFAULT_HIGHLIGHT_FFT,
) -> PeakInterpolationStudy:
    if length < 8:
        raise ValueError("length must be at least 8")
    if any(fft < length for fft in probe_ffts):
        raise ValueError("probe FFT sizes must be at least the window length")
    if highlight_fft not in probe_ffts:
        raise ValueError("highlight_fft must be included in probe_ffts")

    rows: list[PeakInterpolationRow] = []
    for window_name in windows:
        window = build_window(window_name, length)
        enbw = equivalent_noise_bandwidth_bins(window)
        scalloping = abs(scalloping_loss_db(window))
        main_lobe_width = length * null_to_null_main_lobe_width(window, fft_size=16384)
        for probe_fft in probe_ffts:
            bin_step_bins = length / probe_fft
            max_mismatch = bin_step_bins / 2.0
            for estimator in estimators:
                bias_values: list[float] = []
                for index in range(phase_steps + 1):
                    mismatch = max_mismatch * index / phase_steps
                    estimate = _estimate_amplitude(window, mismatch, bin_step_bins=bin_step_bins, estimator=estimator)
                    bias_values.append(20.0 * math.log10(max(estimate, 1e-15)))
                abs_bias = [abs(value) for value in bias_values]
                rows.append(
                    PeakInterpolationRow(
                        window=window_name,
                        estimator=estimator,
                        fft_size=int(probe_fft),
                        length=length,
                        bin_step_bins=bin_step_bins,
                        worst_underread_db=max(0.0, -min(bias_values)),
                        worst_overread_db=max(0.0, max(bias_values)),
                        rms_bias_db=math.sqrt(sum(value * value for value in bias_values) / len(bias_values)),
                        mean_abs_bias_db=sum(abs_bias) / len(abs_bias),
                        p95_abs_bias_db=_quantile(abs_bias, 0.95),
                        enbw_bins=enbw,
                        scalloping_loss_db=scalloping,
                        main_lobe_width_bins=main_lobe_width,
                    )
                )

    return PeakInterpolationStudy(
        length=length,
        probe_ffts=tuple(int(fft) for fft in probe_ffts),
        phase_steps=phase_steps,
        windows=tuple(windows),
        estimators=tuple(estimators),
        highlight_fft=int(highlight_fft),
        rows=tuple(rows),
    )


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


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#334155", width: float = 1.0, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def _polyline(points: Sequence[tuple[float, float]], *, stroke: str, width: float = 3.0) -> str:
    payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" points="{payload}"/>'


def _circle(x: float, y: float, radius: float, *, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'


def _rect(x: float, y: float, width: float, height: float, *, fill: str, stroke: str = "#e5e7eb", radius: float = 18.0, stroke_width: float = 1.0) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width:.1f}"/>'
    )


def render_peak_interpolation_svg(study: PeakInterpolationStudy) -> str:
    width = 1620
    height = 1340
    panel_left = 76.0
    panel_top = 194.0
    panel_gap_x = 34.0
    panel_gap_y = 34.0
    panel_width = (width - 2 * panel_left - panel_gap_x) / 2.0
    panel_height = 456.0

    rows_by_pair = {
        (window, estimator): [row for row in study.rows if row.window == window and row.estimator == estimator]
        for window in study.windows
        for estimator in study.estimators
    }
    x_positions = {fft: index for index, fft in enumerate(study.probe_ffts)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _svg_text(width / 2.0, 42.0, 'Three-point log interpolation opens a compact amplitude lane', size=30, anchor='middle', weight='700'),
        _svg_paragraph(
            width / 2.0,
            78.0,
            f'The earlier audit asked whether flat-top hides a coarse sampled-peak trap. This follow-up asks the next practical question: if you allow one tiny local estimator around the peak, does the amplitude story change? For length {study.length}, the answer is yes.',
            width=118,
            size=15,
            anchor='middle',
        ),
    ]

    legend_y = 154.0
    legend_x = 284.0
    for index, estimator in enumerate(study.estimators):
        x = legend_x + index * 350.0
        parts.append(_line(x, legend_y, x + 28.0, legend_y, stroke=ESTIMATOR_COLORS[estimator], width=3.2))
        parts.append(_svg_text(x + 40.0, legend_y + 5.0, ESTIMATOR_LABELS[estimator], size=14, fill="#111827"))

    def draw_panel(left: float, top: float, window: str, subtitle: str) -> None:
        panel_rows = [row for row in study.rows if row.window == window]
        y_max = max(row.worst_abs_bias_db for row in panel_rows)
        y_max = max(y_max * 1.14, 0.01)
        plot_left = left + 64.0
        plot_right = left + panel_width - 52.0
        plot_top = top + 142.0
        plot_bottom = top + panel_height - 58.0

        def map_x(fft_size: int) -> float:
            step = x_positions[fft_size] / max(1, len(study.probe_ffts) - 1)
            return plot_left + step * (plot_right - plot_left)

        def map_y(value: float) -> float:
            return plot_bottom - value / y_max * (plot_bottom - plot_top)

        parts.append(_rect(left, top, panel_width, panel_height, fill="#ffffff"))
        parts.append(_svg_text(left + 22.0, top + 32.0, WINDOW_LABELS[window], size=20, weight='700'))
        parts.append(_svg_paragraph(left + 22.0, top + 58.0, subtitle, width=62, size=14))
        parts.append(_svg_text(plot_left, top + 124.0, 'worst absolute amplitude bias (dB)', size=13, fill='#6b7280', weight='600'))

        for step in range(5):
            frac = step / 4.0
            y_value = frac * y_max
            y = map_y(y_value)
            parts.append(_line(plot_left, y, plot_right, y, stroke='#e5e7eb', dash='4 6'))
            parts.append(_svg_text(plot_left - 10.0, y + 5.0, f'{y_value:.3f}', size=12, anchor='end', fill='#6b7280'))

        for fft_size in study.probe_ffts:
            x = map_x(fft_size)
            anchor = 'middle'
            if fft_size == study.probe_ffts[0]:
                anchor = 'start'
            elif fft_size == study.probe_ffts[-1]:
                anchor = 'end'
            parts.append(_line(x, plot_top, x, plot_bottom, stroke='#eef1f5', dash='4 6'))
            parts.append(_svg_text(x, plot_bottom + 24.0, str(fft_size), size=11, anchor=anchor, fill='#6b7280'))

        parts.append(_line(plot_left, plot_top, plot_left, plot_bottom, stroke='#334155', width=2.0))
        parts.append(_line(plot_left, plot_bottom, plot_right, plot_bottom, stroke='#334155', width=2.0))

        for estimator in study.estimators:
            rows = rows_by_pair[(window, estimator)]
            points = [(map_x(row.fft_size), map_y(row.worst_abs_bias_db)) for row in rows]
            parts.append(_polyline(points, stroke=ESTIMATOR_COLORS[estimator]))
            highlight_row = next(row for row in rows if row.fft_size == study.highlight_fft)
            parts.append(_circle(map_x(study.highlight_fft), map_y(highlight_row.worst_abs_bias_db), 5.0, fill=ESTIMATOR_COLORS[estimator]))

        parts.append(_svg_text((plot_left + plot_right) / 2.0, plot_bottom + 46.0, 'probe FFT size', size=14, anchor='middle', fill='#374151'))

    draw_panel(
        panel_left,
        panel_top,
        'blackman',
        'Raw sampled peaks leave a real quarter-dB hole here. A log parabola collapses it into a few thousandths of a dB.',
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top,
        'blackman-harris',
        'This is the sharper compact option. The log fit nearly erases the old amplitude gap while ENBW stays far below flat-top.',
    )
    draw_panel(
        panel_left,
        panel_top + panel_height + panel_gap_y,
        'flattop',
        'Flat-top already wins with no extra work. Interpolation is not its advantage; the raw sampled peak was honest from the start.',
    )

    left = panel_left + panel_width + panel_gap_x
    top = panel_top + panel_height + panel_gap_y
    parts.append(_rect(left, top, panel_width, panel_height, fill="#ffffff"))
    parts.append(_svg_text(left + 22.0, top + 32.0, f'{study.highlight_fft}-point snapshot', size=20, weight='700'))
    parts.append(_svg_paragraph(left + 22.0, top + 58.0, 'At the coarsest probe in this audit, the amplitude lane splits in two. Flat-top still wins the no-extra-processing read. But a three-point log parabola gives Blackman and especially Blackman-Harris a compact alternative.', width=64, size=13))

    table_left = left + 20.0
    table_top = top + 132.0
    col_widths = (146.0, 78.0, 106.0, 106.0, 106.0)
    row_height = 58.0
    headers = ('window', 'ENBW', 'sampled', 'linear', 'log')
    x = table_left
    for width_value, header in zip(col_widths, headers):
        parts.append(_rect(x, table_top, width_value, row_height, fill='#13223a', stroke='#cbd5e1', radius=10.0, stroke_width=0.8))
        parts.append(_svg_text(x + width_value / 2.0, table_top + 35.0, header, size=12, anchor='middle', fill='#f8fafc', weight='700'))
        x += width_value

    highlight_rows = {
        window: {
            estimator: next(row for row in rows_by_pair[(window, estimator)] if row.fft_size == study.highlight_fft)
            for estimator in study.estimators
        }
        for window in study.windows
    }

    for row_index, window in enumerate(study.windows, start=1):
        y = table_top + row_index * row_height
        best_bias = min(highlight_rows[window][estimator].worst_abs_bias_db for estimator in study.estimators)
        cells = [
            (WINDOW_LABELS[window], None),
            (f'{highlight_rows[window][study.estimators[0]].enbw_bins:.3f}', None),
            (f'{highlight_rows[window]["sampled"].worst_abs_bias_db:.4f}', highlight_rows[window]["sampled"].worst_abs_bias_db),
            (f'{highlight_rows[window]["parabolic-linear"].worst_abs_bias_db:.4f}', highlight_rows[window]["parabolic-linear"].worst_abs_bias_db),
            (f'{highlight_rows[window]["parabolic-log"].worst_abs_bias_db:.4f}', highlight_rows[window]["parabolic-log"].worst_abs_bias_db),
        ]
        x = table_left
        for index, (text, maybe_bias) in enumerate(cells):
            highlight = maybe_bias is not None and abs(maybe_bias - best_bias) < 1e-12
            fill = '#dcfce7' if highlight else '#ffffff'
            text_fill = '#14532d' if highlight else '#111827'
            if index < 2:
                fill = '#ffffff'
                text_fill = '#111827'
            parts.append(_rect(x, y, col_widths[index], row_height, fill=fill, stroke='#e2e8f0', radius=10.0, stroke_width=0.8))
            parts.append(_svg_text(x + col_widths[index] / 2.0, y + 35.0, text, size=12, anchor='middle', fill=text_fill, weight='700' if highlight else '500'))
            x += col_widths[index]

    blackman_sampled = highlight_rows['blackman']['sampled']
    blackman_log = highlight_rows['blackman']['parabolic-log']
    bh_sampled = highlight_rows['blackman-harris']['sampled']
    bh_log = highlight_rows['blackman-harris']['parabolic-log']
    flat_sampled = highlight_rows['flattop']['sampled']
    flat_log = highlight_rows['flattop']['parabolic-log']
    parts.append(_svg_paragraph(
        left + 22.0,
        top + panel_height - 98.0,
        f'At {study.highlight_fft} points, Blackman drops from {blackman_sampled.worst_abs_bias_db:.3f} dB to {blackman_log.worst_abs_bias_db:.4f} dB and Blackman-Harris drops from {bh_sampled.worst_abs_bias_db:.3f} dB to {bh_log.worst_abs_bias_db:.4f} dB with a log parabola. Flat-top was already inside {flat_sampled.worst_abs_bias_db:.4f} dB raw, while its own log fit rises to {flat_log.worst_abs_bias_db:.4f} dB. So flat-top keeps the zero-extra-work lane, but it no longer owns amplitude honesty outright once interpolation is allowed.',
        width=74,
        size=13,
        fill='#4b5563',
    ))
    parts.append('</svg>')
    return '\n'.join(parts)


def render_peak_interpolation_report(study: PeakInterpolationStudy) -> str:
    def row(window: str, estimator: str, fft_size: int) -> PeakInterpolationRow:
        return next(entry for entry in study.rows if entry.window == window and entry.estimator == estimator and entry.fft_size == fft_size)

    blackman_sampled = row('blackman', 'sampled', study.highlight_fft)
    blackman_linear = row('blackman', 'parabolic-linear', study.highlight_fft)
    blackman_log = row('blackman', 'parabolic-log', study.highlight_fft)
    bh_sampled = row('blackman-harris', 'sampled', study.highlight_fft)
    bh_linear = row('blackman-harris', 'parabolic-linear', study.highlight_fft)
    bh_log = row('blackman-harris', 'parabolic-log', study.highlight_fft)
    flat_sampled = row('flattop', 'sampled', study.highlight_fft)
    flat_log = row('flattop', 'parabolic-log', study.highlight_fft)
    return '\n'.join([
        '# Three-point log peak interpolation opens a compact amplitude lane',
        '',
        'The previous amplitude audit answered one narrow question: if you only read the largest sampled FFT peak, does flat-top hide a coarse-grid trap? It did not.',
        '',
        'This follow-up asks the practical next question:',
        '',
        '- keep the same windows,',
        '- keep the same coarse FFT peak grid,',
        '- but allow one tiny local estimator around the peak instead of stopping at the biggest sampled bin.',
        '',
        'That changes the story more than I expected.',
        '',
        '## The three bounded reads',
        '',
        '1. **sampled peak**: just take the biggest sampled magnitude',
        '2. **3-point parabola on magnitude**: fit a quadratic through the three local magnitudes',
        '3. **3-point parabola on log magnitude**: fit the same parabola after taking `log |X[k]|`',
        '',
        'The last one is still tiny. It only uses the peak bin and its two neighbors. But it bends the practical ranking.',
        '',
        '## Main read at the coarsest probe',
        '',
        f'- at `{study.highlight_fft}` points, **Blackman** falls from `{blackman_sampled.worst_abs_bias_db:.3f} dB` worst-case bias on the raw sampled peak to `{blackman_linear.worst_abs_bias_db:.3f} dB` with a linear parabola and `{blackman_log.worst_abs_bias_db:.4f} dB` with a log parabola',
        f'- **Blackman-Harris** falls from `{bh_sampled.worst_abs_bias_db:.3f} dB` raw to `{bh_linear.worst_abs_bias_db:.3f} dB` linear and `{bh_log.worst_abs_bias_db:.4f} dB` log',
        f'- **flat-top** already sits inside `{flat_sampled.worst_abs_bias_db:.4f} dB` on the raw sampled peak, and its log parabola actually grows that bounded error to `{flat_log.worst_abs_bias_db:.4f} dB`',
        '',
        '## What actually changed',
        '',
        'The old task map was honest for the raw sampled-peak read: flat-top really was the amplitude specialist.',
        '',
        'This new sidecar shows a more conditional statement:',
        '',
        '- if you want amplitude honesty **with no extra processing**, keep flat-top',
        '- if you can afford a **3-point log interpolation**, Blackman-Harris becomes a real compact amplitude option',
        '- Blackman becomes much better too, but Blackman-Harris is the sharper compromise here because it lands at lower bounded bias than Blackman while still costing far less ENBW than flat-top',
        '',
        f'That is the new split: at `{study.highlight_fft}` points, Blackman-Harris reaches `{bh_log.worst_abs_bias_db:.4f} dB` worst-case bias with ENBW `{bh_log.enbw_bins:.3f}` bins, while flat-top needs ENBW `{flat_sampled.enbw_bins:.3f}` bins to win the same job without interpolation.',
        '',
        '## Why the linear parabola is not the same result',
        '',
        'A generic "parabolic interpolation" summary is too mushy. The method matters.',
        '',
        f'- the **linear-magnitude** parabola helps a lot, but it still leaves Blackman-Harris at `{bh_linear.worst_abs_bias_db:.3f} dB`',
        f'- the **log-magnitude** parabola drops that to `{bh_log.worst_abs_bias_db:.4f} dB`',
        '- so this is not just "do any interpolation"; it is a narrower point about which local fit actually matches the lobe shape well enough to matter',
        '',
        '## Practical rule for this repo now',
        '',
        '1. Keep flat-top as the default answer for raw sampled-peak amplitude reads.',
        '2. Add a second amplitude lane: Blackman-Harris plus 3-point log interpolation when you want much lower ENBW and a narrower main lobe.',
        '3. Do not over-credit linear-magnitude parabolas. They help, but they do not change the compact-window ranking as sharply.',
        '',
        '## Scope boundary',
        '',
        'This is still a bounded, noiseless, isolated-tone audit. It does not settle every peak estimator, every noise regime, or every instrument front end. It says something narrower and useful: a tiny local log fit can erase most of the coarse-grid amplitude penalty that made flat-top look uniquely necessary.',
    ]) + '\n'


def write_peak_interpolation_csv(study: PeakInterpolationStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        fieldnames = [
            'window',
            'estimator',
            'fft_size',
            'length',
            'bin_step_bins',
            'worst_underread_db',
            'worst_overread_db',
            'worst_abs_bias_db',
            'rms_bias_db',
            'mean_abs_bias_db',
            'p95_abs_bias_db',
            'enbw_bins',
            'scalloping_loss_db',
            'main_lobe_width_bins',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in study.rows:
            writer.writerow(row.as_dict())
    return path


def write_peak_interpolation_notebook(study: PeakInterpolationStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Peak interpolation amplitude audit\n',
                    '\n',
                    'This notebook is the slower companion to the peak-interpolation sidecar. The question is no longer whether flat-top has a coarse sampled-peak trap. The question is whether one tiny local interpolator changes the amplitude ranking enough to open a compact alternative.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Local estimators\n',
                    '\n',
                    'Given three neighboring magnitude samples `y_{-1}, y_0, y_{+1}`, a quadratic peak fit uses\n',
                    '\n',
                    '$$p = \\frac{1}{2}\\frac{y_{-1} - y_{+1}}{y_{-1} - 2y_0 + y_{+1}}, \\qquad \\hat y = y_0 - \\frac{1}{4}(y_{-1} - y_{+1})p.$$\n',
                    '\n',
                    'This study tries that formula in two lanes: once on the magnitudes themselves and once on `\\log |X[k]|`, then exponentiates back. The difference turns out to matter.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from windowlab.peak_interpolation import study_peak_interpolation\n',
                    '\n',
                    f'study = study_peak_interpolation(length={study.length}, probe_ffts={study.probe_ffts}, highlight_fft={study.highlight_fft})\n',
                    '[(row.window, row.estimator, row.fft_size, round(row.worst_abs_bias_db, 6)) for row in study.rows if row.fft_size == 256]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Figure\n',
                    '\n',
                    '![Peak interpolation audit](../art/window-peak-interpolation-audit.png)\n',
                    '\n',
                    'Read the Blackman-Harris panel first. The raw sampled peak leaves a visible amplitude hole. The linear parabola helps. The log parabola nearly wipes the hole out.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    "rows_256 = [row for row in study.rows if row.fft_size == 256]\n",
                    '[(row.window, row.estimator, round(row.worst_abs_bias_db, 6), round(row.enbw_bins, 3)) for row in rows_256]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Why this changes the map\n',
                    '\n',
                    'The raw sampled-peak lane still belongs to flat-top. But if one tiny 3-point log fit is allowed, Blackman-Harris becomes a serious compact amplitude choice: much lower ENBW than flat-top, yet already down in the few-millith-decibel bias range in this bounded audit.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Caveats\n',
                    '\n',
                    '1. This is noiseless and isolated-tone only.\n',
                    '2. It compares one local interpolator family, not every estimator.\n',
                    '3. The conclusion is conditional: flat-top still wins when you want the sampled peak itself to be honest with no extra work.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    path.write_text(json.dumps(notebook, indent=2) + '\n')
    return path
