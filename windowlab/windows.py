from __future__ import annotations

import math
from typing import Callable


WindowBuilder = Callable[[int], list[float]]


KAISER_BETA_86 = 8.6


def _check_length(length: int) -> None:
    if length < 2:
        raise ValueError("window length must be at least 2")


def _i0(value: float) -> float:
    total = 1.0
    term = 1.0
    k = 1
    half_sq = (value * value) / 4.0
    while True:
        term *= half_sq / (k * k)
        total += term
        if term < 1e-15 * total:
            return total
        k += 1


def rectangular(length: int) -> list[float]:
    _check_length(length)
    return [1.0] * length


def hann(length: int) -> list[float]:
    _check_length(length)
    scale = 2.0 * math.pi / (length - 1)
    return [0.5 - 0.5 * math.cos(scale * n) for n in range(length)]


def hamming(length: int) -> list[float]:
    _check_length(length)
    scale = 2.0 * math.pi / (length - 1)
    return [0.54 - 0.46 * math.cos(scale * n) for n in range(length)]


def blackman(length: int) -> list[float]:
    _check_length(length)
    scale = 2.0 * math.pi / (length - 1)
    return [
        0.42 - 0.5 * math.cos(scale * n) + 0.08 * math.cos(2.0 * scale * n)
        for n in range(length)
    ]


def kaiser(length: int, beta: float) -> list[float]:
    _check_length(length)
    if beta < 0.0:
        raise ValueError("beta must be non-negative")
    denom = _i0(beta)
    center_scale = 2.0 / (length - 1)
    return [
        _i0(beta * math.sqrt(max(0.0, 1.0 - (center_scale * n - 1.0) ** 2))) / denom
        for n in range(length)
    ]


def kaiser_86(length: int) -> list[float]:
    return kaiser(length, KAISER_BETA_86)


WINDOW_BUILDERS: dict[str, WindowBuilder] = {
    "rectangular": rectangular,
    "hann": hann,
    "hamming": hamming,
    "blackman": blackman,
    "kaiser-8.6": kaiser_86,
}


def available_windows() -> list[str]:
    return list(WINDOW_BUILDERS)


def build_window(name: str, length: int) -> list[float]:
    try:
        builder = WINDOW_BUILDERS[name]
    except KeyError as exc:
        raise ValueError(f"unknown window: {name}") from exc
    return builder(length)
