from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from i18n import DEFAULT_LANG, TRANSLATIONS


WIDTH = 1080
HEIGHT = 1920
ICON_SIZE = 24
ICON_GAP = 8

ICONS_DIR = Path(__file__).resolve().parent / "icons"


THEMES = {
    "forest": {
        "bg_top": "#052425",
        "bg_bottom": "#011717",
        "panel": "#032024",
        "border": "#345b50",
        "text": "#e8f2cc",
        "muted": "#a4b98e",
        "accent": "#c8dc73",
        "up": "#9dd66b",
        "down": "#f08065",
        "warning": "#ffb300",
        "neutral": "#6f7e6e",
        "cold": "#7bb9df",
    },
    "volcanic": {
        "bg_top": "#2a0f0b",
        "bg_bottom": "#170705",
        "panel": "#2a130f",
        "border": "#8f3a2f",
        "text": "#ffe9de",
        "muted": "#d4ab9d",
        "accent": "#ff8b61",
        "up": "#ffb057",
        "down": "#f08065",
        "warning": "#ffd166",
        "neutral": "#6c4a40",
        "cold": "#85c2ff",
    },
    "alpine": {
        "bg_top": "#132532",
        "bg_bottom": "#0a1822",
        "panel": "#112633",
        "border": "#2f6582",
        "text": "#e5f5ff",
        "muted": "#99bccf",
        "accent": "#8bddff",
        "up": "#8be15f",
        "down": "#ff6c57",
        "warning": "#ffd166",
        "neutral": "#4b6472",
        "cold": "#74afff",
    }
}


def _font(size: int, bold: bool = False):
    candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient_background(width: int, height: int, top: str, bottom: str) -> Image.Image:
    img = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(img)

    t_r, t_g, t_b = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    b_r, b_g, b_b = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))

    for y in range(height):
        p = y / max(height - 1, 1)
        color = (
            int(t_r + (b_r - t_r) * p),
            int(t_g + (b_g - t_g) * p),
            int(t_b + (b_b - t_b) * p),
        )
        draw.line([(0, y), (width, y)], fill=color)

    return img


def _panel(
    draw: ImageDraw.ImageDraw,
    rect,
    fill: str,
    border: str,
    radius: int = 18,
    border_w: int = 2,
):
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=border, width=border_w)


def _fmt_km(v: float, labels: dict | None = None) -> str:
    if labels is None:
        labels = TRANSLATIONS[DEFAULT_LANG]
    return f"{v:.1f} {labels['unit_km']}"


def _fmt_speed(v: float | None, labels: dict | None = None) -> str:
    if labels is None:
        labels = TRANSLATIONS[DEFAULT_LANG]
    return labels["not_available"] if v is None else f"{v:.1f} {labels['unit_kmh']}"


def _fmt_time(v: str | None, labels: dict | None = None) -> str:
    if labels is None:
        labels = TRANSLATIONS[DEFAULT_LANG]
    return labels["not_available"] if v is None else v


def _fmt_m(v: float, labels: dict | None = None) -> str:
    if labels is None:
        labels = TRANSLATIONS[DEFAULT_LANG]
    return f"{int(round(v))} {labels['unit_m']}"


def _load_i18n(lang: str) -> dict:
    code = "es" if (lang or "").lower().startswith("es") else "en"
    return TRANSLATIONS[code]


def _t(labels: dict, key: str) -> str:
    return labels[key]


def _route_date_label(metadata, lang: str) -> str:
    route_time = metadata.get("time")
    if not isinstance(route_time, datetime):
        return ""
    labels = _load_i18n(lang)
    weekdays = (
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    )
    months = (
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    )
    weekday = _t(labels, f"weekday_{weekdays[route_time.weekday()]}")
    month = _t(labels, f"month_{months[route_time.month - 1]}")
    if lang.lower().startswith("es"):
        weekday = weekday.capitalize()
    return _t(labels, "date_format").format(
        weekday=weekday,
        day=route_time.day,
        month=month,
        year=route_time.year,
    )


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_xy,
    font,
    fill,
):
    tw, th = _text_size(draw, text, font)
    draw.text((center_xy[0] - tw / 2, center_xy[1] - th / 2), text, font=font, fill=fill)


def _fit_font_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    start_size: int,
    min_size: int,
    bold: bool = True,
):
    for size in range(start_size, min_size - 1, -1):
        font = _font(size, bold=bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return _font(min_size, bold=bold)


def _load_required_icons() -> dict:
    icon_paths = {
        "ascent": ICONS_DIR / "ascent_24x24.png",
        "ascent_analysis": ICONS_DIR / "ascent_analysis_24x24.png",
        "descent": ICONS_DIR / "descent_24x24.png",
        "descent_analysis": ICONS_DIR / "descent_analysis_24x24.png",
        "extreme": ICONS_DIR / "extreme_24x24.png",
        "finish": ICONS_DIR / "finish_24x24.png",
        "flat_sections": ICONS_DIR / "flat_sections_24x24.png",
        "general": ICONS_DIR / "general_24x24.png",
        "negative_progression": ICONS_DIR / "negative_progression_24x24.png",
        "positive_progression": ICONS_DIR / "positive_progression_24x24.png",
        "progression": ICONS_DIR / "progression_24x24.png",
        "speed": ICONS_DIR / "speed_24x24.png",
        "start": ICONS_DIR / "start_24x24.png",
        "total_distance": ICONS_DIR / "total_distance_24x24.png",
        "total_time": ICONS_DIR / "total_time_24x24.png",
    }

    loaded = {}
    for key, path in icon_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Required icon not found: {path}")
        icon = Image.open(path).convert("RGBA")
        if icon.size != (ICON_SIZE, ICON_SIZE):
            icon = icon.resize((ICON_SIZE, ICON_SIZE))
        loaded[key] = icon
    return loaded


def _draw_icon_title(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    icon: Image.Image,
    text: str,
    x: int,
    y: int,
    fill: str,
    max_width: int,
    start_size: int,
    min_size: int,
    bold: bool = True,
):
    text_max_width = max(20, max_width - ICON_SIZE - ICON_GAP)
    font = _fit_font_for_width(
        draw,
        text,
        max_width=text_max_width,
        start_size=start_size,
        min_size=min_size,
        bold=bold,
    )
    _, text_h = _text_size(draw, text, font)
    icon_y = int(y + max(0, (text_h - ICON_SIZE) / 2))
    img.paste(icon, (x, icon_y), icon)
    draw.text((x + ICON_SIZE + ICON_GAP, y), text, fill=fill, font=font)


def _hex_to_rgb(value: str):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _rgb_to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _interpolate_hex(start_hex: str, end_hex: str, t: float) -> str:
    sr, sg, sb = _hex_to_rgb(start_hex)
    er, eg, eb = _hex_to_rgb(end_hex)
    return _rgb_to_hex(
        (
            int(sr + (er - sr) * t),
            int(sg + (eg - sg) * t),
            int(sb + (eb - sb) * t),
        )
    )


def _gradient_steps(start_hex: str, end_hex: str, count: int) -> list[str]:
    if count <= 1:
        return [start_hex]
    return [
        _interpolate_hex(start_hex, end_hex, idx / (count - 1))
        for idx in range(count)
    ]


def _draw_slope_table(
    draw: ImageDraw.ImageDraw,
    rect,
    section_top_y: int,
    rows: list[dict],
    total_text: str,
    total_color: str,
    dot_colors: list[str],
    text_color: str,
    muted_color: str,
    labels: dict,
):
    inner_left = rect[0] + 12
    inner_right = rect[2] - 12
    header_y = section_top_y + 58

    head_font = _font(11, bold=True)
    row_font = _font(17, bold=False)
    total_font = _font(16, bold=True)

    col_grade_x = inner_left + 8
    col_dist_x = inner_left + int((inner_right - inner_left) * 0.40)
    col_pct_x = inner_left + int((inner_right - inner_left) * 0.74)

    draw.text((col_grade_x, header_y), _t(labels, "col_grade"), fill=muted_color, font=head_font)
    draw.text((col_dist_x, header_y), _t(labels, "col_distance"), fill=muted_color, font=head_font)
    draw.text((col_pct_x, header_y), _t(labels, "col_pct"), fill=muted_color, font=head_font)
    draw.line((inner_left, header_y + 18, inner_right, header_y + 18), fill="#2b4e3a", width=1)

    row_start_y = header_y + 24
    row_step = 31
    for idx, row in enumerate(rows[:4]):
        ry = row_start_y + idx * row_step
        dot = dot_colors[idx] if idx < len(dot_colors) else dot_colors[-1]
        draw.ellipse((inner_left, ry + 8, inner_left + 10, ry + 18), fill=dot)

        draw.text((col_grade_x + 18, ry), str(row.get("label", "")), fill=text_color, font=row_font)
        draw.text(
            (col_dist_x, ry),
            f"{float(row.get('distance_km', 0.0)):.2f} {_t(labels, 'unit_km')}",
            fill=text_color,
            font=row_font,
        )
        draw.text((col_pct_x, ry), f"{float(row.get('route_pct', 0.0)):.1f}%", fill=text_color, font=row_font)

    fit_total_font = _fit_font_for_width(
        draw,
        total_text,
        max_width=(inner_right - inner_left),
        start_size=29,
        min_size=15,
        bold=True,
    )
    draw.text((inner_left + 6, rect[3] - 42), total_text, fill=total_color, font=fit_total_font)


def _draw_ratio_gauge(
    draw: ImageDraw.ImageDraw,
    rect,
    value_pct: float,
    color: str,
    labels: dict,
    label_key: str,
    m_font,
    s_font,
):
    _panel(draw, rect, fill="#06272d", border="#335f39", radius=14, border_w=1)
    draw.text((rect[0] + 14, rect[1] + 12), _t(labels, label_key).upper(), fill=color, font=s_font)

    cx = (rect[0] + rect[2]) / 2
    cy = (rect[1] + rect[3]) / 2 + 12
    radius = min(rect[2] - rect[0], rect[3] - rect[1]) * 0.27
    gauge_box = (cx - radius, cy - radius, cx + radius, cy + radius)

    draw.arc(gauge_box, start=0, end=360, fill="#2f4c35", width=11)
    clamped = max(0.0, min(100.0, float(value_pct)))
    draw.arc(gauge_box, start=-90, end=-90 + (clamped * 3.6), fill=color, width=11)

    _draw_centered_text(draw, f"{clamped:.1f}%", (cx, cy), m_font, "#f2f7d8")


def _split_title(text: str, max_len: int = 30):
    words = str(text or "").strip().split()
    if not words:
        return []

    lines = []
    current = words[0]
    for w in words[1:]:
        if len(current) + 1 + len(w) <= max_len:
            current = f"{current} {w}"
        else:
            lines.append(current)
            current = w
            if len(lines) == 2:
                break
    if len(lines) < 2:
        lines.append(current)

    return lines[:2]


def _fit_title_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int = 2,
    start_size: int = 72,
    min_size: int = 34,
):
    """Fit a title by measured pixel width, preserving whole words where possible."""
    words = str(text or "").strip().split()
    if not words:
        return [""], _font(min_size, bold=True)

    def wrap(font):
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    for size in range(start_size, min_size - 1, -2):
        font = _font(size, bold=True)
        lines = wrap(font)
        if len(lines) <= max_lines and all(
            draw.textlength(line, font=font) <= max_width for line in lines
        ):
            return lines, font

    font = _font(min_size, bold=True)
    lines = wrap(font)
    kept = lines[:max_lines]
    if len(lines) > max_lines or any(
        draw.textlength(line, font=font) > max_width for line in kept
    ):
        # The final line carries all remaining text, with a measured ellipsis.
        remaining = " ".join(lines[max_lines - 1:])
        while remaining and draw.textlength(remaining + "…", font=font) > max_width:
            remaining = remaining[:-1]
        kept[-1] = remaining.rstrip() + "…"
    return kept, font


# Render final story image

def render_story(
    metadata,
    metrics,
    chart_path,
    output_path,
    theme="forest",
    lang=DEFAULT_LANG,
):
    if theme == "forest":
        from rendering.outdoor import render_outdoor_story
        return render_outdoor_story(metadata, metrics, chart_path, output_path, lang=lang)

    colors = THEMES.get(theme, THEMES["forest"])
    labels = _load_i18n(lang)
    icons = _load_required_icons()

    img = _gradient_background(
        WIDTH,
        HEIGHT,
        colors["bg_top"],
        colors["bg_bottom"],
    )

    draw = ImageDraw.Draw(img)

    title_font = _font(76, bold=True)
    subtitle_font = _font(26, bold=True)
    h_font = _font(38, bold=True)
    m_font = _font(29, bold=True)
    s_font = _font(22, bold=False)
    n_font = _font(64, bold=True)
    xs_font = _font(18, bold=True)
    label_font = _font(16, bold=True)
    total_font = _font(20, bold=True)
    badge_font = _font(20, bold=True)

    margin = 14
    content_w = WIDTH - margin * 2
    y = margin

    hero_h = 420
    hero_rect = (margin, y, margin + content_w, y + hero_h)
    _panel(draw, hero_rect, fill=colors["panel"], border=colors["border"], radius=20)

    date_label = _route_date_label(metadata, lang)
    if date_label:
        draw.text((margin + 26, y + 20), date_label, fill=colors["accent"], font=subtitle_font)

    title_lines, title_font = _fit_title_lines(
        draw,
        metadata.get("name") or _t(labels, "unnamed_route"),
        max_width=content_w - 52,
        max_lines=2,
        start_size=72,
        min_size=42,
    )
    draw.text((margin + 24, y + 64), title_lines[0], fill=colors["text"], font=title_font)
    if len(title_lines) > 1:
        draw.text((margin + 24, y + 64 + max(52, title_font.size + 7)), title_lines[1], fill=colors["text"], font=title_font)

    metrics_top = y + 254
    card_w = int((content_w - 48) / 5)
    top_metrics = [
        ("total_distance", _t(labels, "total_distance"), _fmt_km(metrics["distance_km"], labels), colors["text"]),
        ("ascent", _t(labels, "ascent"), f"+{_fmt_m(metrics['elevation_gain_m'], labels)}", colors["up"]),
        ("descent", _t(labels, "descent"), f"-{_fmt_m(metrics['elevation_loss_m'], labels)}", colors["down"]),
        ("total_time", _t(labels, "total_time"), _fmt_time(metrics["total_time"], labels), colors["text"]),
        ("speed", _t(labels, "avg_speed"), _fmt_speed(metrics["avg_speed_total"], labels), colors["text"]),
    ]
    for i, (icon_key, label, value, value_color) in enumerate(top_metrics):
        x = margin + 16 + i * (card_w + 8)
        _panel(
            draw,
            (x, metrics_top, x + card_w, metrics_top + 104),
            fill="#072c30",
            border="#335f39",
            radius=10,
            border_w=1,
        )
        draw.text((x + 10, metrics_top + 12), value, fill=value_color, font=m_font)
        _draw_icon_title(
            draw,
            img,
            icons[icon_key],
            label.upper(),
            x + 10,
            metrics_top + 68,
            colors["muted"],
            max_width=card_w - 16,
            start_size=16,
            min_size=11,
            bold=True,
        )

    _draw_icon_title(
        draw,
        img,
        icons["start"],
        f"{_t(labels, 'start')} {_fmt_time(metrics['start_time'], labels)}",
        margin + 28,
        y + 380,
        colors["text"],
        max_width=360,
        start_size=29,
        min_size=20,
        bold=True,
    )
    draw.text((margin + 420, y + 370), "|", fill=colors["muted"], font=m_font)
    _draw_icon_title(
        draw,
        img,
        icons["finish"],
        f"{_t(labels, 'end')} {_fmt_time(metrics['end_time'], labels)}",
        margin + 520,
        y + 380,
        colors["text"],
        max_width=320,
        start_size=29,
        min_size=20,
        bold=True,
    )

    y += hero_h + 12

    elev_h = 404
    elev_rect = (margin, y, margin + content_w, y + elev_h)
    _panel(draw, elev_rect, fill=colors["panel"], border=colors["border"], radius=20)
    _draw_icon_title(
        draw,
        img,
        icons["progression"],
        _t(labels, 'elevation_profile').upper(),
        margin + 22,
        y + 18,
        colors["text"],
        max_width=560,
        start_size=38,
        min_size=24,
        bold=True,
    )

    chart = Image.open(chart_path).convert("RGBA")
    chart = chart.resize((content_w - 48, 292))
    img.paste(chart, (margin + 24, y + 96), chart)

    _panel(
        draw,
        (margin + 640, y + 20, margin + 792, y + 88),
        fill="#173923",
        border="#335f39",
        radius=12,
        border_w=1,
    )
    _draw_icon_title(
        draw,
        img,
        icons["positive_progression"],
        f"{_t(labels, 'elevation_gain_short')} +{_fmt_m(metrics['elevation_gain_m'], labels)}",
        margin + 648,
        y + 38,
        colors["up"],
        max_width=140,
        start_size=20,
        min_size=13,
        bold=True,
    )

    _panel(
        draw,
        (margin + 808, y + 20, margin + 960, y + 88),
        fill="#3b1717",
        border="#6f2a2a",
        radius=12,
        border_w=1,
    )
    _draw_icon_title(
        draw,
        img,
        icons["negative_progression"],
        f"{_t(labels, 'elevation_loss_short')} -{_fmt_m(metrics['elevation_loss_m'], labels)}",
        margin + 816,
        y + 38,
        colors["down"],
        max_width=140,
        start_size=20,
        min_size=13,
        bold=True,
    )

    y += elev_h + 12

    row_h = 284
    left_w = int((content_w - 12) * 0.52)
    right_w = content_w - 12 - left_w

    left_rect = (margin, y, margin + left_w, y + row_h)
    right_rect = (margin + left_w + 12, y, margin + left_w + 12 + right_w, y + row_h)
    _panel(draw, left_rect, fill=colors["panel"], border=colors["border"], radius=18)
    _panel(draw, right_rect, fill=colors["panel"], border=colors["border"], radius=18)

    _draw_icon_title(
        draw,
        img,
        icons["speed"],
        _t(labels, "times_speeds").upper(),
        left_rect[0] + 18,
        y + 14,
        colors["text"],
        max_width=left_w - 36,
        start_size=29,
        min_size=18,
        bold=True,
    )
    _draw_icon_title(
        draw,
        img,
        icons["progression"],
        _t(labels, 'slope_ratios').upper(),
        right_rect[0] + 18,
        y + 14,
        colors["text"],
        max_width=right_w - 36,
        start_size=29,
        min_size=18,
        bold=True,
    )

    time_cells = [
        (_t(labels, "total_time"), _fmt_time(metrics["total_time"], labels)),
        (_t(labels, "moving"), _fmt_time(metrics["moving_time"], labels)),
        (_t(labels, "stopped"), _fmt_time(metrics["stopped_time"], labels)),
        (_t(labels, "avg_speed"), _fmt_speed(metrics["avg_speed_total"], labels)),
        (_t(labels, "avg_speed_moving"), _fmt_speed(metrics["avg_speed_moving"], labels)),
        (_t(labels, "max_speed"), _fmt_speed(metrics["max_speed"], labels)),
    ]
    cell_w = int((left_w - 36) / 3)
    for i, (lbl, val) in enumerate(time_cells):
        cx = left_rect[0] + 14 + (i % 3) * (cell_w + 4)
        cy = y + 60 + (i // 3) * 100
        _panel(draw, (cx, cy, cx + cell_w, cy + 92), fill="#072c30", border="#335f39", radius=8, border_w=1)
        draw.text((cx + 10, cy + 12), val, fill=colors["text"], font=m_font)
        cell_label = lbl.upper()
        fit_label_font = _fit_font_for_width(
            draw,
            cell_label,
            max_width=cell_w - 18,
            start_size=16,
            min_size=12,
            bold=True,
        )
        draw.text((cx + 10, cy + 60), cell_label, fill=colors["muted"], font=fit_label_font)

    grid_rect = (right_rect[0] + 10, y + 52, right_rect[2] - 10, y + 268)
    _panel(draw, grid_rect, fill="#06272d", border="#335f39", radius=8, border_w=1)

    mid_x = int((grid_rect[0] + grid_rect[2]) / 2)
    mid_y = int((grid_rect[1] + grid_rect[3]) / 2)
    draw.line((mid_x, grid_rect[1] + 2, mid_x, grid_rect[3] - 2), fill="#335f39", width=1)
    draw.line((grid_rect[0] + 2, mid_y, grid_rect[2] - 2, mid_y), fill="#335f39", width=1)

    top_left = (grid_rect[0], grid_rect[1], mid_x, mid_y)
    top_right = (mid_x, grid_rect[1], grid_rect[2], mid_y)
    bottom_left = (grid_rect[0], mid_y, mid_x, grid_rect[3])
    bottom_right = (mid_x, mid_y, grid_rect[2], grid_rect[3])

    ratio_label_font = _font(14, bold=True)
    ratio_value_font = _font(24, bold=True)
    metric_label_font = _font(15, bold=True)
    metric_value_font = _font(27, bold=True)
    metric_unit_font = _font(17, bold=True)

    def draw_ratio_cell(rect, label, value_pct, color):
        label_fit_font = _fit_font_for_width(
            draw,
            label,
            max_width=(rect[2] - rect[0]) - 16,
            start_size=14,
            min_size=11,
            bold=True,
        )
        label_w, _ = _text_size(draw, label, label_fit_font)
        draw.text((rect[0] + (rect[2] - rect[0] - label_w) / 2, rect[1] + 7), label, fill=colors["text"], font=label_fit_font)

        cx = int((rect[0] + rect[2]) / 2)
        cy = int((rect[1] + rect[3]) / 2) + 8
        radius = 34
        gauge_box = (cx - radius, cy - radius, cx + radius, cy + radius)
        draw.arc(gauge_box, start=0, end=360, fill="#2f4c35", width=11)

        clamped = max(0.0, min(100.0, float(value_pct)))
        draw.arc(gauge_box, start=-90, end=-90 + (clamped * 3.6), fill=color, width=11)

        value_text = f"{clamped:.1f}%"
        value_w, value_h = _text_size(draw, value_text, ratio_value_font)
        draw.text((cx - value_w / 2, cy - value_h / 2), value_text, fill=colors["text"], font=ratio_value_font)

    def draw_metric_cell(rect, label, value, color):
        label_fit_font = _fit_font_for_width(
            draw,
            label,
            max_width=(rect[2] - rect[0]) - 12,
            start_size=15,
            min_size=12,
            bold=True,
        )
        label_w, _ = _text_size(draw, label, label_fit_font)
        draw.text((rect[0] + (rect[2] - rect[0] - label_w) / 2, rect[1] + 9), label, fill=colors["text"], font=label_fit_font)

        value_text = f"{value:.1f}"
        fit_value_font = _fit_font_for_width(
            draw,
            value_text,
            max_width=(rect[2] - rect[0]) - 16,
            start_size=27,
            min_size=18,
            bold=True,
        )
        value_w, value_h = _text_size(draw, value_text, fit_value_font)
        value_y = rect[1] + 30
        draw.text((rect[0] + (rect[2] - rect[0] - value_w) / 2, value_y), value_text, fill=color, font=fit_value_font)

        unit_text = _t(labels, "unit_m_per_km")
        unit_w, _ = _text_size(draw, unit_text, metric_unit_font)
        draw.text((rect[0] + (rect[2] - rect[0] - unit_w) / 2, value_y + value_h + 7), unit_text, fill=color, font=metric_unit_font)

    draw_ratio_cell(top_left, _t(labels, "uphill_ratio").upper(), metrics["uphill_ratio_pct"], colors["up"])
    draw_ratio_cell(top_right, _t(labels, "downhill_ratio").upper(), metrics["downhill_ratio_pct"], colors["down"])

    up_label = _t(labels, "ascent_per_km").upper().replace("+/", " + /")
    down_label = _t(labels, "descent_per_km").upper().replace("-/", " - /")
    draw_metric_cell(bottom_left, up_label, metrics["ascent_per_km"], colors["up"])
    draw_metric_cell(bottom_right, down_label, metrics["descent_per_km"], colors["down"])

    y += row_h + 8

    triple_h = 330
    col_w = int((content_w - 24) / 3)
    up_rect = (margin, y, margin + col_w, y + triple_h)
    flat_rect = (margin + col_w + 12, y, margin + col_w * 2 + 12, y + triple_h)
    down_rect = (margin + col_w * 2 + 24, y, margin + col_w * 3 + 24, y + triple_h)

    for rect in (up_rect, flat_rect, down_rect):
        _panel(draw, rect, fill=colors["panel"], border=colors["border"], radius=18)

    _draw_icon_title(
        draw,
        img,
        icons["ascent_analysis"],
        _t(labels, "climb_analysis").upper(),
        up_rect[0] + 16,
        y + 14,
        colors["text"],
        max_width=col_w - 24,
        start_size=29,
        min_size=14,
        bold=True,
    )
    _draw_icon_title(
        draw,
        img,
        icons["flat_sections"],
        _t(labels, 'flat_sections').upper(),
        flat_rect[0] + 16,
        y + 14,
        colors["text"],
        max_width=col_w - 24,
        start_size=29,
        min_size=14,
        bold=True,
    )
    _draw_icon_title(
        draw,
        img,
        icons["descent_analysis"],
        _t(labels, "descent_analysis").upper(),
        down_rect[0] + 16,
        y + 14,
        colors["text"],
        max_width=col_w - 24,
        start_size=29,
        min_size=14,
        bold=True,
    )

    up_total_text = (
        f"{_t(labels, 'uphill_total')}: {metrics['uphill_distance_km']:.2f} "
        f"{_t(labels, 'unit_km')}"
    )
    _draw_slope_table(
        draw,
        up_rect,
        y,
        metrics["uphill_table"],
        up_total_text,
        colors["up"],
        dot_colors=["#ff3b30", "#ff6d00", "#ff9f0a", "#9acb22"],
        text_color=colors["text"],
        muted_color=colors["muted"],
        labels=labels,
    )

    flat_image = Path(__file__).resolve().parent / "images" / "flat_track.png"
    flat_center_x = int((flat_rect[0] + flat_rect[2]) / 2)
    if flat_image.exists():
        flat_icon = Image.open(flat_image).convert("RGBA")
        flat_icon = flat_icon.resize((180, 98))
        flat_icon_x = flat_center_x - int(flat_icon.width / 2)
        img.paste(flat_icon, (flat_icon_x, y + 202), flat_icon)

    flat_distance_text = f"{metrics['flat_distance_km']:.2f} {_t(labels, 'unit_km')}"
    flat_distance_w, _ = _text_size(draw, flat_distance_text, n_font)
    draw.text((flat_center_x - flat_distance_w / 2, y + 100), flat_distance_text, fill=colors["cold"], font=n_font)

    flat_ratio_text = f"({metrics['flat_ratio_pct']:.1f}% {_t(labels, 'flat_of_route')})"
    flat_ratio_w, _ = _text_size(draw, flat_ratio_text, m_font)
    draw.text((flat_center_x - flat_ratio_w / 2, y + 168), flat_ratio_text, fill=colors["text"], font=m_font)
    flat_hint = _t(labels, "flat_subtitle")
    flat_hint_font = _fit_font_for_width(
        draw,
        flat_hint,
        max_width=col_w - 42,
        start_size=19,
        min_size=14,
        bold=True,
    )
    flat_hint_w, _ = _text_size(draw, flat_hint, flat_hint_font)
    draw.text((flat_center_x - flat_hint_w / 2, y + 296), flat_hint, fill=colors["muted"], font=flat_hint_font)

    down_total_text = (
        f"{_t(labels, 'downhill_total')}: {metrics['downhill_distance_km']:.2f} "
        f"{_t(labels, 'unit_km')}"
    )
    _draw_slope_table(
        draw,
        down_rect,
        y,
        metrics["downhill_table"],
        down_total_text,
        colors["down"],
        dot_colors=["#9acb22", "#ff9f0a", "#2b7bff", "#1f4ed8"],
        text_color=colors["text"],
        muted_color=colors["muted"],
        labels=labels,
    )

    y += triple_h + 8

    distribution_h = 132
    distribution_rect = (margin, y, margin + content_w, y + distribution_h)
    _panel(draw, distribution_rect, fill=colors["panel"], border=colors["border"], radius=18)

    distribution_title = _t(labels, "slope_distribution").upper()
    _draw_icon_title(
        draw,
        img,
        icons["progression"],
        distribution_title,
        distribution_rect[0] + 16,
        y + 10,
        colors["text"],
        max_width=content_w - 40,
        start_size=29,
        min_size=17,
        bold=True,
    )

    uphill_rows = metrics.get("uphill_table") or []
    downhill_rows = metrics.get("downhill_table") or []

    uphill_parts = [
        {
            "label": str(row.get("label", "")),
            "pct": max(0.0, float(row.get("route_pct", 0.0))),
        }
        for row in uphill_rows
    ]
    downhill_parts = [
        {
            "label": str(row.get("label", "")),
            "pct": max(0.0, float(row.get("route_pct", 0.0))),
        }
        for row in downhill_rows
    ]
    flat_part = {
        "label": _t(labels, "flat_bin_label"),
        "pct": max(0.0, float(metrics.get("flat_ratio_pct", 0.0))),
    }

    total_part = sum(part["pct"] for part in uphill_parts) + flat_part["pct"] + sum(part["pct"] for part in downhill_parts)
    if total_part <= 0:
        raise ValueError("Invalid slope distribution percentages: total must be > 0")

    up_colors = _gradient_steps("#7f1d1d", "#facc15", len(uphill_parts))
    down_colors = _gradient_steps("#1e3a8a", "#93c5fd", len(downhill_parts))

    bar_x = margin + 24
    bar_y = y + 44
    bar_w = content_w - 48
    bar_h = 30
    segment_gap = 3

    segments = []
    for idx, part in enumerate(uphill_parts):
        segments.append({"label": part["label"], "pct": part["pct"], "color": up_colors[idx], "text": "#f8f8f8"})
    segments.append({"label": flat_part["label"], "pct": flat_part["pct"], "color": "#6b7280", "text": "#f8f8f8"})
    for idx, part in enumerate(downhill_parts):
        segments.append({"label": part["label"], "pct": part["pct"], "color": down_colors[idx], "text": "#f8f8f8"})

    available_w = max(len(segments), bar_w - segment_gap * max(0, len(segments) - 1))
    provisional = [
        max(1, int(round((seg["pct"] / total_part) * available_w)))
        for seg in segments
    ]

    delta = available_w - sum(provisional)
    if provisional and delta > 0:
        for i in range(delta):
            provisional[i % len(provisional)] += 1
    elif provisional and delta < 0:
        # Remove pixels from the widest segments first, but never below 1 px.
        shrink_order = sorted(
            range(len(provisional)),
            key=lambda idx: provisional[idx],
            reverse=True,
        )
        while delta < 0:
            changed = False
            for idx in shrink_order:
                if provisional[idx] > 1 and delta < 0:
                    provisional[idx] -= 1
                    delta += 1
                    changed = True
            if not changed:
                break

    pct_font = _font(12, bold=True)
    lbl_font = _font(12, bold=False)

    cursor_x = bar_x
    for idx, seg in enumerate(segments):
        seg_w = provisional[idx]
        seg_x0 = cursor_x
        seg_x1 = seg_x0 + seg_w

        draw.rounded_rectangle((seg_x0, bar_y, seg_x1, bar_y + bar_h), radius=5, fill=seg["color"])

        pct_text = f"{seg['pct']:.1f}%"
        pct_w, pct_h = _text_size(draw, pct_text, pct_font)
        draw.text(
            (seg_x0 + (seg_w - pct_w) / 2, bar_y + (bar_h - pct_h) / 2),
            pct_text,
            fill=seg["text"],
            font=pct_font,
        )

        lbl = seg["label"]
        lbl_fit_font = _fit_font_for_width(
            draw,
            lbl,
            max_width=max(20, seg_w - 4),
            start_size=12,
            min_size=9,
            bold=False,
        )
        lbl_w, _ = _text_size(draw, lbl, lbl_fit_font)
        draw.text((seg_x0 + (seg_w - lbl_w) / 2, bar_y + bar_h + 6), lbl, fill=colors["text"], font=lbl_fit_font)

        cursor_x = seg_x1 + segment_gap

    subtitle_font = _fit_font_for_width(
        draw,
        _t(labels, "steep_climb"),
        max_width=260,
        start_size=18,
        min_size=12,
        bold=True,
    )
    draw.text((bar_x, y + 104), _t(labels, "steep_climb"), fill="#facc15", font=subtitle_font)

    right_subtitle = _t(labels, "steep_descent")
    right_subtitle_font = _fit_font_for_width(
        draw,
        right_subtitle,
        max_width=260,
        start_size=18,
        min_size=12,
        bold=True,
    )
    right_w, _ = _text_size(draw, right_subtitle, right_subtitle_font)
    draw.text((bar_x + bar_w - right_w, y + 104), right_subtitle, fill="#ff3b30", font=right_subtitle_font)

    y += distribution_h + 8

    bottom_h = 236
    l_w = int((content_w - 12) / 2)
    r_w = content_w - 12 - l_w
    ext_rect = (margin, y, margin + l_w, y + bottom_h)
    gen_rect = (margin + l_w + 12, y, margin + l_w + 12 + r_w, y + bottom_h)
    _panel(draw, ext_rect, fill=colors["panel"], border=colors["border"], radius=18)
    _panel(draw, gen_rect, fill=colors["panel"], border=colors["border"], radius=18)

    _draw_icon_title(
        draw,
        img,
        icons["extreme"],
        _t(labels, "extreme_grades").upper(),
        ext_rect[0] + 16,
        y + 14,
        colors["text"],
        max_width=l_w - 28,
        start_size=29,
        min_size=18,
        bold=True,
    )
    _draw_icon_title(
        draw,
        img,
        icons["general"],
        _t(labels, "start_end_points").upper(),
        gen_rect[0] + 16,
        y + 14,
        colors["text"],
        max_width=r_w - 28,
        start_size=29,
        min_size=18,
        bold=True,
    )

    grid_left = ext_rect[0] + 10
    grid_top = y + 52
    grid_right = ext_rect[2] - 10
    grid_bottom = ext_rect[3] - 12
    gap = 8
    cell_w = int((grid_right - grid_left - gap) / 2)
    cell_h = int((grid_bottom - grid_top - gap) / 2)

    tiles = [
        {
            "rect": (grid_left, grid_top, grid_left + cell_w, grid_top + cell_h),
            "label": _t(labels, "max_uphill").upper(),
            "value": f"{metrics['max_up_grade_pct']:.1f}%",
            "color": colors["up"],
            "spark": True,
        },
        {
            "rect": (grid_left + cell_w + gap, grid_top, grid_right, grid_top + cell_h),
            "label": _t(labels, "max_downhill").upper(),
            "value": f"{metrics['max_down_grade_pct']:.1f}%",
            "color": colors["down"],
            "spark": True,
        },
        {
            "rect": (grid_left, grid_top + cell_h + gap, grid_left + cell_w, grid_bottom),
            "label": _t(labels, "avg_uphill").upper(),
            "value": f"{metrics['avg_up_grade_pct']:.1f}%",
            "color": colors["accent"],
            "spark": False,
        },
        {
            "rect": (grid_left + cell_w + gap, grid_top + cell_h + gap, grid_right, grid_bottom),
            "label": _t(labels, "avg_downhill").upper(),
            "value": f"{metrics['avg_down_grade_pct']:.1f}%",
            "color": colors["down"],
            "spark": False,
        },
    ]

    tile_label_font = _font(11, bold=True)
    tile_value_font = _font(33, bold=True)

    for tile in tiles:
        r = tile["rect"]
        _panel(draw, r, fill="#06272d", border="#335f39", radius=8, border_w=1)

        fit_label_font = _fit_font_for_width(
            draw,
            tile["label"],
            max_width=(r[2] - r[0]) - 12,
            start_size=11,
            min_size=9,
            bold=True,
        )
        draw.text((r[0] + 8, r[1] + 7), tile["label"], fill=colors["text"], font=fit_label_font)

        draw.text((r[0] + 8, r[1] + 30), tile["value"], fill=tile["color"], font=tile_value_font)

        if tile["spark"]:
            spark_y = r[3] - 14
            sx = r[0] + 56
            spark_points = [
                (sx, spark_y),
                (sx + 10, spark_y - 4),
                (sx + 22, spark_y - 10),
                (sx + 34, spark_y - 6),
                (sx + 46, spark_y - 12),
                (sx + 58, spark_y - 8),
                (sx + 70, spark_y - 4),
            ]
            draw.line(spark_points, fill=tile["color"], width=2)

    point_rows = [
        (_t(labels, "start_altitude"), _fmt_m(metrics['elevation_start_m'], labels), "#38bdf8"),
        (_t(labels, "end_altitude"), _fmt_m(metrics['elevation_end_m'], labels), "#f59e0b"),
    ]

    row_label_font = _font(24, bold=False)
    row_value_font = _font(30, bold=True)
    row_y0 = y + 92
    row_step = 64
    left_x = gen_rect[0] + 24
    right_x = gen_rect[2] - 22

    for idx, (lbl, val, dot_color) in enumerate(point_rows):
        ry = row_y0 + idx * row_step
        draw.ellipse((left_x, ry + 12, left_x + 14, ry + 26), fill=dot_color)
        draw.text((left_x + 22, ry + 4), lbl, fill=colors["text"], font=row_label_font)
        draw.text((right_x, ry + 3), val, fill=dot_color, font=row_value_font, anchor="ra")

    draw.line((gen_rect[0] + 20, row_y0 + 55, gen_rect[2] - 20, row_y0 + 55), fill="#294437", width=1)

    y += bottom_h + 8
    footer = _t(labels, "footer_text").format(points=metrics["point_count"])
    draw.text((margin + 16, y), footer, fill=colors["muted"], font=s_font)

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    img.save(output_path)