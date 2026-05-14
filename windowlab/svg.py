from __future__ import annotations

from html import escape


PALETTE = {
    "rectangular": "#1f77b4",
    "hann": "#ff7f0e",
    "hamming": "#2ca02c",
    "blackman": "#d62728",
    "kaiser-8.6": "#9467bd",
    "flattop": "#8b5cf6",
}


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#333", width: int = 1, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def _polyline(points: list[tuple[float, float]], *, stroke: str, width: int = 2) -> str:
    payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" points="{payload}"/>'


def _circle(x: float, y: float, radius: float, *, fill: str, stroke: str = "none", width: int = 1) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


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


def triptych_bar_svg(
    title: str,
    subtitle: str,
    panels: list[dict[str, object]],
    *,
    width: int = 1200,
    height: int = 580,
    background: str = "#fcfcfd",
) -> str:
    left = 60
    right = width - 40
    top = 120
    bottom = height - 80
    gap = 26
    panel_width = (right - left - gap * (len(panels) - 1)) / len(panels)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _text(width / 2, 72, subtitle, size=16, anchor="middle", fill="#4b5563"),
    ]

    legend_x = left
    legend_y = 98
    legend_names: list[str] = list(panels[0]["values"].keys()) if panels else []
    for idx, name in enumerate(legend_names):
        x = legend_x + idx * 140
        parts.append(_line(x, legend_y, x + 24, legend_y, stroke=PALETTE.get(name, "#111827"), width=4))
        parts.append(_text(x + 32, legend_y + 5, name, size=14, fill="#111827"))

    for panel_index, panel in enumerate(panels):
        panel_left = left + panel_index * (panel_width + gap)
        panel_right = panel_left + panel_width
        y_lo, y_hi = panel["y_range"]

        def map_y(value: float) -> float:
            return bottom - (value - y_lo) / (y_hi - y_lo) * (bottom - top)

        parts.append(f'<rect x="{panel_left:.1f}" y="{top:.1f}" width="{panel_width:.1f}" height="{bottom - top:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="14"/>')
        parts.append(_text((panel_left + panel_right) / 2, top - 18, str(panel["title"]), size=17, anchor="middle", weight="700"))
        values: dict[str, float] = panel["values"]
        bar_gap = 16.0
        usable_width = panel_width - 54.0
        bar_width = (usable_width - bar_gap * (len(values) - 1)) / len(values)
        base_y = map_y(0.0 if y_lo <= 0.0 <= y_hi else y_lo)

        for step in range(5):
            frac = step / 4
            y_value = y_lo + frac * (y_hi - y_lo)
            y = map_y(y_value)
            parts.append(_line(panel_left + 20, y, panel_right - 16, y, stroke="#e5e7eb", dash="4 6"))
            parts.append(_text(panel_left + 16, y + 5, panel["tick_format"].format(y_value), size=12, anchor="end", fill="#6b7280"))

        for idx, (name, value) in enumerate(values.items()):
            x = panel_left + 30 + idx * (bar_width + bar_gap)
            y = map_y(value)
            height_px = abs(base_y - y)
            rect_y = min(base_y, y)
            parts.append(
                f'<rect x="{x:.1f}" y="{rect_y:.1f}" width="{bar_width:.1f}" height="{max(height_px, 1.5):.1f}" fill="{PALETTE.get(name, "#111827")}" rx="8"/>'
            )
            parts.append(_text(x + bar_width / 2, bottom + 22, name, size=12, anchor="middle", fill="#374151"))
            parts.append(_text(x + bar_width / 2, rect_y - 8, panel["value_format"].format(value), size=12, anchor="middle", fill="#111827", weight="700"))

        parts.append(_text((panel_left + panel_right) / 2, bottom + 48, str(panel["y_label"]), size=13, anchor="middle", fill="#6b7280"))

    parts.append('</svg>')
    return "\n".join(parts)


def stacked_line_panels_svg(
    title: str,
    subtitle: str,
    x_label: str,
    panels: list[dict[str, object]],
    *,
    width: int = 1200,
    height: int = 860,
    background: str = "#fcfcfd",
) -> str:
    left = 90
    right = width - 40
    top = 110
    bottom = height - 90
    panel_gap = 34
    panel_height = (bottom - top - panel_gap * (len(panels) - 1)) / len(panels)
    x_lo, x_hi = panels[0]["x_range"]

    def map_x(value: float) -> float:
        return left + (value - x_lo) / (x_hi - x_lo) * (right - left)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        _text(width / 2, 40, title, size=28, anchor="middle", weight="700"),
        _text(width / 2, 70, subtitle, size=16, anchor="middle", fill="#4b5563"),
    ]

    legend_x = left
    legend_y = 92
    legend_items: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for panel in panels:
        for series in panel.get("series", []):
            item = (str(series["name"]), str(series["stroke"]), None)
            if item not in seen:
                legend_items.append(item)
                seen.add(item)
        for ref in panel.get("references", []):
            item = (str(ref["label"]), str(ref["stroke"]), str(ref.get("dash")))
            if item not in seen:
                legend_items.append(item)
                seen.add(item)

    for idx, (label, stroke, dash) in enumerate(legend_items):
        x = legend_x + idx * 170
        parts.append(_line(x, legend_y, x + 24, legend_y, stroke=stroke, width=4, dash=dash))
        parts.append(_text(x + 32, legend_y + 5, label, size=14, fill="#111827"))

    for panel_index, panel in enumerate(panels):
        panel_top = top + panel_index * (panel_height + panel_gap)
        panel_bottom = panel_top + panel_height
        y_lo, y_hi = panel["y_range"]

        def map_y(value: float) -> float:
            return panel_bottom - (value - y_lo) / (y_hi - y_lo) * (panel_height - 24)

        parts.append(f'<rect x="{left:.1f}" y="{panel_top:.1f}" width="{right - left:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="14"/>')
        parts.append(_text(left + 18, panel_top + 28, str(panel["title"]), size=17, weight="700"))
        parts.append(_text(right - 8, panel_top + 28, str(panel["y_label"]), size=13, anchor="end", fill="#6b7280"))

        for step in range(5):
            frac = step / 4
            y_value = y_lo + frac * (y_hi - y_lo)
            y = map_y(y_value)
            parts.append(_line(left + 20, y, right - 16, y, stroke="#e5e7eb", dash="4 6"))
            parts.append(_text(left + 16, y + 5, str(panel["tick_format"]).format(y_value), size=12, anchor="end", fill="#6b7280"))

        for step in range(8):
            frac = step / 7
            x_value = x_lo + frac * (x_hi - x_lo)
            x = map_x(x_value)
            parts.append(_line(x, panel_top + 40, x, panel_bottom - 16, stroke="#eef1f5", dash="4 6"))
            parts.append(_text(x, panel_bottom + 20, str(panel["x_tick_format"]).format(x_value), size=12, anchor="middle", fill="#6b7280"))

        for ref in panel.get("references", []):
            y = map_y(float(ref["value"]))
            parts.append(_line(left + 20, y, right - 16, y, stroke=str(ref["stroke"]), width=2, dash=str(ref.get("dash", "6 6"))))
            parts.append(_text(right - 22, y - 6, str(ref["label"]), size=12, anchor="end", fill=str(ref["stroke"]), weight="700"))

        for series in panel.get("series", []):
            mapped = [(map_x(x), map_y(y)) for x, y in series["points"]]
            parts.append(_polyline(mapped, stroke=str(series["stroke"]), width=int(series.get("width", 3))))

        for marker in panel.get("markers", []):
            x = map_x(float(marker["x"]))
            y = map_y(float(marker["y"]))
            parts.append(_circle(x, y, 5.0, fill=str(marker.get("fill", "#ffffff")), stroke=str(marker.get("stroke", "#111827")), width=2))
            parts.append(_text(x, y - 10, str(marker["label"]), size=12, anchor="middle", fill="#111827", weight="700"))

    parts.append(_text((left + right) / 2, height - 24, x_label, size=16, anchor="middle", fill="#374151"))
    parts.append('</svg>')
    return "\n".join(parts)
