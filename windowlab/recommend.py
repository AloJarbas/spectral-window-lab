from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from windowlab.metrics import (
    coherent_gain_normalized_response,
    equivalent_noise_bandwidth_bins,
    null_to_null_main_lobe_width,
    peak_sidelobe_level_db,
    scalloping_loss_db,
)
from windowlab.overlap import squared_overlap_add_summary
from windowlab.windows import WINDOW_BUILDERS


DEFAULT_TASK_WINDOWS = (
    'rectangular',
    'hann',
    'hamming',
    'blackman',
    'kaiser-8.6',
    'blackman-harris',
    'nuttall-min4-bh',
    'nuttall-continuous',
    'flattop',
)


@dataclass(frozen=True)
class WindowTaskMetrics:
    name: str
    enbw_bins: float
    peak_sidelobe_db: float
    sidelobe_suppression_db: float
    main_lobe_width_bins: float
    scalloping_loss_db: float
    synthesis_gain_span_db: float
    far_tail_max_db: float
    far_tail_suppression_db: float


@dataclass(frozen=True)
class TaskProfile:
    key: str
    title: str
    short_label: str
    summary: str
    weights: dict[str, float]
    max_values: dict[str, float]
    min_values: dict[str, float]


@dataclass(frozen=True)
class TaskRanking:
    task_key: str
    task_title: str
    window: str
    eligible: bool
    rank: int
    score: float
    suitability: float
    enbw_bins: float
    peak_sidelobe_db: float
    main_lobe_width_bins: float
    scalloping_loss_db: float
    synthesis_gain_span_db: float
    far_tail_max_db: float
    far_tail_suppression_db: float


LOWER_IS_BETTER = {
    'enbw_bins',
    'main_lobe_width_bins',
    'scalloping_loss_db',
    'synthesis_gain_span_db',
}
HIGHER_IS_BETTER = {'sidelobe_suppression_db', 'far_tail_suppression_db'}

TASK_PROFILES: tuple[TaskProfile, ...] = (
    TaskProfile(
        key='close_tones',
        title='Separate very close equal-strength tones',
        short_label='close tones',
        summary='Only for the narrow case where main-lobe width matters more than far-out leakage.',
        weights={'main_lobe_width_bins': 0.70, 'enbw_bins': 0.20, 'sidelobe_suppression_db': 0.10},
        max_values={'main_lobe_width_bins': 4.2, 'enbw_bins': 1.6},
        min_values={},
    ),
    TaskProfile(
        key='compact_compromise',
        title='Compact low-sidelobe compromise',
        short_label='compact compromise',
        summary='A bounded default lane when you want cleaner sidelobes without paying the flat-top bill.',
        weights={'sidelobe_suppression_db': 0.45, 'enbw_bins': 0.20, 'main_lobe_width_bins': 0.20, 'scalloping_loss_db': 0.15},
        max_values={'main_lobe_width_bins': 6.5, 'enbw_bins': 1.9, 'scalloping_loss_db': 2.0},
        min_values={},
    ),
    TaskProfile(
        key='weak_near_strong',
        title='Hunt a weak spur beside a strong line',
        short_label='weak beside strong',
        summary='This lane pays for first-sidelobe suppression, but still caps width so the answer does not become absurdly wide.',
        weights={'sidelobe_suppression_db': 0.65, 'main_lobe_width_bins': 0.20, 'enbw_bins': 0.15},
        max_values={'main_lobe_width_bins': 8.5, 'enbw_bins': 2.2},
        min_values={},
    ),
    TaskProfile(
        key='weak_far_strong',
        title='Hunt a weak farther-out spur under a strong line',
        short_label='farther-out spur',
        summary='This follow-up lane shifts the scoring focus from the first sidelobe to the 24–48 bin tail, so the continuous Nuttall variant finally gets its own honest job.',
        weights={'far_tail_suppression_db': 0.72, 'sidelobe_suppression_db': 0.10, 'main_lobe_width_bins': 0.10, 'enbw_bins': 0.08},
        max_values={'main_lobe_width_bins': 8.5, 'enbw_bins': 2.2},
        min_values={'far_tail_suppression_db': 95.0},
    ),
    TaskProfile(
        key='amplitude',
        title='Measure isolated-tone amplitude honestly',
        short_label='amplitude honesty',
        summary='This is the lane where scalloping loss dominates and flat-top is allowed to win on purpose.',
        weights={'scalloping_loss_db': 0.80, 'enbw_bins': 0.15, 'main_lobe_width_bins': 0.05},
        max_values={'scalloping_loss_db': 1.2},
        min_values={},
    ),
    TaskProfile(
        key='stft_qhop',
        title='Quarter-hop STFT with calmer reconstruction',
        short_label='quarter-hop STFT',
        summary='This uses the repo\'s quarter-hop synthesis-normalization swing and refuses windows whose reconstruction bill is already loud.',
        weights={'synthesis_gain_span_db': 0.55, 'sidelobe_suppression_db': 0.20, 'enbw_bins': 0.15, 'main_lobe_width_bins': 0.10},
        max_values={'synthesis_gain_span_db': 0.30},
        min_values={'sidelobe_suppression_db': 30.0},
    ),
)


def _max_band_response_db(window: list[float], start: float, stop: float, *, steps: int = 880) -> float:
    import math

    values = []
    for idx in range(steps + 1):
        offset = start + (stop - start) * idx / steps
        response = coherent_gain_normalized_response(window, offset)
        values.append(20.0 * math.log10(max(response, 1e-12)))
    return max(values)


def build_task_metrics(
    *,
    length: int = 129,
    fft_size: int = 4096,
    overlap_length: int = 128,
    synthesis_hop: int = 32,
    names: Iterable[str] | None = None,
) -> list[WindowTaskMetrics]:
    selected_names = list(names) if names is not None else list(DEFAULT_TASK_WINDOWS)
    rows: list[WindowTaskMetrics] = []
    for name in selected_names:
        builder = WINDOW_BUILDERS[name]
        frequency_window = builder(length)
        overlap_window = builder(overlap_length)
        peak_sidelobe = peak_sidelobe_level_db(frequency_window, fft_size=fft_size)
        rows.append(
            WindowTaskMetrics(
                name=name,
                enbw_bins=equivalent_noise_bandwidth_bins(frequency_window),
                peak_sidelobe_db=peak_sidelobe,
                sidelobe_suppression_db=abs(peak_sidelobe),
                main_lobe_width_bins=length * null_to_null_main_lobe_width(frequency_window, fft_size=fft_size),
                scalloping_loss_db=abs(scalloping_loss_db(frequency_window)),
                synthesis_gain_span_db=squared_overlap_add_summary(overlap_window, synthesis_hop).ripple_db,
                far_tail_max_db=_max_band_response_db(frequency_window, 24.0, 48.0),
                far_tail_suppression_db=abs(_max_band_response_db(frequency_window, 24.0, 48.0)),
            )
        )
    return rows


def _eligible_for_task(row: WindowTaskMetrics, task: TaskProfile) -> bool:
    for metric_name, max_value in task.max_values.items():
        if getattr(row, metric_name) > max_value:
            return False
    for metric_name, min_value in task.min_values.items():
        if getattr(row, metric_name) < min_value:
            return False
    return True


def _normalized_cost(metric_name: str, value: float, rows: list[WindowTaskMetrics]) -> float:
    values = [getattr(row, metric_name) for row in rows]
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-12:
        return 0.0
    if metric_name in LOWER_IS_BETTER:
        return (value - lo) / (hi - lo)
    if metric_name in HIGHER_IS_BETTER:
        return (hi - value) / (hi - lo)
    raise ValueError(f'unknown metric direction: {metric_name}')


def rank_windows_for_task(rows: Iterable[WindowTaskMetrics], task: TaskProfile) -> list[TaskRanking]:
    metrics_rows = list(rows)
    eligible_rows = [row for row in metrics_rows if _eligible_for_task(row, task)]
    scoring_pool = eligible_rows if len(eligible_rows) >= 2 else metrics_rows

    scored: list[tuple[float, float, WindowTaskMetrics, bool]] = []
    for row in metrics_rows:
        eligible = row in eligible_rows if eligible_rows else True
        if not eligible:
            score = 10.0
        else:
            score = sum(
                weight * _normalized_cost(metric_name, getattr(row, metric_name), scoring_pool)
                for metric_name, weight in task.weights.items()
            )
        scored.append((score, -row.sidelobe_suppression_db, row, eligible))

    rankings: list[TaskRanking] = []
    for rank, (score_value, _, row, eligible) in enumerate(sorted(scored, key=lambda item: (item[0], item[1], item[2].name)), start=1):
        rankings.append(
            TaskRanking(
                task_key=task.key,
                task_title=task.title,
                window=row.name,
                eligible=eligible,
                rank=rank,
                score=round(score_value if eligible else 10.0, 6),
                suitability=round(0.0 if not eligible else max(0.0, 1.0 - score_value), 6),
                enbw_bins=row.enbw_bins,
                peak_sidelobe_db=row.peak_sidelobe_db,
                main_lobe_width_bins=row.main_lobe_width_bins,
                scalloping_loss_db=row.scalloping_loss_db,
                synthesis_gain_span_db=row.synthesis_gain_span_db,
                far_tail_max_db=row.far_tail_max_db,
                far_tail_suppression_db=row.far_tail_suppression_db,
            )
        )
    return rankings


def build_task_rankings(rows: Iterable[WindowTaskMetrics] | None = None) -> dict[str, list[TaskRanking]]:
    metrics_rows = list(rows) if rows is not None else build_task_metrics()
    return {task.key: rank_windows_for_task(metrics_rows, task) for task in TASK_PROFILES}


def top_pick_for_task(rows: Iterable[WindowTaskMetrics], task: TaskProfile) -> TaskRanking:
    rankings = rank_windows_for_task(rows, task)
    for ranking in rankings:
        if ranking.eligible:
            return ranking
    return rankings[0]
