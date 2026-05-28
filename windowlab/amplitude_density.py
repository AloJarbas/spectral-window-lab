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
DEFAULT_LENGTH = 129
DEFAULT_PROBE_FFTS: tuple[int, ...] = (256, 512, 1024, 2048, 4096)
DEFAULT_PHASE_STEPS = 2400
DEFAULT_HIGHLIGHT_FFT = 256
WINDOW_LABELS = {
    "blackman": "Blackman",
    "blackman-harris": "Blackman-Harris",
    "flattop": "Flat-top",
}
WINDOW_COLORS = {
    "blackman": "#dc2626",
    "blackman-harris": "#2563eb",
    "flattop": "#7c3aed",
}


@dataclass(frozen=True)
class AmplitudeDensityRow:
    window: str
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
class AmplitudeDensityCurvePoint:
    window: str
    fft_size: int
    mismatch_bins: float
    bias_db: float


@dataclass(frozen=True)
class AmplitudeDensityStudy:
    length: int
    probe_ffts: tuple[int, ...]
    phase_steps: int
    windows: tuple[str, ...]
    highlight_fft: int
    rows: tuple[AmplitudeDensityRow, ...]
    highlight_curve_points: tuple[AmplitudeDensityCurvePoint, ...]


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(values)
    index = int(round(q * (len(ordered) - 1)))
    index = max(0, min(len(ordered) - 1, index))
    return ordered[index]


def _bias_profile(window: Sequence[float], *, probe_fft: int, phase_steps: int) -> list[tuple[float, float]]:
    if phase_steps < 2:
        raise ValueError("phase_steps must be at least 2")
    bin_step_bins = len(window) / probe_fft
    max_mismatch = bin_step_bins / 2.0
    profile: list[tuple[float, float]] = []
    for idx in range(phase_steps + 1):
        mismatch = max_mismatch * idx / phase_steps
        response = coherent_gain_normalized_response(window, mismatch)
        bias_db = 20.0 * math.log10(max(response, 1e-12))
        profile.append((mismatch, bias_db))
    return profile


def study_amplitude_fft_density(
    *,
    length: int = DEFAULT_LENGTH,
    probe_ffts: Sequence[int] = DEFAULT_PROBE_FFTS,
    phase_steps: int = DEFAULT_PHASE_STEPS,
    windows: Sequence[str] = DEFAULT_WINDOWS,
    highlight_fft: int = DEFAULT_HIGHLIGHT_FFT,
) -> AmplitudeDensityStudy:
    if length < 8:
        raise ValueError("length must be at least 8")
    if any(fft < length for fft in probe_ffts):
        raise ValueError("probe FFT sizes must be at least the window length")
    if highlight_fft not in probe_ffts:
        raise ValueError("highlight_fft must be included in probe_ffts")

    rows: list[AmplitudeDensityRow] = []
    highlight_curve_points: list[AmplitudeDensityCurvePoint] = []
    for window_name in windows:
        window = build_window(window_name, length)
        enbw = equivalent_noise_bandwidth_bins(window)
        scalloping = abs(scalloping_loss_db(window))
        main_lobe_width = length * null_to_null_main_lobe_width(window, fft_size=16384)
        for probe_fft in probe_ffts:
            profile = _bias_profile(window, probe_fft=probe_fft, phase_steps=phase_steps)
            bias_values = [bias_db for _, bias_db in profile]
            worst_underread = max(0.0, -min(bias_values))
            worst_overread = max(0.0, max(bias_values))
            abs_bias = [abs(value) for value in bias_values]
            rows.append(
                AmplitudeDensityRow(
                    window=window_name,
                    fft_size=int(probe_fft),
                    length=length,
                    bin_step_bins=length / probe_fft,
                    worst_underread_db=worst_underread,
                    worst_overread_db=worst_overread,
                    rms_bias_db=math.sqrt(sum(value * value for value in bias_values) / len(bias_values)),
                    mean_abs_bias_db=sum(abs_bias) / len(abs_bias),
                    p95_abs_bias_db=_quantile(abs_bias, 0.95),
                    enbw_bins=enbw,
                    scalloping_loss_db=scalloping,
                    main_lobe_width_bins=main_lobe_width,
                )
            )
            if probe_fft == highlight_fft:
                highlight_curve_points.extend(
                    AmplitudeDensityCurvePoint(
                        window=window_name,
                        fft_size=int(probe_fft),
                        mismatch_bins=mismatch,
                        bias_db=bias_db,
                    )
                    for mismatch, bias_db in profile
                )

    return AmplitudeDensityStudy(
        length=length,
        probe_ffts=tuple(int(fft) for fft in probe_ffts),
        phase_steps=phase_steps,
        windows=tuple(windows),
        highlight_fft=int(highlight_fft),
        rows=tuple(rows),
        highlight_curve_points=tuple(highlight_curve_points),
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


def render_amplitude_fft_density_svg(study: AmplitudeDensityStudy) -> str:
    width = 1640
    height = 1320
    panel_left = 82.0
    panel_top = 194.0
    panel_gap_x = 42.0
    panel_gap_y = 34.0
    panel_width = (width - 2 * panel_left - panel_gap_x) / 2.0
    panel_height = 452.0
    rows_by_window = {
        window: [row for row in study.rows if row.window == window]
        for window in study.windows
    }
    x_positions = {fft: index for index, fft in enumerate(study.probe_ffts)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _svg_text(width / 2.0, 42.0, 'Flat-top does not hide a coarse FFT peak-read trap', size=30, anchor='middle', weight='700'),
        _svg_paragraph(
            width / 2.0,
            78.0,
            f'This sidecar asks one narrower question: after coherent-gain normalization, how much bias survives if a tone lands between FFT samples and you only read the biggest sampled peak at length {study.length}? Flat-top stays unusually calm even on a coarse peak grid.',
            width=118,
            size=15,
            anchor='middle',
        ),
    ]

    legend_y = 152.0
    legend_x = 320.0
    for index, window in enumerate(study.windows):
        x = legend_x + index * 300.0
        parts.append(_line(x, legend_y, x + 28.0, legend_y, stroke=WINDOW_COLORS[window], width=3.2))
        parts.append(_svg_text(x + 40.0, legend_y + 5.0, WINDOW_LABELS[window], size=14, fill="#111827"))

    def draw_panel(
        left: float,
        top: float,
        title: str,
        subtitle: str,
        *,
        y_label: str,
        y_lookup: str,
        y_values: list[float],
    ) -> None:
        y_min = 0.0
        y_max = max(y_values) * 1.12 if max(y_values) > 0.0 else 1.0
        plot_left = left + 64.0
        plot_right = left + panel_width - 52.0
        plot_top = top + 138.0
        plot_bottom = top + panel_height - 58.0

        def map_x(fft_size: int) -> float:
            step = x_positions[fft_size] / max(1, len(study.probe_ffts) - 1)
            return plot_left + step * (plot_right - plot_left)

        def map_y(value: float) -> float:
            return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

        parts.append(_rect(left, top, panel_width, panel_height, fill="#ffffff"))
        parts.append(_svg_text(left + 22.0, top + 32.0, title, size=20, weight='700'))
        parts.append(_svg_paragraph(left + 22.0, top + 58.0, subtitle, width=62, size=14))
        parts.append(_svg_text(plot_left, top + 124.0, y_label, size=13, fill='#6b7280', weight='600'))

        for step in range(5):
            frac = step / 4.0
            y_value = y_min + frac * (y_max - y_min)
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

        for window in study.windows:
            rows = rows_by_window[window]
            points = [(map_x(row.fft_size), map_y(getattr(row, y_lookup))) for row in rows]
            parts.append(_polyline(points, stroke=WINDOW_COLORS[window]))
            highlight_row = next(row for row in rows if row.fft_size == study.highlight_fft)
            parts.append(_circle(map_x(study.highlight_fft), map_y(getattr(highlight_row, y_lookup)), 5.0, fill=WINDOW_COLORS[window]))

        parts.append(_svg_text((plot_left + plot_right) / 2.0, plot_bottom + 46.0, 'probe FFT size', size=14, anchor='middle', fill='#374151'))

    draw_panel(
        panel_left,
        panel_top,
        'Worst peak underread versus FFT size',
        'Compact windows still lose real amplitude if you only read the nearest sampled peak. Flat-top barely does.',
        y_label='worst underread (dB)',
        y_lookup='worst_underread_db',
        y_values=[row.worst_underread_db for row in study.rows],
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top,
        '95th-percentile absolute bias',
        'This is the practical middle of the same story: not the one worst phase, but almost all of them.',
        y_label='95th-percentile |bias| (dB)',
        y_lookup='p95_abs_bias_db',
        y_values=[row.p95_abs_bias_db for row in study.rows],
    )

    # Bottom-left profile panel.
    left = panel_left
    top = panel_top + panel_height + panel_gap_y
    plot_left = left + 64.0
    plot_right = left + panel_width - 52.0
    plot_top = top + 138.0
    plot_bottom = top + panel_height - 58.0
    points_by_window = {
        window: [point for point in study.highlight_curve_points if point.window == window]
        for window in study.windows
    }
    max_x = max(point.mismatch_bins for point in study.highlight_curve_points)
    y_min = min(point.bias_db for point in study.highlight_curve_points)
    y_max = max(point.bias_db for point in study.highlight_curve_points)
    y_floor = min(-0.30, y_min * 1.08)
    y_ceiling = max(0.006, y_max * 1.20)

    def map_profile_x(value: float) -> float:
        return plot_left + value / max_x * (plot_right - plot_left)

    def map_profile_y(value: float) -> float:
        return plot_bottom - (value - y_floor) / (y_ceiling - y_floor) * (plot_bottom - plot_top)

    parts.append(_rect(left, top, panel_width, panel_height, fill="#ffffff"))
    parts.append(_svg_text(left + 22.0, top + 32.0, f'{study.highlight_fft}-point peak-bias profile', size=20, weight='700'))
    parts.append(_svg_paragraph(left + 22.0, top + 58.0, f'The x-axis is mismatch to the nearest sampled FFT peak in original-bin units. Blackman and Blackman-Harris only move downward. Flat-top stays almost perfectly level, with a tiny positive hump instead of a hidden underread cliff.', width=64, size=14))
    parts.append(_svg_text(plot_left, top + 124.0, 'peak-read bias (dB)', size=13, fill='#6b7280', weight='600'))

    for tick in range(5):
        frac = tick / 4.0
        y_value = y_floor + frac * (y_ceiling - y_floor)
        y = map_profile_y(y_value)
        parts.append(_line(plot_left, y, plot_right, y, stroke='#e5e7eb', dash='4 6'))
        parts.append(_svg_text(plot_left - 10.0, y + 5.0, f'{y_value:.3f}', size=12, anchor='end', fill='#6b7280'))
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        mismatch = max_x * frac
        x = map_profile_x(mismatch)
        label = f'{mismatch:.3f}' if frac not in {0.0, 1.0} else ('0' if frac == 0.0 else f'{mismatch:.3f}')
        parts.append(_line(x, plot_top, x, plot_bottom, stroke='#eef1f5', dash='4 6'))
        parts.append(_svg_text(x, plot_bottom + 24.0, label, size=11, anchor='middle', fill='#6b7280'))
    parts.append(_line(plot_left, plot_top, plot_left, plot_bottom, stroke='#334155', width=2.0))
    parts.append(_line(plot_left, plot_bottom, plot_right, plot_bottom, stroke='#334155', width=2.0))
    for window in study.windows:
        curve = points_by_window[window]
        points = [(map_profile_x(point.mismatch_bins), map_profile_y(point.bias_db)) for point in curve]
        parts.append(_polyline(points, stroke=WINDOW_COLORS[window]))
        end_point = curve[-1]
        parts.append(_circle(map_profile_x(end_point.mismatch_bins), map_profile_y(end_point.bias_db), 4.8, fill=WINDOW_COLORS[window]))
    parts.append(_svg_text((plot_left + plot_right) / 2.0, plot_bottom + 46.0, 'mismatch to nearest sampled peak (bins)', size=14, anchor='middle', fill='#374151'))

    # Bottom-right summary panel.
    left = panel_left + panel_width + panel_gap_x
    top = panel_top + panel_height + panel_gap_y
    parts.append(_rect(left, top, panel_width, panel_height, fill="#ffffff"))
    parts.append(_svg_text(left + 22.0, top + 32.0, f'{study.highlight_fft}-point snapshot', size=20, weight='700'))
    parts.append(_svg_paragraph(left + 22.0, top + 58.0, 'The flat-top row is the punchline. Width and ENBW still cost plenty, but the sampled peak is already honest enough for isolated-tone amplitude.', width=64, size=13))

    table_left = left + 20.0
    table_top = top + 132.0
    col_widths = (154.0, 84.0, 106.0, 106.0, 106.0)
    row_height = 58.0
    headers = ('window', 'ENBW', 'scallop |dB|', 'underread', 'overread')
    x = table_left
    for width_value, header in zip(col_widths, headers):
        parts.append(_rect(x, table_top, width_value, row_height, fill='#13223a', stroke='#cbd5e1', radius=10.0, stroke_width=0.8))
        parts.append(_svg_text(x + width_value / 2.0, table_top + 35.0, header, size=12, anchor='middle', fill='#f8fafc', weight='700'))
        x += width_value

    highlight_rows = [next(row for row in rows_by_window[window] if row.fft_size == study.highlight_fft) for window in study.windows]
    best_enbw = min(row.enbw_bins for row in highlight_rows)
    best_scalloping = min(row.scalloping_loss_db for row in highlight_rows)
    best_underread = min(row.worst_underread_db for row in highlight_rows)
    best_overread = min(row.worst_overread_db for row in highlight_rows)

    for row_index, row in enumerate(highlight_rows, start=1):
        y = table_top + row_index * row_height
        cells = [
            (WINDOW_LABELS[row.window], 'window'),
            (f'{row.enbw_bins:.3f}', 'enbw_bins'),
            (f'{row.scalloping_loss_db:.4f}', 'scalloping_loss_db'),
            (f'{row.worst_underread_db:.4f}', 'worst_underread_db'),
            (f'{row.worst_overread_db:.4f}', 'worst_overread_db'),
        ]
        x = table_left
        for (text, key), width_value in zip(cells, col_widths):
            highlight = (
                (key == 'enbw_bins' and abs(row.enbw_bins - best_enbw) < 1e-12)
                or (key == 'scalloping_loss_db' and abs(row.scalloping_loss_db - best_scalloping) < 1e-12)
                or (key == 'worst_underread_db' and abs(row.worst_underread_db - best_underread) < 1e-12)
                or (key == 'worst_overread_db' and abs(row.worst_overread_db - best_overread) < 1e-12)
            )
            fill = '#dcfce7' if highlight and key != 'window' else '#ffffff'
            text_fill = '#14532d' if fill == '#dcfce7' else '#111827'
            parts.append(_rect(x, y, width_value, row_height, fill=fill, stroke='#e2e8f0', radius=10.0, stroke_width=0.8))
            parts.append(_svg_text(x + width_value / 2.0, y + 35.0, text, size=12, anchor='middle', fill=text_fill, weight='700' if fill == '#dcfce7' else '500'))
            x += width_value

    flat = next(row for row in highlight_rows if row.window == 'flattop')
    bh = next(row for row in highlight_rows if row.window == 'blackman-harris')
    blackman = next(row for row in highlight_rows if row.window == 'blackman')
    parts.append(_svg_paragraph(
        left + 22.0,
        top + panel_height - 76.0,
        f'At {study.highlight_fft} points, Blackman still underreads by {blackman.worst_underread_db:.3f} dB and Blackman-Harris by {bh.worst_underread_db:.3f} dB. Flat-top stays inside +{flat.worst_overread_db:.4f} / -{flat.worst_underread_db:.4f} dB. So the amplitude lane is paying for width and ENBW, not a hidden coarse-grid tax.',
        width=74,
        size=13,
        fill='#4b5563',
    ))
    parts.append('</svg>')
    return '\n'.join(parts)


def render_amplitude_fft_density_report(study: AmplitudeDensityStudy) -> str:
    row = lambda window, fft: next(entry for entry in study.rows if entry.window == window and entry.fft_size == fft)
    blackman_256 = row('blackman', study.highlight_fft)
    bh_256 = row('blackman-harris', study.highlight_fft)
    flat_256 = row('flattop', study.highlight_fft)
    bh_512 = row('blackman-harris', 512)
    flat_512 = row('flattop', 512)
    return '\n'.join([
        '# Flat-top does not hide a coarse FFT peak-read trap',
        '',
        'The task map already gives flat-top the amplitude lane. The remaining honest numerical question was narrower:',
        '',
        '- if a tone lands between FFT samples,',
        '- and you only read the largest sampled peak after coherent-gain normalization,',
        '- does flat-top hide a new coarse-grid amplitude error that the earlier scalloping note did not expose?',
        '',
        'This sidecar says **no**. The amplitude-specialist lane is already very grid-stable on that specific read.',
        '',
        f'The study keeps symmetric length `{study.length}` windows and sweeps a sampled-peak ladder of `{", ".join(str(fft) for fft in study.probe_ffts)}` points. For each FFT size, it measures the peak-read bias that survives when the tone can sit anywhere between two sampled FFT peaks.',
        '',
        '## Main read',
        '',
        f'- at `{study.highlight_fft}` points, **Blackman** still underreads by as much as `{blackman_256.worst_underread_db:.3f} dB`',
        f'- at the same probe, **Blackman-Harris** still underreads by `{bh_256.worst_underread_db:.3f} dB`',
        f'- **flat-top** stays inside `+{flat_256.worst_overread_db:.4f} / -{flat_256.worst_underread_db:.4f} dB`',
        f'- even at `512` points, Blackman-Harris still carries `{bh_512.worst_underread_db:.3f} dB` of worst-case underread, while flat-top is down at only `+{flat_512.worst_overread_db:.4f} dB`',
        '',
        '## Why this matters',
        '',
        'The earlier amplitude note already said flat-top earns its keep by keeping the main-lobe top very flat. This audit closes the numerical loophole inside that sentence.',
        '',
        'A coarse FFT peak read could, in principle, have reopened a practical amplitude error even after the direct scalloping metric said the window was flat. That is **not** what happens here.',
        '',
        'Instead the split is cleaner:',
        '',
        '- compact windows still lose visible amplitude when the nearest sampled peak misses the true tone',
        '- flat-top mostly does not underread at all on the same sampled peak ladder',
        '- the only visible flat-top wrinkle is a tiny positive hump, not a hidden attenuation cliff',
        '',
        'So the amplitude-specialist lane is paying for **ENBW** and **main-lobe width**, not for a second hidden coarse-grid amplitude tax.',
        '',
        '## Direct metrics that do not move',
        '',
        f'- flat-top ENBW stays `{flat_256.enbw_bins:.3f}` bins and its half-bin scalloping stays `{flat_256.scalloping_loss_db:.4f} dB`',
        f'- Blackman-Harris ENBW stays `{bh_256.enbw_bins:.3f}` bins and its half-bin scalloping stays `{bh_256.scalloping_loss_db:.4f} dB`',
        '- those are direct window properties; the moving part in this audit is only the sampled peak read',
        '',
        '## Practical rule for this repo',
        '',
        '1. Keep letting flat-top win the isolated-tone amplitude lane on purpose.',
        '2. Do not invent a fake warning that flat-top needs heavy zero-padding before its peak read becomes trustworthy.',
        '3. Keep the real warning attached to flat-top: wide main lobe, large ENBW, poor selectivity when nearby lines matter.',
        '',
        '## Scope boundary',
        '',
        'This is a bounded peak-reading audit, not a statement about every amplitude estimator, every interpolation method, or every FFT instrument. It only says something narrower and useful: with these windows, the flat-top peak itself is already very hard to fool by coarse sample spacing.',
    ]) + '\n'


def write_amplitude_fft_density_csv(study: AmplitudeDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        fieldnames = [
            'window',
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


def write_amplitude_fft_density_notebook(study: AmplitudeDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Amplitude-specialist FFT peak-density audit\n',
                    '\n',
                    'This notebook is the slower companion to the amplitude-grid sidecar. The question is not whether flat-top is wide or expensive. The question is whether a coarse sampled FFT peak quietly puts a big amplitude error back into the one job flat-top is supposed to win.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from windowlab.amplitude_density import study_amplitude_fft_density\n',
                    '\n',
                    f'study = study_amplitude_fft_density(length={study.length}, probe_ffts={study.probe_ffts}, highlight_fft={study.highlight_fft})\n',
                    '[(row.window, row.fft_size, round(row.worst_underread_db, 4), round(row.worst_overread_db, 4)) for row in study.rows if row.fft_size in (256, 512)]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## The bounded result\n',
                    '\n',
                    'Blackman and Blackman-Harris still lose visible amplitude on a coarse sampled peak. Flat-top barely moves, and what little it does is a tiny positive hump rather than a new underread cliff.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Figure\n',
                    '\n',
                    '![Amplitude-specialist FFT density audit](../art/window-amplitude-fft-density-audit.png)\n',
                    '\n',
                    'Read the lower-left panel first. The compact windows bend downward immediately. Flat-top sits almost on the zero line. That is the whole point of the sidecar.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    "rows_256 = [row for row in study.rows if row.fft_size == 256]\n",
                    '[(row.window, round(row.worst_underread_db, 4), round(row.worst_overread_db, 4), round(row.enbw_bins, 3)) for row in rows_256]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## What stays fixed\n',
                    '\n',
                    'ENBW, scalloping, and width do not move across this audit. The changing quantity is only the sampled peak read. That keeps this pass from turning into another general window ranking in disguise.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Next questions\n',
                    '\n',
                    '1. Try one peak-interpolation lane only if it changes the practical amplitude story instead of just polishing the same flat-top result.\n',
                    '2. Try one genuinely different desired-dual family only if it bends the dual-path tradeoff instead of landing between the same endpoints.\n',
                    '3. Port the metric core to Julia or Fortran once those toolchains are live and reproducibility stays clean.\n',
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
