from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable

from .overlap import squared_overlap_add_profile


@dataclass(frozen=True)
class ReconstructionConditionSummary:
    hop: int
    mean_denominator: float
    min_denominator: float
    max_denominator: float
    min_denominator_fraction: float
    max_synthesis_gain: float
    mean_relative_noise_gain: float
    rms_relative_noise_gain: float
    worst_relative_noise_gain: float


@dataclass(frozen=True)
class ReconstructionRun:
    signal: list[float]
    reconstructed: list[float]
    denominator: list[float]
    rmse: float
    max_abs_error: float


def _as_list(window: Iterable[float]) -> list[float]:
    values = list(window)
    if not values:
        raise ValueError("window must not be empty")
    return values


def reconstruction_condition_summary(window: Iterable[float], hop: int) -> ReconstructionConditionSummary:
    profile = squared_overlap_add_profile(window, hop)
    mean_denominator = sum(profile) / len(profile)
    min_denominator = min(profile)
    max_denominator = max(profile)
    if mean_denominator <= 0.0:
        raise ValueError("mean squared overlap must stay positive")
    if min_denominator <= 0.0:
        raise ValueError("squared overlap profile must stay positive for normalized reconstruction")

    relative_noise_gains = [math.sqrt(mean_denominator / value) for value in profile]
    return ReconstructionConditionSummary(
        hop=hop,
        mean_denominator=mean_denominator,
        min_denominator=min_denominator,
        max_denominator=max_denominator,
        min_denominator_fraction=min_denominator / mean_denominator,
        max_synthesis_gain=mean_denominator / min_denominator,
        mean_relative_noise_gain=sum(relative_noise_gains) / len(relative_noise_gains),
        rms_relative_noise_gain=math.sqrt(sum(gain * gain for gain in relative_noise_gains) / len(relative_noise_gains)),
        worst_relative_noise_gain=max(relative_noise_gains),
    )


def relative_noise_gain_profile(window: Iterable[float], hop: int) -> list[tuple[float, float]]:
    summary = reconstruction_condition_summary(window, hop)
    profile = squared_overlap_add_profile(window, hop)
    if hop == 1:
        return [(0.0, math.sqrt(summary.mean_denominator / profile[0]))]
    return [
        (index / (hop - 1), math.sqrt(summary.mean_denominator / value))
        for index, value in enumerate(profile)
    ]


def build_reference_signal(length: int) -> list[float]:
    if length < 4:
        raise ValueError("length must be at least 4")
    signal: list[float] = []
    for index in range(length):
        t = index / length
        value = (
            0.58 * math.sin(2.0 * math.pi * 7.0 * t + 0.1)
            + 0.24 * math.sin(2.0 * math.pi * 19.0 * t - 0.3)
            + 0.12 * math.cos(2.0 * math.pi * 31.0 * t + 0.5)
            + 0.06 * math.sin(2.0 * math.pi * 3.0 * t * t)
        )
        signal.append(value)
    return signal


def periodic_same_window_reconstruction(
    signal: Iterable[float],
    window: Iterable[float],
    hop: int,
    *,
    coefficient_noise_std: float = 0.0,
    seed: int = 0,
) -> ReconstructionRun:
    samples = list(signal)
    if not samples:
        raise ValueError("signal must not be empty")
    if hop < 1:
        raise ValueError("hop must be positive")
    if len(samples) % hop != 0:
        raise ValueError("signal length must be a multiple of hop for periodic reconstruction")

    weights = _as_list(window)
    frame_length = len(weights)
    sample_count = len(samples)
    rng = random.Random(seed)

    numerator = [0.0] * sample_count
    denominator = [0.0] * sample_count

    for start in range(0, sample_count, hop):
        for offset, weight in enumerate(weights):
            index = (start + offset) % sample_count
            coefficient = samples[index] * weight
            if coefficient_noise_std:
                coefficient += rng.gauss(0.0, coefficient_noise_std)
            numerator[index] += coefficient * weight
            denominator[index] += weight * weight

    reconstructed: list[float] = []
    error_sq = 0.0
    max_abs_error = 0.0
    for expected, value, denom in zip(samples, numerator, denominator):
        if denom <= 0.0:
            raise ValueError("reconstruction denominator hit zero")
        actual = value / denom
        reconstructed.append(actual)
        error = actual - expected
        error_sq += error * error
        max_abs_error = max(max_abs_error, abs(error))

    rmse = math.sqrt(error_sq / sample_count)
    return ReconstructionRun(
        signal=samples,
        reconstructed=reconstructed,
        denominator=denominator,
        rmse=rmse,
        max_abs_error=max_abs_error,
    )


def simulated_relative_noise_gain(
    window: Iterable[float],
    hop: int,
    *,
    periods: int = 64,
    coefficient_noise_std: float = 1e-6,
    seed: int = 0,
    trials: int = 8,
) -> float:
    if coefficient_noise_std <= 0.0:
        raise ValueError("coefficient_noise_std must be positive")
    if trials < 1:
        raise ValueError("trials must be at least 1")
    weights = _as_list(window)
    length = periods * hop
    quiet_signal = [0.0] * length
    output_rms_values: list[float] = []
    for trial in range(trials):
        run = periodic_same_window_reconstruction(
            quiet_signal,
            weights,
            hop,
            coefficient_noise_std=coefficient_noise_std,
            seed=seed + trial * 7919,
        )
        output_rms_values.append(math.sqrt(sum(value * value for value in run.reconstructed) / len(run.reconstructed)))
    output_rms = sum(output_rms_values) / len(output_rms_values)
    summary = reconstruction_condition_summary(weights, hop)
    flat_case_rms = coefficient_noise_std / math.sqrt(summary.mean_denominator)
    return output_rms / flat_case_rms
