from __future__ import annotations

import math
from typing import Callable


WindowBuilder = Callable[[int], list[float]]


KAISER_BETA_86 = 8.6
BLACKMAN_HARRIS_COEFFICIENTS = (
    0.35875,
    0.48829,
    0.14128,
    0.01168,
)
NUTTALL_MIN4_BH_COEFFICIENTS = (
    0.3635819,
    0.4891775,
    0.1365995,
    0.0106411,
)
NUTTALL_CONTINUOUS_COEFFICIENTS = (
    0.355768,
    0.487396,
    0.144232,
    0.012604,
)
FLATTOP_COEFFICIENTS = (
    0.21557895,
    0.41663158,
    0.277263158,
    0.083578947,
    0.006947368,
)


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


def _generalized_cosine(length: int, coefficients: tuple[float, ...]) -> list[float]:
    _check_length(length)
    scale = 2.0 * math.pi / (length - 1)
    values: list[float] = []
    for n in range(length):
        total = 0.0
        for index, coefficient in enumerate(coefficients):
            sign = -1.0 if index % 2 else 1.0
            total += sign * coefficient * math.cos(index * scale * n)
        values.append(total)
    return values


def rectangular(length: int) -> list[float]:
    _check_length(length)
    return [1.0] * length


def hann(length: int) -> list[float]:
    return _generalized_cosine(length, (0.5, 0.5))


def hamming(length: int) -> list[float]:
    return _generalized_cosine(length, (0.54, 0.46))


def blackman(length: int) -> list[float]:
    return _generalized_cosine(length, (0.42, 0.5, 0.08))


def blackman_harris(length: int) -> list[float]:
    return _generalized_cosine(length, BLACKMAN_HARRIS_COEFFICIENTS)


def nuttall_min4_bh(length: int) -> list[float]:
    return _generalized_cosine(length, NUTTALL_MIN4_BH_COEFFICIENTS)


def nuttall_continuous(length: int) -> list[float]:
    return _generalized_cosine(length, NUTTALL_CONTINUOUS_COEFFICIENTS)


def nuttall(length: int) -> list[float]:
    return nuttall_min4_bh(length)


def flattop(length: int) -> list[float]:
    return _generalized_cosine(length, FLATTOP_COEFFICIENTS)


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
    "blackman-harris": blackman_harris,
    "nuttall": nuttall,
    "nuttall-min4-bh": nuttall_min4_bh,
    "nuttall-continuous": nuttall_continuous,
    "flattop": flattop,
}


def available_windows() -> list[str]:
    return list(WINDOW_BUILDERS)


def build_window(name: str, length: int) -> list[float]:
    try:
        builder = WINDOW_BUILDERS[name]
    except KeyError as exc:
        raise ValueError(f"unknown window: {name}") from exc
    return builder(length)
