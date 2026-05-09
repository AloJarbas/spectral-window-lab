from __future__ import annotations

import math
from typing import Callable


WindowBuilder = Callable[[int], list[float]]


def _check_length(length: int) -> None:
    if length < 2:
        raise ValueError("window length must be at least 2")


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


WINDOW_BUILDERS: dict[str, WindowBuilder] = {
    "rectangular": rectangular,
    "hann": hann,
    "hamming": hamming,
    "blackman": blackman,
}


def available_windows() -> list[str]:
    return list(WINDOW_BUILDERS)


def build_window(name: str, length: int) -> list[float]:
    try:
        builder = WINDOW_BUILDERS[name]
    except KeyError as exc:
        raise ValueError(f"unknown window: {name}") from exc
    return builder(length)
