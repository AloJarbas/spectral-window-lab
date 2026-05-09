from __future__ import annotations

from html import escape


PALETTE = {
    "rectangular": "#1f77b4",
    "hann": "#ff7f0e",
    "hamming": "#2ca02c",
    "blackman": "#d62728",
}


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#333", width: int = 1, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def _polyline(points: list[tuple[float, float]], *, stroke: str, width: int = 2) -> str:
    payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" points="{payload}"/>'


def _text(x: float, y: float, text: str, *, size: int = 16, anchor: str = "start", fill: str = "#222", weight: str = "normal") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">{escape(text)}</text>'


def chart_svg(title: str, x_label: str, y_label: str, series: dict[str, list[tuple[float, float]]], *, width: int = 1100, height: int = 680, y_range: tuple[float, float] = (0.0, 1.0), x_range: tuple[float, float] = (0.0, 1.0), background: str = "#fcfcfd") -> str:
    left = 90
    right = width - 40
    top = 70
    bottom = height - 90

    def map_x(value: float) -> float:
        lo, hi = x_range
        return left + (value - lo) / (hi - lo) * (right - left)

    def map_y(value: float) -> float:
        lo, hi = y_range
        return bottom - (value - lo) / (hi - lo) * (bottom - top)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        _text(width / 2, 38, title, size=28, anchor="middle", weight="700"),
        _line(left, top, left, bottom, width=2),
        _line(left, bottom, right, bottom, width=2),
    ]

    for step in range(6):
        frac = step / 5
        y_value = y_range[0] + frac * (y_range[1] - y_range[0])
        y = map_y(y_value)
        parts.append(_line(left, y, right, y, stroke="#d9dde3", dash="4 6"))
        parts.append(_text(left - 12, y + 5, f"{y_value:.2f}", size=13, anchor="end", fill="#4b5563"))

    for step in range(6):
        frac = step / 5
        x_value = x_range[0] + frac * (x_range[1] - x_range[0])
        x = map_x(x_value)
        parts.append(_line(x, top, x, bottom, stroke="#eef1f5", dash="4 6"))
        parts.append(_text(x, bottom + 28, f"{x_value:.2f}", size=13, anchor="middle", fill="#4b5563"))

    for name, points in series.items():
        mapped = [(map_x(x), map_y(y)) for x, y in points]
        parts.append(_polyline(mapped, stroke=PALETTE.get(name, "#111827"), width=3))

    legend_x = right - 180
    legend_y = top + 12
    for idx, name in enumerate(series):
        y = legend_y + idx * 26
        parts.append(_line(legend_x, y, legend_x + 24, y, stroke=PALETTE.get(name, "#111827"), width=4))
        parts.append(_text(legend_x + 32, y + 5, name, size=15, fill="#111827"))

    parts.append(_text((left + right) / 2, height - 28, x_label, size=16, anchor="middle", fill="#374151"))
    parts.append(_text(28, (top + bottom) / 2, y_label, size=16, anchor="middle", fill="#374151"))
    parts.append('</svg>')
    return "\n".join(parts)
