from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class OverlapAddSummary:
    hop: int
    mean_sum: float
    min_sum: float
    max_sum: float
    max_deviation_fraction: float
    ripple_db: float
    profile: list[float]


def periodic_overlap_add_profile(window: Iterable[float], hop: int) -> list[float]:
    values = list(window)
    if not values:
        raise ValueError("window must not be empty")
    if hop < 1 or hop > len(values):
        raise ValueError("hop must satisfy 1 <= hop <= len(window)")
    profile = [0.0] * hop
    for index, value in enumerate(values):
        profile[index % hop] += value
    return profile


def normalized_overlap_add_profile(window: Iterable[float], hop: int) -> list[tuple[float, float]]:
    profile = periodic_overlap_add_profile(window, hop)
    mean_value = sum(profile) / len(profile)
    if mean_value == 0.0:
        raise ValueError("overlap-add mean is zero")
    if hop == 1:
        return [(0.0, profile[0] / mean_value)]
    return [(index / (hop - 1), value / mean_value) for index, value in enumerate(profile)]


def overlap_add_summary(window: Iterable[float], hop: int) -> OverlapAddSummary:
    profile = periodic_overlap_add_profile(window, hop)
    mean_sum = sum(profile) / len(profile)
    min_sum = min(profile)
    max_sum = max(profile)
    if mean_sum == 0.0:
        raise ValueError("overlap-add mean is zero")
    max_deviation_fraction = max(abs(value - mean_sum) for value in profile) / mean_sum
    if min_sum <= 0.0:
        ripple_db = float("inf")
    else:
        ripple_db = 20.0 * math.log10(max_sum / min_sum)
    return OverlapAddSummary(
        hop=hop,
        mean_sum=mean_sum,
        min_sum=min_sum,
        max_sum=max_sum,
        max_deviation_fraction=max_deviation_fraction,
        ripple_db=ripple_db,
        profile=profile,
    )
