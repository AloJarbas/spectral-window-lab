from __future__ import annotations

from dataclasses import dataclass
from html import escape
import csv
import json
import math
from pathlib import Path
from textwrap import wrap
from typing import Sequence

from .metrics import equivalent_noise_bandwidth_bins, null_to_null_main_lobe_width, peak_sidelobe_level_db, positive_frequency_spectrum, scalloping_loss_db
from .windows import build_window

DEFAULT_WINDOWS: tuple[str, ...] = ("kaiser-8.6", "blackman-harris", "nuttall")
DEFAULT_LENGTH = 129
DEFAULT_REFERENCE_FFT = 16384
DEFAULT_PROBE_FFTS: tuple[int, ...] = (256, 512, 1024, 2048, 4096)
WINDOW_LABELS = {
    "kaiser-8.6": "Kaiser β=8.6",
    "blackman-harris": "Blackman-Harris",
    "nuttall": "Nuttall",
}
WINDOW_COLORS = {
    "kaiser-8.6": "#dc2626",
    "blackman-harris": "#2563eb",
    "nuttall": "#7c3aed",
}


def _first_local_minimum(values: Sequence[float]) -> int:
    for idx in range(2, len(values)):
        if values[idx - 1] < values[idx - 2] and values[idx - 1] < values[idx]:
            return idx - 1
    return max(2, len(values) // 16)


@dataclass(frozen=True)
class SpecialistDensityRow:
    window: str
    fft_size: int
    reference_fft: int
    enbw_bins: float
    scalloping_loss_db: float
    peak_sidelobe_db: float
    reference_peak_sidelobe_db: float
    peak_sidelobe_peak_bin: float
    reference_peak_sidelobe_peak_bin: float
    first_null_bin: float
    reference_first_null_bin: float
    main_lobe_width_bins: float
    reference_main_lobe_width_bins: float

    @property
    def peak_sidelobe_error_db(self) -> float:
        return abs(self.peak_sidelobe_db - self.reference_peak_sidelobe_db)

    @property
    def peak_location_error_bins(self) -> float:
        return abs(self.peak_sidelobe_peak_bin - self.reference_peak_sidelobe_peak_bin)

    @property
    def first_null_error_bins(self) -> float:
        return abs(self.first_null_bin - self.reference_first_null_bin)

    @property
    def main_lobe_width_error_bins(self) -> float:
        return abs(self.main_lobe_width_bins - self.reference_main_lobe_width_bins)

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "window": self.window,
            "fft_size": self.fft_size,
            "reference_fft": self.reference_fft,
            "enbw_bins": self.enbw_bins,
            "scalloping_loss_db": self.scalloping_loss_db,
            "peak_sidelobe_db": self.peak_sidelobe_db,
            "reference_peak_sidelobe_db": self.reference_peak_sidelobe_db,
            "peak_sidelobe_error_db": self.peak_sidelobe_error_db,
            "peak_sidelobe_peak_bin": self.peak_sidelobe_peak_bin,
            "reference_peak_sidelobe_peak_bin": self.reference_peak_sidelobe_peak_bin,
            "peak_location_error_bins": self.peak_location_error_bins,
            "first_null_bin": self.first_null_bin,
            "reference_first_null_bin": self.reference_first_null_bin,
            "first_null_error_bins": self.first_null_error_bins,
            "main_lobe_width_bins": self.main_lobe_width_bins,
            "reference_main_lobe_width_bins": self.reference_main_lobe_width_bins,
            "main_lobe_width_error_bins": self.main_lobe_width_error_bins,
        }


@dataclass(frozen=True)
class SpecialistDensityStudy:
    length: int
    reference_fft: int
    probe_ffts: tuple[int, ...]
    rows: tuple[SpecialistDensityRow, ...]


def _window_peak_and_null(window: Sequence[float], fft_size: int) -> tuple[float, float, float, float]:
    freqs, mags = positive_frequency_spectrum(window, fft_size=fft_size)
    first_null_idx = _first_local_minimum(mags)
    peak_idx = max(range(first_null_idx + 1, len(mags)), key=lambda idx: mags[idx])
    first_null_bin = freqs[first_null_idx] * len(window)
    peak_bin = freqs[peak_idx] * len(window)
    peak_sidelobe_db = 20.0 * math.log10(max(mags[peak_idx], 1e-12))
    main_lobe_width_bins = 2.0 * freqs[first_null_idx] * len(window)
    return peak_sidelobe_db, peak_bin, first_null_bin, main_lobe_width_bins


def study_specialist_fft_density(
    *,
    length: int = DEFAULT_LENGTH,
    reference_fft: int = DEFAULT_REFERENCE_FFT,
    probe_ffts: Sequence[int] = DEFAULT_PROBE_FFTS,
    windows: Sequence[str] = DEFAULT_WINDOWS,
) -> SpecialistDensityStudy:
    if length < 8:
        raise ValueError("length must be at least 8")
    if reference_fft < 8:
        raise ValueError("reference_fft must be at least 8")
    if any(fft < 8 for fft in probe_ffts):
        raise ValueError("probe FFT sizes must be at least 8")

    rows: list[SpecialistDensityRow] = []
    for window_name in windows:
        window = build_window(window_name, length)
        reference_peak_db, reference_peak_bin, reference_null_bin, reference_width_bins = _window_peak_and_null(window, reference_fft)
        enbw = equivalent_noise_bandwidth_bins(window)
        scalloping = abs(scalloping_loss_db(window))
        for probe_fft in probe_ffts:
            peak_db, peak_bin, first_null_bin, width_bins = _window_peak_and_null(window, probe_fft)
            rows.append(
                SpecialistDensityRow(
                    window=window_name,
                    fft_size=int(probe_fft),
                    reference_fft=int(reference_fft),
                    enbw_bins=enbw,
                    scalloping_loss_db=scalloping,
                    peak_sidelobe_db=peak_db,
                    reference_peak_sidelobe_db=reference_peak_db,
                    peak_sidelobe_peak_bin=peak_bin,
                    reference_peak_sidelobe_peak_bin=reference_peak_bin,
                    first_null_bin=first_null_bin,
                    reference_first_null_bin=reference_null_bin,
                    main_lobe_width_bins=width_bins,
                    reference_main_lobe_width_bins=reference_width_bins,
                )
            )
    return SpecialistDensityStudy(
        length=length,
        reference_fft=reference_fft,
        probe_ffts=tuple(int(fft) for fft in probe_ffts),
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


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#334155", width: int = 1, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def _polyline(points: list[tuple[float, float]], *, stroke: str, width: int = 3) -> str:
    payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" points="{payload}"/>'


def _circle(x: float, y: float, radius: float, *, fill: str, stroke: str = "#ffffff", width: int = 2) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def render_specialist_fft_density_svg(study: SpecialistDensityStudy) -> str:
    width = 1520
    height = 1260
    panel_left = 84
    panel_top = 194
    panel_gap_x = 46
    panel_gap_y = 34
    panel_width = (width - 2 * panel_left - panel_gap_x) / 2
    panel_height = 420
    rows_by_window = {
        window: [row for row in study.rows if row.window == window]
        for window in DEFAULT_WINDOWS
    }
    x_positions = {fft: index for index, fft in enumerate(study.probe_ffts)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _svg_text(width / 2, 42, 'FFT-grid sensitivity is not one deep-sidelobe story', size=30, anchor='middle', weight='700'),
        _svg_paragraph(
            width / 2,
            78,
            f'This follow-up reruns the FFT-density audit on two deep-sidelobe windows instead of only the Kaiser family. Same length {study.length}, same dense reference ({study.reference_fft} points), same probe ladder ({", ".join(str(fft) for fft in study.probe_ffts)}).',
            width=138,
            size=16,
            anchor='middle',
        ),
    ]

    legend_y = 152
    legend_x = 290
    for index, window in enumerate(DEFAULT_WINDOWS):
        x = legend_x + index * 280
        color = WINDOW_COLORS[window]
        label = WINDOW_LABELS[window]
        parts.append(_line(x, legend_y, x + 28, legend_y, stroke=color, width=3))
        parts.append(_svg_text(x + 40, legend_y + 5, label, size=14, fill="#111827"))

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
        plot_left = left + 64
        plot_right = left + panel_width - 52
        plot_top = top + 116
        plot_bottom = top + panel_height - 54

        def map_x(fft_size: int) -> float:
            step = x_positions[fft_size] / max(1, len(study.probe_ffts) - 1)
            return plot_left + step * (plot_right - plot_left)

        def map_y(value: float) -> float:
            return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

        parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="18"/>')
        parts.append(_svg_text(left + 22, top + 32, title, size=20, weight='700'))
        parts.append(_svg_paragraph(left + 22, top + 58, subtitle, width=60, size=14))
        parts.append(_svg_text(plot_left, top + 102, y_label, size=13, fill='#6b7280', weight='600'))

        for step in range(5):
            frac = step / 4
            y_value = y_min + frac * (y_max - y_min)
            y = map_y(y_value)
            parts.append(_line(plot_left, y, plot_right, y, stroke='#e5e7eb', dash='4 6'))
            parts.append(_svg_text(plot_left - 10, y + 5, f'{y_value:.2f}', size=12, anchor='end', fill='#6b7280'))

        for fft_size in study.probe_ffts:
            x = map_x(fft_size)
            anchor = 'middle'
            if fft_size == study.probe_ffts[0]:
                anchor = 'start'
            elif fft_size == study.probe_ffts[-1]:
                anchor = 'end'
            parts.append(_line(x, plot_top, x, plot_bottom, stroke='#eef1f5', dash='4 6'))
            parts.append(_svg_text(x, plot_bottom + 24, str(fft_size), size=11, anchor=anchor, fill='#6b7280'))

        parts.append(_line(plot_left, plot_top, plot_left, plot_bottom, stroke='#334155', width=2))
        parts.append(_line(plot_left, plot_bottom, plot_right, plot_bottom, stroke='#334155', width=2))

        for window in DEFAULT_WINDOWS:
            rows = rows_by_window[window]
            points = [(map_x(row.fft_size), map_y(getattr(row, y_lookup))) for row in rows]
            parts.append(_polyline(points, stroke=WINDOW_COLORS[window]))
            row_512 = next(row for row in rows if row.fft_size == 512)
            x = map_x(512)
            y = map_y(getattr(row_512, y_lookup))
            parts.append(_circle(x, y, 5.0, fill=WINDOW_COLORS[window]))

        parts.append(_svg_text((plot_left + plot_right) / 2, plot_bottom + 46, 'probe FFT size', size=14, anchor='middle', fill='#374151'))

    draw_panel(
        panel_left,
        panel_top,
        'Peak sidelobe error versus FFT size',
        'Kaiser drifts hard, Blackman-Harris stays nearly locked, and Nuttall lands in the middle.',
        y_label='absolute sidelobe error (dB)',
        y_lookup='peak_sidelobe_error_db',
        y_values=[row.peak_sidelobe_error_db for row in study.rows],
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top,
        'Main-lobe width error versus FFT size',
        'Nuttall is the interesting surprise here: the width read can stay wrong after the sidelobe read is already mostly calm.',
        y_label='absolute width error (bins)',
        y_lookup='main_lobe_width_error_bins',
        y_values=[row.main_lobe_width_error_bins for row in study.rows],
    )
    draw_panel(
        panel_left,
        panel_top + panel_height + panel_gap_y,
        'First-sidelobe peak location miss',
        'Blackman-Harris keeps landing almost exactly on the same sampled peak. Nuttall and Kaiser do not.',
        y_label='absolute peak-location miss (bins)',
        y_lookup='peak_location_error_bins',
        y_values=[row.peak_location_error_bins for row in study.rows],
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top + panel_height + panel_gap_y,
        'First-null location miss',
        'This is why the Nuttall width read stays soft longer: at 512 and 1024 the first local minimum can jump to the wrong sampled null.',
        y_label='absolute first-null miss (bins)',
        y_lookup='first_null_error_bins',
        y_values=[row.first_null_error_bins for row in study.rows],
    )

    kaiser_512 = next(row for row in study.rows if row.window == 'kaiser-8.6' and row.fft_size == 512)
    bh_512 = next(row for row in study.rows if row.window == 'blackman-harris' and row.fft_size == 512)
    nuttall_512 = next(row for row in study.rows if row.window == 'nuttall' and row.fft_size == 512)
    parts.append(_svg_paragraph(
        88,
        1178,
        f'At 512 points, Kaiser β=8.6 is still the harsh anchor: {kaiser_512.peak_sidelobe_error_db:.2f} dB of sidelobe error and {kaiser_512.main_lobe_width_error_bins:.2f} bins of width error. Blackman-Harris is effectively grid-stable at the same probe ({bh_512.peak_sidelobe_error_db:.2f} dB, {bh_512.main_lobe_width_error_bins:.2f} bins) because both its first null and first sidelobe peak land almost exactly on sampled locations. Nuttall changes the family read instead of replaying Kaiser: its sidelobe error at 512 is only {nuttall_512.peak_sidelobe_error_db:.2f} dB, but its first-null miss is {nuttall_512.first_null_error_bins:.2f} bins, so the width read stays much softer than the sidelobe read.',
        width=183,
        size=14,
        fill='#4b5563',
    ))
    parts.append('</svg>')
    return '\n'.join(parts)


def render_specialist_fft_density_report(study: SpecialistDensityStudy) -> str:
    row = lambda window, fft: next(entry for entry in study.rows if entry.window == window and entry.fft_size == fft)
    bh_512 = row('blackman-harris', 512)
    nuttall_512 = row('nuttall', 512)
    nuttall_2048 = row('nuttall', 2048)
    kaiser_512 = row('kaiser-8.6', 512)
    return '\n'.join([
        '# Deep-sidelobe FFT-density family audit',
        '',
        'The Kaiser audit left one honest loophole open: maybe every strong low-sidelobe window is this sensitive to FFT grid density. This follow-up checks that claim against **Blackman-Harris** and **Nuttall** instead of assuming one family story covers them all.',
        '',
        f'This pass keeps the same `{study.length}`-sample windows, uses a dense `{study.reference_fft}`-point reference probe, and walks a smaller FFT ladder: `{", ".join(str(fft) for fft in study.probe_ffts)}`.',
        '',
        '## Main read',
        '',
        f'- **Kaiser β=8.6** is still the harsh anchor at `512` points: `|Δ sidelobe| = {kaiser_512.peak_sidelobe_error_db:.2f} dB`, `|Δ width| = {kaiser_512.main_lobe_width_error_bins:.2f}` bins',
        f'- **Blackman-Harris** is almost grid-locked at the same probe: `|Δ sidelobe| = {bh_512.peak_sidelobe_error_db:.2f} dB`, `|Δ width| = {bh_512.main_lobe_width_error_bins:.2f}` bins',
        f'- **Nuttall** is the useful middle case: at `512` points its sidelobe error is only `{nuttall_512.peak_sidelobe_error_db:.2f} dB`, but its width error is still `{nuttall_512.main_lobe_width_error_bins:.2f}` bins',
        f'- by `2048` points, Nuttall closes most of that gap: `|Δ sidelobe| = {nuttall_2048.peak_sidelobe_error_db:.2f} dB`, `|Δ width| = {nuttall_2048.main_lobe_width_error_bins:.2f}` bins',
        '',
        '## Why the family read changes',
        '',
        f'- Blackman-Harris lands its first sidelobe peak within `{bh_512.peak_location_error_bins:.3f}` bins of the dense reference even at `512` points, and its first null is off by only `{bh_512.first_null_error_bins:.3f}` bins',
        f'- Nuttall is different: the same `512`-point grid misses the first sidelobe peak by `{nuttall_512.peak_location_error_bins:.3f}` bins and the first null by `{nuttall_512.first_null_error_bins:.3f}` bins',
        '- that means “deep sidelobe” is not one FFT-density sensitivity class',
        '- the Kaiser warning was real, but it was not universal in the lazy way. Blackman-Harris stays numerically calm; Nuttall stays visibly softer on width until the probe gets denser',
        '',
        '## What stays fixed',
        '',
        f'- Blackman-Harris ENBW stays `{bh_512.enbw_bins:.3f}` bins and its half-bin loss stays `{bh_512.scalloping_loss_db:.3f} dB` across the whole audit',
        f'- Nuttall ENBW stays `{nuttall_512.enbw_bins:.3f}` bins and its half-bin loss stays `{nuttall_512.scalloping_loss_db:.3f} dB` across the whole audit',
        '- those direct-sum metrics do not move; only the sampled-spectrum estimates do',
        '',
        '## Caveat',
        '',
        'This is still a bounded audit of one length and one reference FFT. It is strong enough to separate three different numerical behaviors without pretending the whole world of windows falls into exactly these three buckets.',
        '',
        'Open `art/window-specialist-fft-density-audit.png`, `art/window-specialist-fft-density-audit.csv`, and `notebooks/specialist_fft_density_audit.ipynb` together next.',
    ]) + '\n'


def write_specialist_fft_density_csv(study: SpecialistDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        fieldnames = [
            'window',
            'fft_size',
            'reference_fft',
            'enbw_bins',
            'scalloping_loss_db',
            'peak_sidelobe_db',
            'reference_peak_sidelobe_db',
            'peak_sidelobe_error_db',
            'peak_sidelobe_peak_bin',
            'reference_peak_sidelobe_peak_bin',
            'peak_location_error_bins',
            'first_null_bin',
            'reference_first_null_bin',
            'first_null_error_bins',
            'main_lobe_width_bins',
            'reference_main_lobe_width_bins',
            'main_lobe_width_error_bins',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in study.rows:
            writer.writerow(row.as_dict())
    return path


def write_specialist_fft_density_notebook(study: SpecialistDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Deep-sidelobe FFT-density family audit\n',
                    '\n',
                    'This notebook is the slower companion to `notes/deep-sidelobe-fft-density-family-audit.md`.\n',
                    '\n',
                    'The question is narrower than the Kaiser pass: **do Blackman-Harris and Nuttall inherit the same coarse-FFT failure mode, or was that warning more family-specific than it first looked?**\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from windowlab.specialist_density import study_specialist_fft_density\n',
                    '\n',
                    f'study = study_specialist_fft_density(length={study.length}, reference_fft={study.reference_fft}, probe_ffts={study.probe_ffts})\n',
                    '[(row.window, row.fft_size, round(row.peak_sidelobe_error_db, 3), round(row.main_lobe_width_error_bins, 3)) for row in study.rows if row.fft_size == 512]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## The bounded result\n',
                    '\n',
                    'Blackman-Harris is almost grid-stable on this probe ladder. Nuttall is not. Kaiser stays the harsh anchor.\n',
                    '\n',
                    'That changes the repo in a useful way because it kills the lazy conclusion that “deep sidelobe” is one numerical-measurement class.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## The figure\n',
                    '\n',
                    '![Deep-sidelobe FFT-density family audit](../art/window-specialist-fft-density-audit.png)\n',
                    '\n',
                    'Read the lower row carefully. The Nuttall width story stays soft longer than its sidelobe story because the first local minimum can jump to the wrong sampled null even after the sidelobe peak is already close.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    "rows_512 = [row for row in study.rows if row.fft_size == 512]\n",
                    '[(row.window, round(row.peak_location_error_bins, 3), round(row.first_null_error_bins, 3)) for row in rows_512]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## What stays fixed\n',
                    '\n',
                    'ENBW and scalloping stay fixed for every window in this notebook. The moving part is only the sampled-spectrum estimate. That split is the whole reason to carry this sidecar instead of leaving the FFT-density warning attached only to Kaiser.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Next questions\n',
                    '\n',
                    '1. Check one amplitude-specialist family only if it changes the new family-specific read instead of replaying Kaiser or Nuttall.\n',
                    '2. Try one genuinely different desired-dual family only if it bends the dual-path tradeoff instead of just landing between the same endpoints.\n',
                    '3. Port the metric core to Julia or Fortran once the toolchains are live and the cross-language check can stay reproducible.\n',
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
