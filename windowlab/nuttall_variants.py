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
    coherent_gain,
    coherent_gain_normalized_response,
    equivalent_noise_bandwidth_bins,
    null_to_null_main_lobe_width,
    peak_sidelobe_level_db,
    scalloping_loss_db,
)
from .windows import build_window

DEFAULT_LENGTH = 129
DEFAULT_FFT_SIZE = 16384
DEFAULT_VARIANTS: tuple[str, ...] = (
    'blackman-harris',
    'nuttall-min4-bh',
    'nuttall-continuous',
)
DEFAULT_BANDS: tuple[tuple[float, float], ...] = (
    (6.0, 12.0),
    (12.0, 24.0),
    (24.0, 48.0),
)
DEFAULT_CURVE_START = 4.0
DEFAULT_CURVE_STOP = 48.0
DEFAULT_CURVE_STEPS = 880
VARIANT_LABELS = {
    'blackman-harris': 'Blackman-Harris',
    'nuttall-min4-bh': 'Nuttall min-4-term BH',
    'nuttall-continuous': 'Nuttall continuous',
}
VARIANT_COLORS = {
    'blackman-harris': '#2563eb',
    'nuttall-min4-bh': '#b45309',
    'nuttall-continuous': '#7c3aed',
}


@dataclass(frozen=True)
class NuttallVariantRow:
    window: str
    label: str
    coherent_gain: float
    enbw_bins: float
    peak_sidelobe_db: float
    main_lobe_width_bins: float
    scalloping_loss_db: float
    max_6_12_db: float
    max_12_24_db: float
    max_24_48_db: float

    @property
    def peak_suppression_db(self) -> float:
        return abs(self.peak_sidelobe_db)

    def band_value(self, start: float, stop: float) -> float:
        lookup = {
            (6.0, 12.0): self.max_6_12_db,
            (12.0, 24.0): self.max_12_24_db,
            (24.0, 48.0): self.max_24_48_db,
        }
        return lookup[(float(start), float(stop))]

    def as_dict(self) -> dict[str, float | str]:
        return {
            'window': self.window,
            'label': self.label,
            'coherent_gain': self.coherent_gain,
            'enbw_bins': self.enbw_bins,
            'peak_sidelobe_db': self.peak_sidelobe_db,
            'peak_suppression_db': self.peak_suppression_db,
            'main_lobe_width_bins': self.main_lobe_width_bins,
            'scalloping_loss_db': self.scalloping_loss_db,
            'max_6_12_db': self.max_6_12_db,
            'max_12_24_db': self.max_12_24_db,
            'max_24_48_db': self.max_24_48_db,
        }


@dataclass(frozen=True)
class NuttallVariantCurvePoint:
    window: str
    offset_bins: float
    response_db: float


@dataclass(frozen=True)
class NuttallVariantStudy:
    length: int
    fft_size: int
    variants: tuple[str, ...]
    bands: tuple[tuple[float, float], ...]
    curve_start: float
    curve_stop: float
    curve_steps: int
    rows: tuple[NuttallVariantRow, ...]
    curve_points: tuple[NuttallVariantCurvePoint, ...]


def _response_curve(window: Sequence[float], *, start: float, stop: float, steps: int) -> list[tuple[float, float]]:
    if steps < 2:
        raise ValueError('steps must be at least 2')
    curve: list[tuple[float, float]] = []
    for idx in range(steps + 1):
        offset = start + (stop - start) * idx / steps
        response = coherent_gain_normalized_response(window, offset)
        curve.append((offset, 20.0 * math.log10(max(response, 1e-12))))
    return curve


def _band_max(curve: Sequence[tuple[float, float]], start: float, stop: float) -> float:
    values = [response_db for offset, response_db in curve if start <= offset <= stop]
    if not values:
        raise ValueError(f'band [{start}, {stop}] has no sampled points')
    return max(values)


def study_nuttall_variant_split(
    *,
    length: int = DEFAULT_LENGTH,
    fft_size: int = DEFAULT_FFT_SIZE,
    variants: Sequence[str] = DEFAULT_VARIANTS,
    bands: Sequence[tuple[float, float]] = DEFAULT_BANDS,
    curve_start: float = DEFAULT_CURVE_START,
    curve_stop: float = DEFAULT_CURVE_STOP,
    curve_steps: int = DEFAULT_CURVE_STEPS,
) -> NuttallVariantStudy:
    if length < 8:
        raise ValueError('length must be at least 8')
    if fft_size < 8:
        raise ValueError('fft_size must be at least 8')
    rows: list[NuttallVariantRow] = []
    curve_points: list[NuttallVariantCurvePoint] = []
    for variant in variants:
        window = build_window(variant, length)
        curve = _response_curve(window, start=curve_start, stop=curve_stop, steps=curve_steps)
        for offset, response_db in curve:
            curve_points.append(NuttallVariantCurvePoint(window=variant, offset_bins=offset, response_db=response_db))
        rows.append(
            NuttallVariantRow(
                window=variant,
                label=VARIANT_LABELS[variant],
                coherent_gain=coherent_gain(window),
                enbw_bins=equivalent_noise_bandwidth_bins(window),
                peak_sidelobe_db=peak_sidelobe_level_db(window, fft_size=fft_size),
                main_lobe_width_bins=length * null_to_null_main_lobe_width(window, fft_size=fft_size),
                scalloping_loss_db=abs(scalloping_loss_db(window)),
                max_6_12_db=_band_max(curve, 6.0, 12.0),
                max_12_24_db=_band_max(curve, 12.0, 24.0),
                max_24_48_db=_band_max(curve, 24.0, 48.0),
            )
        )
    return NuttallVariantStudy(
        length=length,
        fft_size=fft_size,
        variants=tuple(variants),
        bands=tuple((float(start), float(stop)) for start, stop in bands),
        curve_start=curve_start,
        curve_stop=curve_stop,
        curve_steps=curve_steps,
        rows=tuple(rows),
        curve_points=tuple(curve_points),
    )


def _text(x: float, y: float, value: str, *, size: int = 16, fill: str = '#111827', anchor: str = 'start', weight: str = '400') -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">{escape(value)}</text>'
    )


def _paragraph(x: float, y: float, value: str, *, width: int, size: int = 15, fill: str = '#4b5563', line_height: float = 20.0, anchor: str = 'start') -> str:
    lines = wrap(value, width=width) or [value]
    spans = [f'<tspan x="{x:.1f}" dy="0" text-anchor="{anchor}">{escape(lines[0])}</tspan>']
    spans.extend(f'<tspan x="{x:.1f}" dy="{line_height:.1f}" text-anchor="{anchor}">{escape(line)}</tspan>' for line in lines[1:])
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif">{"".join(spans)}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = '#334155', width: float = 1.0, dash: str | None = None, opacity: float = 1.0) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"{dash_attr}/>'


def _polyline(points: Sequence[tuple[float, float]], *, stroke: str, width: float = 3.0) -> str:
    payload = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" points="{payload}"/>'


def _circle(x: float, y: float, radius: float, *, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'


def _rect(x: float, y: float, width: float, height: float, *, fill: str, stroke: str = '#e5e7eb', radius: float = 18.0, stroke_width: float = 1.0) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width:.1f}"/>'
    )


def render_nuttall_variant_svg(study: NuttallVariantStudy) -> str:
    width = 1720
    height = 1420
    left_panel = (70.0, 182.0, 900.0, 700.0)
    right_panel = (970.0, 182.0, 620.0, 700.0)
    bottom_y = 922.0
    bottom_h = 420.0
    rows_by_window = {row.window: row for row in study.rows}
    curve_by_window = {
        window: [(point.offset_bins, point.response_db) for point in study.curve_points if point.window == window]
        for window in study.variants
    }
    y_min = min(point.response_db for point in study.curve_points) - 2.0
    y_max = max(point.response_db for point in study.curve_points) + 1.0

    def map_x(offset: float) -> float:
        left, _, panel_w, _ = left_panel
        plot_left = left + 78.0
        plot_right = left + panel_w - 34.0
        return plot_left + (offset - study.curve_start) / (study.curve_stop - study.curve_start) * (plot_right - plot_left)

    def map_y(response_db: float) -> float:
        _, top, _, panel_h = left_panel
        plot_top = top + 154.0
        plot_bottom = top + panel_h - 78.0
        return plot_bottom - (response_db - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _text(width / 2, 44, 'One Nuttall variant wins the first sidelobe. Another wins the far tail.', size=31, anchor='middle', weight='700'),
        _paragraph(width / 2, 82, f'This pass splits the repo\'s old bare `nuttall` label into two explicit coefficient families at length {study.length}. The minimum-4-term-Blackman-Harris variant keeps the lowest first sidelobe. The continuous-derivative variant gives some of that back and buys cleaner far-out decay.', width=146, size=16, anchor='middle'),
    ]

    legend_y = 144.0
    legend_x = 290.0
    for index, variant in enumerate(study.variants):
        x = legend_x + index * 350.0
        parts.append(_line(x, legend_y, x + 28.0, legend_y, stroke=VARIANT_COLORS[variant], width=3.5))
        parts.append(_text(x + 40.0, legend_y + 5.0, VARIANT_LABELS[variant], size=15, fill='#111827'))

    # Left panel: far-out leakage curve.
    left, top, panel_w, panel_h = left_panel
    plot_left = left + 78.0
    plot_right = left + panel_w - 34.0
    plot_top = top + 154.0
    plot_bottom = top + panel_h - 78.0
    parts.append(_rect(left, top, panel_w, panel_h, fill='#ffffff'))
    parts.append(_text(left + 24.0, top + 34.0, 'Far-out leakage envelope', size=22, weight='700'))
    parts.append(_paragraph(left + 24.0, top + 62.0, 'The lines show normalized offset response from 4 to 48 bins away from the tone. The shape split is the real point: the minimum-4-term-BH variant keeps the first sidelobe lowest, but the continuous variant falls away faster deeper into the tail.', width=82, size=15))

    for boundary in (6.0, 12.0, 24.0, 48.0):
        x = map_x(boundary)
        parts.append(_line(x, plot_top, x, plot_bottom, stroke='#d1d5db', width=1.1, dash='5 7'))
        label = f'{boundary:.0f}' if boundary < study.curve_stop else f'{boundary:.0f} bins'
        parts.append(_text(x, plot_bottom + 24.0, label, size=12, anchor='middle', fill='#6b7280'))
    for tick in range(math.floor(y_min / 5.0) * 5, math.ceil(y_max / 5.0) * 5 + 1, 5):
        y = map_y(float(tick))
        parts.append(_line(plot_left, y, plot_right, y, stroke='#eef2f7', width=1.0, dash='4 8'))
        parts.append(_text(plot_left - 12.0, y + 4.0, f'{tick:.0f}', size=12, anchor='end', fill='#6b7280'))
    parts.append(_line(plot_left, plot_top, plot_left, plot_bottom, stroke='#334155', width=2.0))
    parts.append(_line(plot_left, plot_bottom, plot_right, plot_bottom, stroke='#334155', width=2.0))
    parts.append(_text(plot_left, plot_top - 26.0, 'normalized response (dB)', size=13, fill='#6b7280', weight='600'))
    parts.append(_text((plot_left + plot_right) / 2.0, plot_bottom + 52.0, 'offset from the tone (bins)', size=14, anchor='middle', fill='#374151'))

    sample_offsets = (6.0, 12.0, 24.0, 48.0)
    for variant in study.variants:
        curve = curve_by_window[variant]
        points = [(map_x(offset), map_y(response_db)) for offset, response_db in curve]
        parts.append(_polyline(points, stroke=VARIANT_COLORS[variant], width=3.3))
        lookup = {round(offset, 3): response_db for offset, response_db in curve}
        for sample_offset in sample_offsets[:-1]:
            nearest = min(curve, key=lambda item: abs(item[0] - sample_offset))
            parts.append(_circle(map_x(nearest[0]), map_y(nearest[1]), 4.8, fill=VARIANT_COLORS[variant]))

    # Right panel: metric table.
    left, top, panel_w, panel_h = right_panel
    parts.append(_rect(left, top, panel_w, panel_h, fill='#ffffff'))
    parts.append(_text(left + 24.0, top + 34.0, 'Metric split at a glance', size=22, weight='700'))
    parts.append(_paragraph(left + 24.0, top + 62.0, 'Best values are shaded. The continuous variant does not win the first-sidelobe contest. It wins the far tail.', width=54, size=15))
    table_left = left + 20.0
    table_top = top + 124.0
    metric_col_w = 188.0
    value_col_w = 134.0
    row_h = 62.0
    metrics = [
        ('peak_suppression_db', 'peak sidelobe |dB|', '{:.2f}', 'high'),
        ('enbw_bins', 'ENBW (bins)', '{:.4f}', 'low'),
        ('scalloping_loss_db', 'scalloping |dB|', '{:.4f}', 'low'),
        ('max_6_12_db', 'max 6–12 bins (dB)', '{:.2f}', 'low'),
        ('max_12_24_db', 'max 12–24 bins (dB)', '{:.2f}', 'low'),
        ('max_24_48_db', 'max 24–48 bins (dB)', '{:.2f}', 'low'),
    ]
    for col, variant in enumerate(study.variants):
        x = table_left + metric_col_w + col * value_col_w
        parts.append(_rect(x, table_top, value_col_w, row_h, fill='#0f172a' if col == 1 else '#13223a', stroke='#cbd5e1', radius=10.0, stroke_width=0.8))
        header_lines = wrap(VARIANT_LABELS[variant], width=14)
        parts.append(_text(x + value_col_w / 2.0, table_top + 26.0, header_lines[0], size=13, anchor='middle', fill='#f8fafc', weight='700'))
        if len(header_lines) > 1:
            parts.append(_text(x + value_col_w / 2.0, table_top + 44.0, header_lines[1], size=12, anchor='middle', fill='#e2e8f0', weight='600'))
    for row_index, (metric_key, label, fmt, direction) in enumerate(metrics, start=1):
        y = table_top + row_index * row_h
        parts.append(_rect(table_left, y, metric_col_w, row_h, fill='#f8fafc', stroke='#e2e8f0', radius=10.0, stroke_width=0.8))
        parts.append(_text(table_left + 14.0, y + 35.0, label, size=14, weight='600'))
        values = [getattr(rows_by_window[variant], metric_key) for variant in study.variants]
        best_value = max(values) if direction == 'high' else min(values)
        for col, variant in enumerate(study.variants):
            x = table_left + metric_col_w + col * value_col_w
            value = getattr(rows_by_window[variant], metric_key)
            fill = '#dcfce7' if abs(value - best_value) < 1e-9 else '#ffffff'
            text_fill = '#14532d' if fill == '#dcfce7' else '#111827'
            parts.append(_rect(x, y, value_col_w, row_h, fill=fill, stroke='#e2e8f0', radius=10.0, stroke_width=0.8))
            parts.append(_text(x + value_col_w / 2.0, y + 35.0, fmt.format(value), size=14, anchor='middle', fill=text_fill, weight='700' if fill == '#dcfce7' else '500'))

    # Bottom cards.
    parts.append(_rect(70.0, bottom_y, 490.0, bottom_h, fill='#ffffff'))
    parts.append(_rect(580.0, bottom_y, 490.0, bottom_h, fill='#ffffff'))
    parts.append(_rect(1090.0, bottom_y, 520.0, bottom_h, fill='#ffffff'))

    bh = rows_by_window['blackman-harris']
    min4 = rows_by_window['nuttall-min4-bh']
    cont = rows_by_window['nuttall-continuous']

    parts.append(_text(94.0, bottom_y + 34.0, '1. First-sidelobe winner', size=22, weight='700'))
    parts.append(_paragraph(94.0, bottom_y + 64.0, f'The old repo `nuttall` is still a legitimate window: its peak sidelobe lands at {min4.peak_sidelobe_db:.2f} dB, deeper than Blackman-Harris ({bh.peak_sidelobe_db:.2f} dB) and deeper than the continuous variant ({cont.peak_sidelobe_db:.2f} dB). If the job is mostly “push the first sidelobe down,” the minimum-4-term-BH branch still deserves the nod.', width=51, size=16))

    parts.append(_text(604.0, bottom_y + 34.0, '2. Far-tail winner', size=22, weight='700'))
    parts.append(_paragraph(604.0, bottom_y + 64.0, f'The deeper tail flips the story. In the 24–48 bin band the minimum-4-term-BH variant only gets down to {min4.max_24_48_db:.2f} dB, while the continuous variant reaches {cont.max_24_48_db:.2f} dB. That is the real naming trap: one family member wins the first sidelobe, the other wins far-out decay.', width=49, size=16))

    parts.append(_text(1114.0, bottom_y + 34.0, '3. Naming rule for the repo', size=22, weight='700'))
    parts.append(_paragraph(1114.0, bottom_y + 64.0, 'So the bare name `nuttall` is not good enough once the repo starts teaching sidelobe falloff. Keep `nuttall` as a compatibility alias for the current minimum-4-term-BH implementation, but surface both variants explicitly in the new sidecar and in future weak-spur-at-distance work.', width=52, size=16))

    parts.append('</svg>')
    return '\n'.join(parts)


def render_nuttall_variant_report(study: NuttallVariantStudy) -> str:
    rows = {row.window: row for row in study.rows}
    bh = rows['blackman-harris']
    min4 = rows['nuttall-min4-bh']
    cont = rows['nuttall-continuous']
    return '\n'.join([
        '# Nuttall variants split one low-sidelobe story into two different jobs',
        '',
        'The repo already had a good deep-sidelobe branch. What it did not have was an honest answer to one quieter naming problem:',
        '',
        '- the current `nuttall` implementation is real,',
        '- but it is **not** the only coefficient set people mean by `Nuttall`,',
        '- and that difference becomes important as soon as the question shifts from **first sidelobe depth** to **far-out decay**.',
        '',
        'This sidecar keeps the existing Blackman-Harris comparison and adds one explicit split inside the Nuttall family:',
        '',
        '- **Blackman-Harris**',
        '- **Nuttall minimum 4-term Blackman-Harris** (the repo\'s current `nuttall`)',
        '- **Nuttall continuous-derivative variant**',
        '',
        f'All three are measured at length `{study.length}` with the repo\'s standard-library metric code and a dense `{study.fft_size}`-point sampled-spectrum read for peak-sidelobe and width values.',
        '',
        '## Main read',
        '',
        f'- the repo\'s current `nuttall` still wins the **first-sidelobe** contest: `{min4.peak_sidelobe_db:.2f} dB` versus `{bh.peak_sidelobe_db:.2f} dB` for Blackman-Harris and `{cont.peak_sidelobe_db:.2f} dB` for the continuous variant',
        f'- in the near tail (`6–12` bins), that same variant also stays lowest: `{min4.max_6_12_db:.2f} dB` versus `{bh.max_6_12_db:.2f} dB` and `{cont.max_6_12_db:.2f} dB`',
        f'- but the deeper tail flips the story: in the `24–48` bin band the continuous variant reaches `{cont.max_24_48_db:.2f} dB`, while the minimum-4-term-BH variant stalls at `{min4.max_24_48_db:.2f} dB`',
        f'- Blackman-Harris lands between those two stories: `{bh.max_24_48_db:.2f} dB` in the same far-out band',
        '',
        '## Why this matters',
        '',
        'The old deep-sidelobe note is still fine. Blackman-Harris and the repo\'s current Nuttall implementation really are deep-sidelobe specialists instead of amplitude specialists.',
        '',
        'What changes is the next sentence. Once the repo wants to talk about **weak spurs farther away from the carrier** or **sidelobe falloff**, the bare word `nuttall` stops being precise enough.',
        '',
        'That is because the family split is real:',
        '',
        '- the **minimum-4-term-BH** branch spends more of the cosine-sum degrees of freedom on crushing the first sidelobe',
        '- the **continuous-derivative** branch gives some of that back and buys a cleaner far tail',
        '',
        'So these are not two names for the same ranking. They are two different design bets.',
        '',
        '## Local metric snapshot',
        '',
        '| variant | coherent gain | ENBW (bins) | peak sidelobe (dB) | scalloping loss (dB) | max 6–12 bins (dB) | max 12–24 bins (dB) | max 24–48 bins (dB) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
        f'| Blackman-Harris | `{bh.coherent_gain:.6f}` | `{bh.enbw_bins:.4f}` | `{bh.peak_sidelobe_db:.2f}` | `-{bh.scalloping_loss_db:.4f}` | `{bh.max_6_12_db:.2f}` | `{bh.max_12_24_db:.2f}` | `{bh.max_24_48_db:.2f}` |',
        f'| Nuttall min-4-term BH | `{min4.coherent_gain:.6f}` | `{min4.enbw_bins:.4f}` | `{min4.peak_sidelobe_db:.2f}` | `-{min4.scalloping_loss_db:.4f}` | `{min4.max_6_12_db:.2f}` | `{min4.max_12_24_db:.2f}` | `{min4.max_24_48_db:.2f}` |',
        f'| Nuttall continuous | `{cont.coherent_gain:.6f}` | `{cont.enbw_bins:.4f}` | `{cont.peak_sidelobe_db:.2f}` | `-{cont.scalloping_loss_db:.4f}` | `{cont.max_6_12_db:.2f}` | `{cont.max_12_24_db:.2f}` | `{cont.max_24_48_db:.2f}` |',
        '',
        '## Practical rule for this repo',
        '',
        '1. Keep `nuttall` as a compatibility alias for the current minimum-4-term-BH implementation.',
        '2. Expose the two explicit variants whenever the lesson cares about sidelobe falloff instead of only peak sidelobe depth.',
        '3. Stop teaching the lazy sentence “Nuttall decays faster than Blackman-Harris” unless the coefficients are named explicitly.',
        '',
        '## Companion files',
        '',
        '- `windowlab/nuttall_variants.py`',
        '- `art/window-nuttall-variant-split.svg`',
        '- `art/window-nuttall-variant-split.png`',
        '- `art/window-nuttall-variant-split.csv`',
        '- `notebooks/nuttall_variant_split.ipynb`',
        '- `notes/nuttall-is-not-one-window.md`',
        '',
        '## Scope boundary',
        '',
        'This is still a bounded three-window comparison at one length. It is strong enough to clean up the naming problem and split two different sidelobe jobs without pretending the whole cosine-sum family can be reduced to one fixed ranking.',
    ]) + '\n'


def write_nuttall_variant_csv(study: NuttallVariantStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        fieldnames = [
            'window',
            'label',
            'coherent_gain',
            'enbw_bins',
            'peak_sidelobe_db',
            'peak_suppression_db',
            'main_lobe_width_bins',
            'scalloping_loss_db',
            'max_6_12_db',
            'max_12_24_db',
            'max_24_48_db',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in study.rows:
            writer.writerow(row.as_dict())
    return path


def write_nuttall_variant_notebook(study: NuttallVariantStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Nuttall variant split\n',
                    '\n',
                    'This notebook is the slower companion to the Nuttall-variant sidecar. The point is not to add one more named window. The point is to make one naming collision stop hiding two different leakage jobs.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from windowlab.nuttall_variants import study_nuttall_variant_split\n',
                    '\n',
                    f'study = study_nuttall_variant_split(length={study.length}, fft_size={study.fft_size})\n',
                    '[(row.label, round(row.peak_sidelobe_db, 2), round(row.max_24_48_db, 2)) for row in study.rows]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## What to look for\n',
                    '\n',
                    '1. The repo\'s current `nuttall` alias should still win the **first-sidelobe** contest.\n',
                    '2. The continuous-derivative variant should win the **24–48 bin** band.\n',
                    '3. Blackman-Harris should stay in the middle rather than collapsing into either Nuttall story.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Figure\n',
                    '\n',
                    '![Nuttall variant split](../art/window-nuttall-variant-split.png)\n',
                    '\n',
                    'Read the left panel first. The minimum-4-term-BH branch hugs the bottom near the first sidelobe. The continuous branch pulls away lower in the far tail. That is the whole naming problem in one picture.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'rows = {row.window: row for row in study.rows}\n',
                    "rows['nuttall-min4-bh'].peak_sidelobe_db, rows['nuttall-continuous'].max_24_48_db\n",
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Two short exercises\n',
                    '\n',
                    '1. Change the window length and see whether the same first-sidelobe versus far-tail split survives.\n',
                    '2. Add one weak-spur-at-distance scoring rule only if it still says something sharper than the existing task map.\n',
                    '\n',
                    '## Caveat\n',
                    '\n',
                    'This notebook does not settle every cosine-sum design question. It only makes one public naming shortcut stop hiding two real coefficient families.\n',
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
