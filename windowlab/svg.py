from __future__ import annotations

from html import escape


PALETTE = {
    "rectangular": "#1f77b4",
    "hann": "#ff7f0e",
    "hamming": "#2ca02c",
    "blackman": "#d62728",
    "kaiser-8.6": "#9467bd",
    "blackman-harris": "#0f766e",
    "nuttall": "#b45309",
    "nuttall-min4-bh": "#b45309",
    "nuttall-continuous": "#7c3aed",
    "flattop": "#8b5cf6",
}

WINDOW_LABELS = {
    "rectangular": "Rectangular",
    "hann": "Hann",
    "hamming": "Hamming",
    "blackman": "Blackman",
    "kaiser-8.6": "Kaiser β=8.6",
    "blackman-harris": "Blackman-Harris",
    "nuttall": "Nuttall",
    "nuttall-min4-bh": "Nuttall min-4-term BH",
    "nuttall-continuous": "Nuttall continuous",
    "flattop": "Flat-top",
}


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#333", width: int = 1, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def _polyline(points: list[tuple[float, float]], *, stroke: str, width: int = 2) -> str:
    payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" points="{payload}"/>'


def _circle(x: float, y: float, radius: float, *, fill: str, stroke: str = "none", width: int = 1) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def _text(x: float, y: float, text: str, *, size: int = 16, anchor: str = "start", fill: str = "#222", weight: str = "normal") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">{escape(text)}</text>'


def _window_label(name: str) -> str:
    return WINDOW_LABELS.get(name, name)


def _estimate_text_width(text: str, size: int) -> float:
    return max(size * 0.58 * len(text), size * 0.9)


def _wrap_lines(text: str, max_width: float, size: int) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        proposal = f"{current} {word}"
        if _estimate_text_width(proposal, size) <= max_width:
            current = proposal
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _text_block(
    x: float,
    y: float,
    text: str,
    *,
    size: int,
    anchor: str = "start",
    fill: str = "#222",
    weight: str = "normal",
    max_width: float,
    line_gap: float = 1.25,
) -> tuple[str, float]:
    lines = _wrap_lines(text, max_width, size)
    tspans = []
    for idx, line in enumerate(lines):
        dy = 0 if idx == 0 else size * line_gap
        tspans.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}" text-anchor="{anchor}">{escape(line)}</tspan>')
    block = (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">' + "".join(tspans) + "</text>"
    )
    return block, len(lines) * size * line_gap


def _legend_rows(items: list[tuple[str, str, str | None]], max_width: float, *, size: int = 14) -> list[list[tuple[str, str, str | None]]]:
    rows: list[list[tuple[str, str, str | None]]] = []
    current: list[tuple[str, str, str | None]] = []
    current_width = 0.0
    for item in items:
        label = item[0]
        item_width = 26 + 10 + _estimate_text_width(label, size) + 28
        if current and current_width + item_width > max_width:
            rows.append(current)
            current = [item]
            current_width = item_width
        else:
            current.append(item)
            current_width += item_width
    if current:
        rows.append(current)
    return rows


def _legend_svg(rows: list[list[tuple[str, str, str | None]]], *, width: int, y: float, size: int = 14) -> tuple[list[str], float]:
    parts: list[str] = []
    row_gap = 22
    for row_idx, row in enumerate(rows):
        total_width = sum(26 + 10 + _estimate_text_width(label, size) + 28 for label, _, _ in row)
        x = (width - total_width) / 2
        baseline = y + row_idx * row_gap
        for label, stroke, dash in row:
            parts.append(_line(x, baseline, x + 24, baseline, stroke=stroke, width=4, dash=dash))
            parts.append(_text(x + 32, baseline + 5, label, size=size, fill="#111827"))
            x += 26 + 10 + _estimate_text_width(label, size) + 28
    return parts, len(rows) * row_gap


def chart_svg(
    title: str,
    x_label: str,
    y_label: str,
    series: dict[str, list[tuple[float, float]]],
    *,
    width: int = 1280,
    height: int = 780,
    y_range: tuple[float, float] = (0.0, 1.0),
    x_range: tuple[float, float] = (0.0, 1.0),
    background: str = "#fcfcfd",
) -> str:
    left = 116
    right = width - 44
    bottom = height - 110

    title_svg, title_height = _text_block(
        width / 2,
        42,
        title,
        size=28,
        anchor="middle",
        fill="#222",
        weight="700",
        max_width=width - 140,
    )

    legend_rows = _legend_rows([(name, PALETTE.get(name, "#111827"), None) for name in series], width - 140, size=15)
    legend_y = 42 + title_height + 10
    legend_svg, legend_height = _legend_svg(legend_rows, width=width, y=legend_y, size=15)
    top = legend_y + legend_height + 28

    def map_x(value: float) -> float:
        lo, hi = x_range
        return left + (value - lo) / (hi - lo) * (right - left)

    def map_y(value: float) -> float:
        lo, hi = y_range
        return bottom - (value - lo) / (hi - lo) * (bottom - top)

    clip_id = "chart-plot-clip"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs>',
        f'<clipPath id="{clip_id}"><rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" height="{bottom - top:.1f}" rx="12"/></clipPath>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        title_svg,
        *legend_svg,
        f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" height="{bottom - top:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="14"/>',
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
        parts.append(_text(x, bottom + 30, f"{x_value:.2f}", size=13, anchor="middle", fill="#4b5563"))

    parts.append(f'<g clip-path="url(#{clip_id})">')
    for name, points in series.items():
        mapped = [(map_x(x), map_y(y)) for x, y in points]
        parts.append(_polyline(mapped, stroke=PALETTE.get(name, "#111827"), width=3))
    parts.append('</g>')

    parts.append(_text((left + right) / 2, height - 34, x_label, size=16, anchor="middle", fill="#374151"))
    parts.append(
        f'<text x="36.0" y="{(top + bottom) / 2:.1f}" fill="#374151" font-size="16" font-family="Inter, Arial, sans-serif" '
        f'text-anchor="middle" transform="rotate(-90 36 {(top + bottom) / 2:.1f})">{escape(y_label)}</text>'
    )
    parts.append('</svg>')
    return "\n".join(parts)


def triptych_bar_svg(
    title: str,
    subtitle: str,
    panels: list[dict[str, object]],
    *,
    width: int = 1400,
    height: int = 720,
    background: str = "#fcfcfd",
) -> str:
    left = 70
    right = width - 50
    bottom = height - 102
    gap = 26
    panel_width = (right - left - gap * (len(panels) - 1)) / len(panels)

    title_svg, title_height = _text_block(
        width / 2,
        42,
        title,
        size=28,
        anchor="middle",
        fill="#222",
        weight="700",
        max_width=width - 150,
    )
    subtitle_svg, subtitle_height = _text_block(
        width / 2,
        42 + title_height,
        subtitle,
        size=16,
        anchor="middle",
        fill="#4b5563",
        max_width=width - 170,
    )

    legend_names: list[str] = list(panels[0]["values"].keys()) if panels else []
    legend_rows = _legend_rows([(name, PALETTE.get(name, "#111827"), None) for name in legend_names], width - 140)
    legend_y = 42 + title_height + subtitle_height + 8
    legend_svg, legend_height = _legend_svg(legend_rows, width=width, y=legend_y)
    top = legend_y + legend_height + 28

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        title_svg,
        subtitle_svg,
        *legend_svg,
    ]

    for panel_index, panel in enumerate(panels):
        panel_left = left + panel_index * (panel_width + gap)
        panel_right = panel_left + panel_width
        y_lo, y_hi = panel["y_range"]
        plot_top = top + 44

        def map_y(value: float) -> float:
            return bottom - (value - y_lo) / (y_hi - y_lo) * (bottom - plot_top)

        parts.append(f'<rect x="{panel_left:.1f}" y="{top:.1f}" width="{panel_width:.1f}" height="{bottom - top:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="14"/>')
        title_block, _ = _text_block(
            (panel_left + panel_right) / 2,
            top + 24,
            str(panel["title"]),
            size=17,
            anchor="middle",
            fill="#111827",
            weight="700",
            max_width=panel_width - 34,
        )
        parts.append(title_block)
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
            parts.append(_text(x + bar_width / 2, bottom + 24, name, size=12, anchor="middle", fill="#374151"))
            parts.append(_text(x + bar_width / 2, rect_y - 10, panel["value_format"].format(value), size=12, anchor="middle", fill="#111827", weight="700"))

        y_label_block, _ = _text_block(
            (panel_left + panel_right) / 2,
            bottom + 52,
            str(panel["y_label"]),
            size=13,
            anchor="middle",
            fill="#6b7280",
            max_width=panel_width - 40,
        )
        parts.append(y_label_block)

    parts.append('</svg>')
    return "\n".join(parts)


def stacked_line_panels_svg(
    title: str,
    subtitle: str,
    x_label: str,
    panels: list[dict[str, object]],
    *,
    width: int = 1400,
    height: int = 1020,
    background: str = "#fcfcfd",
) -> str:
    left = 96
    right = width - 44
    bottom = height - 118
    panel_gap = 38
    x_lo, x_hi = panels[0]["x_range"]

    def map_x(value: float) -> float:
        return left + (value - x_lo) / (x_hi - x_lo) * (right - left)

    title_svg, title_height = _text_block(
        width / 2,
        40,
        title,
        size=28,
        anchor="middle",
        fill="#222",
        weight="700",
        max_width=width - 150,
    )
    subtitle_svg, subtitle_height = _text_block(
        width / 2,
        40 + title_height,
        subtitle,
        size=16,
        anchor="middle",
        fill="#4b5563",
        max_width=width - 180,
    )

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

    legend_rows = _legend_rows(legend_items, width - 140)
    legend_y = 40 + title_height + subtitle_height + 8
    legend_svg, legend_height = _legend_svg(legend_rows, width=width, y=legend_y)
    top = legend_y + legend_height + 28
    panel_height = (bottom - top - panel_gap * (len(panels) - 1)) / len(panels)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs>',
    ]
    for panel_index in range(len(panels)):
        panel_top = top + panel_index * (panel_height + panel_gap)
        parts.append(
            f'<clipPath id="stacked-panel-{panel_index}"><rect x="{left + 20:.1f}" y="{panel_top + 40:.1f}" width="{right - left - 36:.1f}" height="{panel_height - 56:.1f}" rx="10"/></clipPath>'
        )
    parts.extend([
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        title_svg,
        subtitle_svg,
        *legend_svg,
    ])

    for panel_index, panel in enumerate(panels):
        panel_top = top + panel_index * (panel_height + panel_gap)
        panel_bottom = panel_top + panel_height
        y_lo, y_hi = panel["y_range"]

        def map_y(value: float) -> float:
            return panel_bottom - 16 - (value - y_lo) / (y_hi - y_lo) * (panel_height - 56)

        parts.append(f'<rect x="{left:.1f}" y="{panel_top:.1f}" width="{right - left:.1f}" height="{panel_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="14"/>')
        title_block, _ = _text_block(
            left + 18,
            panel_top + 28,
            str(panel["title"]),
            size=17,
            fill="#111827",
            weight="700",
            max_width=right - left - 220,
        )
        parts.append(title_block)
        parts.append(_text(right - 10, panel_top + 28, str(panel["y_label"]), size=13, anchor="end", fill="#6b7280"))

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
            parts.append(_text(x, panel_bottom + 22, str(panel["x_tick_format"]).format(x_value), size=12, anchor="middle", fill="#6b7280"))

        parts.append(f'<g clip-path="url(#stacked-panel-{panel_index})">')
        for ref in panel.get("references", []):
            y = map_y(float(ref["value"]))
            parts.append(_line(left + 20, y, right - 16, y, stroke=str(ref["stroke"]), width=2, dash=str(ref.get("dash", "6 6"))))
        for series in panel.get("series", []):
            mapped = [(map_x(x), map_y(y)) for x, y in series["points"]]
            parts.append(_polyline(mapped, stroke=str(series["stroke"]), width=int(series.get("width", 3))))
        for marker in panel.get("markers", []):
            x = map_x(float(marker["x"]))
            y = map_y(float(marker["y"]))
            parts.append(_circle(x, y, 5.0, fill=str(marker.get("fill", "#ffffff")), stroke=str(marker.get("stroke", "#111827")), width=2))
        parts.append('</g>')

        for ref in panel.get("references", []):
            y = map_y(float(ref["value"]))
            parts.append(_text(right - 22, y - 6, str(ref["label"]), size=12, anchor="end", fill=str(ref["stroke"]), weight="700"))
        for marker in panel.get("markers", []):
            x = map_x(float(marker["x"]))
            y = map_y(float(marker["y"]))
            parts.append(_text(x, y - 10, str(marker["label"]), size=12, anchor="middle", fill="#111827", weight="700"))

    parts.append(_text((left + right) / 2, height - 32, x_label, size=16, anchor="middle", fill="#374151"))
    parts.append('</svg>')
    return "\n".join(parts)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in rgb)


def _blend_hex(start: str, end: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    a = _hex_to_rgb(start)
    b = _hex_to_rgb(end)
    mixed = tuple(int(round(a[idx] + (b[idx] - a[idx]) * t)) for idx in range(3))
    return _rgb_to_hex(mixed)


def task_heatmap_svg(
    title: str,
    subtitle: str,
    windows: list[str],
    tasks: list[dict[str, str]],
    rankings_by_task: dict[str, list[dict[str, object]]],
    *,
    width: int = 2040,
    height: int = 1120,
    background: str = "#fcfcfd",
) -> str:
    left = 300
    top = 170
    cell_width = 252
    cell_height = 70
    grid_width = cell_width * len(tasks)
    grid_height = cell_height * len(windows)

    title_svg, title_height = _text_block(
        width / 2,
        42,
        title,
        size=28,
        anchor="middle",
        fill="#222",
        weight="700",
        max_width=width - 520,
    )
    subtitle_svg, subtitle_height = _text_block(
        width / 2,
        42 + title_height,
        subtitle,
        size=16,
        anchor="middle",
        fill="#4b5563",
        max_width=width - 560,
    )
    top = 42 + title_height + subtitle_height + 42

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        title_svg,
        subtitle_svg,
    ]

    legend_left = left
    legend_top = top - 42
    for idx in range(11):
        x = legend_left + idx * 34
        fill = _blend_hex("#f3f4f6", "#1d4ed8", idx / 10)
        parts.append(f'<rect x="{x:.1f}" y="{legend_top:.1f}" width="34" height="14" fill="{fill}" rx="4"/>')
    parts.append(_text(legend_left, legend_top - 8, "lighter = worse fit, darker = stronger fit", size=12, fill="#6b7280"))
    parts.append(_text(legend_left + 380, legend_top + 12, "gray = outside this task's guardrails", size=12, fill="#6b7280"))

    parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{grid_width:.1f}" height="{grid_height:.1f}" fill="#ffffff" stroke="#e5e7eb" rx="16"/>')

    for row_idx, window in enumerate(windows):
        y = top + row_idx * cell_height
        if row_idx:
            parts.append(_line(left, y, left + grid_width, y, stroke="#e5e7eb", width=1))
        parts.append(_text(left - 16, y + cell_height / 2 + 6, _window_label(window), size=16, anchor="end", fill="#111827", weight="700" if window in {"rectangular", "kaiser-8.6", "nuttall", "nuttall-min4-bh", "nuttall-continuous", "flattop", "hamming"} else "normal"))

    for column_idx, task in enumerate(tasks):
        x = left + column_idx * cell_width
        if column_idx:
            parts.append(_line(x, top, x, top + grid_height, stroke="#e5e7eb", width=1))
        title_block, _ = _text_block(
            x + cell_width / 2,
            top - 14,
            task["title"],
            size=14,
            anchor="middle",
            fill="#111827",
            weight="700",
            max_width=cell_width - 24,
        )
        parts.append(title_block)

        by_window = {str(row["window"]): row for row in rankings_by_task[task["key"]]}
        for row_idx, window in enumerate(windows):
            row = by_window[window]
            y = top + row_idx * cell_height
            eligible = bool(row["eligible"])
            suitability = float(row["suitability"])
            fill = "#e5e7eb" if not eligible else _blend_hex("#eef2ff", "#1d4ed8", suitability)
            text_fill = "#374151" if not eligible or suitability < 0.58 else "#ffffff"
            parts.append(
                f'<rect x="{x + 6:.1f}" y="{y + 6:.1f}" width="{cell_width - 12:.1f}" height="{cell_height - 12:.1f}" fill="{fill}" rx="10"/>'
            )
            rank_text = f'#{int(row["rank"])}' if eligible else 'out'
            parts.append(_text(x + 20, y + 37, rank_text, size=17, fill=text_fill, weight="700"))
            parts.append(_text(x + cell_width - 18, y + 34, f'{int(round(suitability * 100.0)):d}', size=15, anchor="end", fill=text_fill, weight="700" if eligible else "normal"))
            parts.append(_text(x + cell_width - 18, y + 54, 'fit', size=12, anchor="end", fill=text_fill))
            if int(row["rank"]) == 1 and eligible:
                parts.append(f'<rect x="{x + cell_width - 58:.1f}" y="{y + 10:.1f}" width="38" height="16" rx="8" fill="#111827" opacity="0.92"/>')
                parts.append(_text(x + cell_width - 39, y + 22, "pick", size=10, anchor="middle", fill="#ffffff", weight="700"))

    winners_top = top + grid_height + 72
    card_gap = 16
    card_width = (grid_width - card_gap * (len(tasks) - 1)) / len(tasks)
    parts.append(_text(left, winners_top - 18, "Top pick per task", size=15, fill="#111827", weight="700"))
    for idx, task in enumerate(tasks):
        x = left + idx * (card_width + card_gap)
        winner = next(row for row in rankings_by_task[task["key"]] if bool(row["eligible"]))
        summary_block, _ = _text_block(
            x + 16,
            winners_top + 62,
            task["summary"],
            size=12,
            fill="#4b5563",
            max_width=card_width - 32,
        )
        parts.append(f'<rect x="{x:.1f}" y="{winners_top:.1f}" width="{card_width:.1f}" height="148" fill="#ffffff" stroke="#dbe2ea" rx="14"/>')
        parts.append(_text(x + 16, winners_top + 24, task["short_label"], size=12, fill="#6b7280", weight="700"))
        parts.append(_text(x + 16, winners_top + 48, _window_label(str(winner["window"])), size=18, fill="#111827", weight="700"))
        parts.append(summary_block)

    footer_block, _ = _text_block(
        left,
        height - 42,
        "Task map uses this repo's existing frequency metrics at length 129 and quarter-hop synthesis-gain swing for the STFT lane. It is a bounded decision card, not a universal best-window law.",
        size=13,
        fill="#6b7280",
        max_width=grid_width,
    )
    parts.append(footer_block)
    parts.append('</svg>')
    return "\n".join(parts)
