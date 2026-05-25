from __future__ import annotations

from dataclasses import dataclass
from html import escape
import csv
import json
from pathlib import Path
from textwrap import wrap
from typing import Sequence

from .metrics import equivalent_noise_bandwidth_bins, null_to_null_main_lobe_width, peak_sidelobe_level_db, scalloping_loss_db
from .windows import kaiser

DEFAULT_BETAS: tuple[float, ...] = tuple(sorted({step / 2 for step in range(29)} | {8.6}))
DEFAULT_LENGTH = 129
DEFAULT_COARSE_FFT = 512
DEFAULT_FINE_FFT = 4096
HIGHLIGHT_BETAS: tuple[float, ...] = (0.0, 8.6, 14.0)
COARSE_COLOR = "#2563eb"
FINE_COLOR = "#dc2626"
ERROR_COLOR = "#7c3aed"
WIDTH_ERROR_COLOR = "#0f766e"


@dataclass(frozen=True)
class KaiserFftDensityRow:
    beta: float
    enbw_bins: float
    scalloping_loss_db: float
    coarse_peak_sidelobe_db: float
    fine_peak_sidelobe_db: float
    coarse_main_lobe_width_bins: float
    fine_main_lobe_width_bins: float

    @property
    def peak_sidelobe_delta_db(self) -> float:
        return self.coarse_peak_sidelobe_db - self.fine_peak_sidelobe_db

    @property
    def peak_sidelobe_error_db(self) -> float:
        return abs(self.peak_sidelobe_delta_db)

    @property
    def main_lobe_width_delta_bins(self) -> float:
        return self.coarse_main_lobe_width_bins - self.fine_main_lobe_width_bins

    @property
    def main_lobe_width_error_bins(self) -> float:
        return abs(self.main_lobe_width_delta_bins)

    def as_dict(self, *, coarse_fft: int, fine_fft: int) -> dict[str, float | int]:
        return {
            "beta": self.beta,
            "coarse_fft": coarse_fft,
            "fine_fft": fine_fft,
            "enbw_bins": self.enbw_bins,
            "scalloping_loss_db": self.scalloping_loss_db,
            "coarse_peak_sidelobe_db": self.coarse_peak_sidelobe_db,
            "fine_peak_sidelobe_db": self.fine_peak_sidelobe_db,
            "peak_sidelobe_delta_db": self.peak_sidelobe_delta_db,
            "peak_sidelobe_error_db": self.peak_sidelobe_error_db,
            "coarse_main_lobe_width_bins": self.coarse_main_lobe_width_bins,
            "fine_main_lobe_width_bins": self.fine_main_lobe_width_bins,
            "main_lobe_width_delta_bins": self.main_lobe_width_delta_bins,
            "main_lobe_width_error_bins": self.main_lobe_width_error_bins,
        }


@dataclass(frozen=True)
class KaiserFftDensityStudy:
    length: int
    coarse_fft: int
    fine_fft: int
    rows: tuple[KaiserFftDensityRow, ...]


@dataclass(frozen=True)
class KaiserFftDensitySummary:
    first_beta_with_one_db_error: float
    first_beta_with_half_bin_width_error: float
    worst_sidelobe_row: KaiserFftDensityRow
    worst_width_row: KaiserFftDensityRow
    beta_86_row: KaiserFftDensityRow


def study_kaiser_fft_density(
    *,
    length: int = DEFAULT_LENGTH,
    coarse_fft: int = DEFAULT_COARSE_FFT,
    fine_fft: int = DEFAULT_FINE_FFT,
    betas: Sequence[float] = DEFAULT_BETAS,
) -> KaiserFftDensityStudy:
    if length < 8:
        raise ValueError("length must be at least 8")
    if coarse_fft < 8 or fine_fft < 8:
        raise ValueError("fft sizes must be at least 8")
    if fine_fft <= coarse_fft:
        raise ValueError("fine_fft must be greater than coarse_fft")
    rows: list[KaiserFftDensityRow] = []
    for beta in betas:
        window = kaiser(length, float(beta))
        rows.append(
            KaiserFftDensityRow(
                beta=float(beta),
                enbw_bins=equivalent_noise_bandwidth_bins(window),
                scalloping_loss_db=abs(scalloping_loss_db(window)),
                coarse_peak_sidelobe_db=peak_sidelobe_level_db(window, fft_size=coarse_fft),
                fine_peak_sidelobe_db=peak_sidelobe_level_db(window, fft_size=fine_fft),
                coarse_main_lobe_width_bins=length * null_to_null_main_lobe_width(window, fft_size=coarse_fft),
                fine_main_lobe_width_bins=length * null_to_null_main_lobe_width(window, fft_size=fine_fft),
            )
        )
    return KaiserFftDensityStudy(length=length, coarse_fft=coarse_fft, fine_fft=fine_fft, rows=tuple(rows))


def summarize_kaiser_fft_density(study: KaiserFftDensityStudy) -> KaiserFftDensitySummary:
    first_beta_with_one_db_error = next(row.beta for row in study.rows if row.peak_sidelobe_error_db >= 1.0)
    first_beta_with_half_bin_width_error = next(row.beta for row in study.rows if row.main_lobe_width_error_bins >= 0.5)
    worst_sidelobe_row = max(study.rows, key=lambda row: row.peak_sidelobe_error_db)
    worst_width_row = max(study.rows, key=lambda row: row.main_lobe_width_error_bins)
    beta_86_row = next(row for row in study.rows if abs(row.beta - 8.6) < 1e-12)
    return KaiserFftDensitySummary(
        first_beta_with_one_db_error=first_beta_with_one_db_error,
        first_beta_with_half_bin_width_error=first_beta_with_half_bin_width_error,
        worst_sidelobe_row=worst_sidelobe_row,
        worst_width_row=worst_width_row,
        beta_86_row=beta_86_row,
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


def render_kaiser_fft_density_svg(study: KaiserFftDensityStudy) -> str:
    width = 1520
    height = 1260
    panel_left = 84
    panel_top = 194
    panel_gap_x = 46
    panel_gap_y = 34
    panel_width = (width - 2 * panel_left - panel_gap_x) / 2
    panel_height = 420
    x_min = min(row.beta for row in study.rows)
    x_max = max(row.beta for row in study.rows)
    summary = summarize_kaiser_fft_density(study)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        _svg_text(width / 2, 42, 'Kaiser sweep needs enough FFT density', size=30, anchor='middle', weight='700'),
        _svg_paragraph(
            width / 2,
            78,
            f'This sidecar reruns the same Kaiser family at length {study.length}, but compares a coarse {study.coarse_fft}-point spectral probe against a denser {study.fine_fft}-point one. ENBW and scalloping stay fixed; the drift lives in the sampled sidelobe and main-lobe measurements.',
            width=138,
            size=16,
            anchor='middle',
        ),
        '<rect x="72" y="144" width="210" height="28" rx="14" fill="#eff6ff" stroke="#bfdbfe"/>',
        '<rect x="298" y="144" width="210" height="28" rx="14" fill="#fef2f2" stroke="#fecaca"/>',
        '<rect x="524" y="144" width="260" height="28" rx="14" fill="#f5f3ff" stroke="#ddd6fe"/>',
        _svg_text(177, 163, f'blue = coarse FFT ({study.coarse_fft})', size=14, anchor='middle', fill=COARSE_COLOR, weight='600'),
        _svg_text(403, 163, f'red = dense FFT ({study.fine_fft})', size=14, anchor='middle', fill=FINE_COLOR, weight='600'),
        _svg_text(654, 163, 'markers = β = 0, 8.6, 14 checkpoints', size=14, anchor='middle', fill=ERROR_COLOR, weight='600'),
    ]

    def draw_panel(
        left: float,
        top: float,
        title: str,
        subtitle: str,
        *,
        y_label: str,
        y_values: list[float],
        series_specs: list[tuple[list[float], str]],
        markers: bool = True,
    ) -> None:
        y_min = min(y_values)
        y_max = max(y_values)
        y_pad = max(0.08 * (y_max - y_min), 0.2)
        y_min -= y_pad
        y_max += y_pad
        plot_left = left + 64
        plot_right = left + panel_width - 36
        plot_top = top + 116
        plot_bottom = top + panel_height - 54

        def map_x(value: float) -> float:
            return plot_left + (value - x_min) / (x_max - x_min) * (plot_right - plot_left)

        def map_y(value: float) -> float:
            return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

        parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="18"/>')
        parts.append(_svg_text(left + 22, top + 32, title, size=20, weight='700'))
        parts.append(_svg_paragraph(left + 22, top + 58, subtitle, width=58, size=14))
        parts.append(_svg_text(plot_left, top + 102, y_label, size=13, fill='#6b7280', weight='600'))

        for step in range(5):
            frac = step / 4
            y_value = y_min + frac * (y_max - y_min)
            y = map_y(y_value)
            parts.append(_line(plot_left, y, plot_right, y, stroke='#e5e7eb', dash='4 6'))
            parts.append(_svg_text(plot_left - 10, y + 5, f'{y_value:.1f}', size=12, anchor='end', fill='#6b7280'))

        for step in range(8):
            frac = step / 7
            x_value = x_min + frac * (x_max - x_min)
            x = map_x(x_value)
            parts.append(_line(x, plot_top, x, plot_bottom, stroke='#eef1f5', dash='4 6'))
            parts.append(_svg_text(x, plot_bottom + 24, f'{x_value:.0f}', size=12, anchor='middle', fill='#6b7280'))

        parts.append(_line(plot_left, plot_top, plot_left, plot_bottom, stroke='#334155', width=2))
        parts.append(_line(plot_left, plot_bottom, plot_right, plot_bottom, stroke='#334155', width=2))

        for values, color in series_specs:
            points = [(map_x(row.beta), map_y(value)) for row, value in zip(study.rows, values)]
            parts.append(_polyline(points, stroke=color))

        if markers:
            for beta in HIGHLIGHT_BETAS:
                row = next(entry for entry in study.rows if abs(entry.beta - beta) < 1e-12)
                x = map_x(beta)
                y_positions: list[float] = []
                for values, color in series_specs:
                    y = map_y(values[study.rows.index(row)])
                    y_positions.append(y)
                    parts.append(_circle(x, y, 5.0, fill=color))
                label_y = min(y_positions) - 12
                parts.append(_svg_text(x, label_y, f'β={row.beta:.1f}', size=12, anchor='middle', fill='#111827', weight='700'))

        parts.append(_svg_text((plot_left + plot_right) / 2, plot_bottom + 46, 'Kaiser beta', size=14, anchor='middle', fill='#374151'))

    coarse_sidelobe = [row.coarse_peak_sidelobe_db for row in study.rows]
    fine_sidelobe = [row.fine_peak_sidelobe_db for row in study.rows]
    coarse_width = [row.coarse_main_lobe_width_bins for row in study.rows]
    fine_width = [row.fine_main_lobe_width_bins for row in study.rows]
    sidelobe_error = [row.peak_sidelobe_error_db for row in study.rows]
    width_error = [row.main_lobe_width_error_bins for row in study.rows]

    draw_panel(
        panel_left,
        panel_top,
        'Peak sidelobe level drifts under coarse zero padding',
        'The denser probe shows where the coarse spectrum grid flatters the higher-beta windows.',
        y_label='peak sidelobe level (dB)',
        y_values=coarse_sidelobe + fine_sidelobe,
        series_specs=[(coarse_sidelobe, COARSE_COLOR), (fine_sidelobe, FINE_COLOR)],
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top,
        'Main-lobe width drifts under coarse padding',
        'The same coarse probe also makes the higher-beta windows look wider than the denser read does.',
        y_label='null-to-null width (DFT bins)',
        y_values=coarse_width + fine_width,
        series_specs=[(coarse_width, COARSE_COLOR), (fine_width, FINE_COLOR)],
    )
    draw_panel(
        panel_left,
        panel_top + panel_height + panel_gap_y,
        'How much the sidelobe read is off',
        f'By β={summary.first_beta_with_one_db_error:.1f}, the coarse probe is already at least 1 dB off.',
        y_label='absolute sidelobe error (dB)',
        y_values=sidelobe_error,
        series_specs=[(sidelobe_error, ERROR_COLOR)],
    )
    draw_panel(
        panel_left + panel_width + panel_gap_x,
        panel_top + panel_height + panel_gap_y,
        'How much the width read is off',
        f'By β={summary.first_beta_with_half_bin_width_error:.1f}, the coarse probe is already at least half a bin too wide.',
        y_label='absolute width error (bins)',
        y_values=width_error,
        series_specs=[(width_error, WIDTH_ERROR_COLOR)],
    )

    parts.append(_svg_paragraph(
        88,
        1178,
        f'At β=8.6, the coarse {study.coarse_fft}-point probe makes the Kaiser window look {summary.beta_86_row.peak_sidelobe_error_db:.1f} dB cleaner and {summary.beta_86_row.main_lobe_width_error_bins:.2f} bins wider than the denser {study.fine_fft}-point read. By β={summary.worst_sidelobe_row.beta:.1f}, the coarse read is off by {summary.worst_sidelobe_row.peak_sidelobe_error_db:.1f} dB and {summary.worst_width_row.main_lobe_width_error_bins:.2f} bins. ENBW and scalloping do not move at all across this audit, which is the point: the window did not change, only the sampled spectral probe did.',
        width=178,
        size=14,
        fill='#4b5563',
    ))
    parts.append('</svg>')
    return '\n'.join(parts)


def render_kaiser_fft_density_report(study: KaiserFftDensityStudy) -> str:
    summary = summarize_kaiser_fft_density(study)
    low_beta = next(row for row in study.rows if abs(row.beta - 4.0) < 1e-12)
    worst_sidelobe = summary.worst_sidelobe_row
    worst_width = summary.worst_width_row
    beta_86 = summary.beta_86_row
    return '\n'.join([
        '# Kaiser sweep FFT-density audit',
        '',
        'The Kaiser sweep already made one good point: `beta` is a real design knob instead of a folklore label. This follow-up asks the next honest numerical question: **how much of that sweep is the window itself, and how much depends on how densely the spectrum is sampled?**',
        '',
        f'This pass keeps the same `{study.length}`-sample Kaiser family and compares a coarse `{study.coarse_fft}`-point spectral probe against a denser `{study.fine_fft}`-point probe.',
        '',
        '## Main read',
        '',
        f'- at `beta = {low_beta.beta:.1f}`, the coarse probe is already a little noisy but still close: `|Δ sidelobe| = {low_beta.peak_sidelobe_error_db:.2f} dB`, `|Δ width| = {low_beta.main_lobe_width_error_bins:.2f}` bins',
        f'- at the repo\'s named checkpoint `beta = {beta_86.beta:.1f}`, the coarse probe overstates the peak-sidelobe suppression by `{beta_86.peak_sidelobe_error_db:.2f} dB` and overstates the main-lobe width by `{beta_86.main_lobe_width_error_bins:.2f}` bins',
        f'- the worst sidelobe mismatch lands at `beta = {worst_sidelobe.beta:.1f}`: the coarse probe claims `{worst_sidelobe.coarse_peak_sidelobe_db:.2f} dB`, while the denser probe says `{worst_sidelobe.fine_peak_sidelobe_db:.2f} dB`',
        f'- the worst width mismatch also lands at `beta = {worst_width.beta:.1f}`: the coarse probe says `{worst_width.coarse_main_lobe_width_bins:.2f}` bins, while the denser probe says `{worst_width.fine_main_lobe_width_bins:.2f}` bins',
        '',
        '## Why this changes the repo',
        '',
        f'- the first `beta` with at least `1 dB` sidelobe error is `{summary.first_beta_with_one_db_error:.1f}`',
        f'- the first `beta` with at least `0.5` bin width error is `{summary.first_beta_with_half_bin_width_error:.1f}`',
        '- that means a coarse FFT grid can invent a fake high-`beta` windfall: the window can look cleaner and broader than the denser read really supports',
        '- ENBW and scalloping do **not** move across this audit because they are direct sums, not sampled-spectrum estimates',
        '- the right lesson is not that Kaiser changed its mind. The lesson is that some spectral metrics need enough zero padding before a plotted tradeoff is numerically honest',
        '',
        '## Caveat',
        '',
        f'This is still a bounded audit of one window length and two FFT sizes. It is enough to expose the measurement failure mode without claiming one universal minimum FFT ratio for every possible window family.',
        '',
        'Open `art/window-kaiser-fft-density-audit.png`, `art/window-kaiser-fft-density-audit.csv`, and `notebooks/kaiser_fft_density_audit.ipynb` together next.',
    ]) + '\n'


def write_kaiser_fft_density_csv(study: KaiserFftDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        fieldnames = [
            'beta',
            'coarse_fft',
            'fine_fft',
            'enbw_bins',
            'scalloping_loss_db',
            'coarse_peak_sidelobe_db',
            'fine_peak_sidelobe_db',
            'peak_sidelobe_delta_db',
            'peak_sidelobe_error_db',
            'coarse_main_lobe_width_bins',
            'fine_main_lobe_width_bins',
            'main_lobe_width_delta_bins',
            'main_lobe_width_error_bins',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in study.rows:
            writer.writerow(row.as_dict(coarse_fft=study.coarse_fft, fine_fft=study.fine_fft))
    return path


def write_kaiser_fft_density_notebook(study: KaiserFftDensityStudy, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_kaiser_fft_density(study)
    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Kaiser FFT-density audit\n',
                    '\n',
                    'This notebook is the slower companion to `notes/kaiser-fft-density-audit.md`.\n',
                    '\n',
                    'The bounded question is simple: **how much of the Kaiser sweep is the window family, and how much depends on FFT sampling density?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Hold the window family fixed and only change the spectral probe\n',
                    '\n',
                    'The window stays at length `129` and the family still runs across the same `beta` values. This pass only compares a coarse sampled spectrum against a denser one.\n',
                    '\n',
                    'That makes the interpretation clean: if the numbers move, the window did not change. The probe did.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from windowlab.kaiser_density import study_kaiser_fft_density\n',
                    '\n',
                    f'study = study_kaiser_fft_density(length={study.length}, coarse_fft={study.coarse_fft}, fine_fft={study.fine_fft})\n',
                    '[(row.beta, round(row.peak_sidelobe_error_db, 2), round(row.main_lobe_width_error_bins, 2)) for row in study.rows if row.peak_sidelobe_error_db >= 1.0]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. The figure\n',
                    '\n',
                    '![Kaiser FFT-density audit](../art/window-kaiser-fft-density-audit.png)\n',
                    '\n',
                    'Read it in two layers:\n',
                    '\n',
                    '1. the top row compares the coarse and dense measurements directly\n',
                    '2. the bottom row shows how the error grows with `beta` instead of staying flat across the family\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 3. What actually stays fixed\n',
                    '\n',
                    f'Even at `beta = 8.6`, the moving parts are only the sampled-spectrum metrics. The direct-sum metrics do not budge: ENBW stays `{summary.beta_86_row.enbw_bins:.3f}` bins and scalloping stays `{summary.beta_86_row.scalloping_loss_db:.3f} dB`.\n',
                    '\n',
                    'That is the useful split for the repo: some window metrics are inherently stable, while others need enough zero padding before a plotted comparison deserves trust.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Repeat the same audit on one second deep-sidelobe family only if it changes the read instead of just repeating the same drift.\n',
                    '2. Compare the dual-window path against one genuinely different desired-dual family only if it bends the noise-versus-flatness path instead of just landing between the same two endpoints.\n',
                    '3. Port the core metrics to Julia or Fortran only if the new language run stays reproducible and adds a real cross-check.\n',
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
