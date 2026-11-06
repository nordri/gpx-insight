"""Outdoor Minimal: deterministic Pillow renderer, presentation only.

No calculations are performed here; every number comes from analytics.metrics.
The original canvas renderer remains available for other themes.
"""
from __future__ import annotations

from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from rendering.canvas import (
    WIDTH, HEIGHT, _font, _fit_title_lines, _fmt_km, _fmt_m,
    _fmt_speed, _fmt_time, _load_i18n, _route_date_label, _t,
)

BG = "#101F1D"
PANEL = "#1A2C28"
PANEL_LIGHT = "#213832"
LINE = "#365047"
TEXT = "#F0F1E3"
MUTED = "#A7B8A8"
GREEN = "#B6D49A"
ORANGE = "#E8A17F"
BLUE = "#99C8CE"
NEUTRAL = "#81958D"
W, H = WIDTH, max(HEIGHT, 2140)  # Footer cards need their own vertical space.
M = 46
INNER = W - 2 * M


def font(size, bold=False):
    return _font(size, bold=bold)


def txt(d, x, y, s, size=24, color=TEXT, bold=False, anchor=None):
    d.text((x, y), str(s), font=font(size, bold), fill=color, anchor=anchor)


def line(d, xy, color=LINE, width=2):
    d.line(xy, fill=color, width=width)


def panel(d, box, fill=PANEL, radius=26):
    d.rounded_rectangle(box, radius=radius, fill=fill)


def title(d, x, y, name, sub=None):
    txt(d, x, y, name, 29, TEXT, True)
    if sub:
        txt(d, x, y + 40, sub, 18, MUTED)


def _f(value, digits=1, suffix=""):
    if value is None:
        return "N/D"
    return f"{value:.{digits}f}{suffix}"


def _grade(v):
    return "N/D" if v is None else f"{v:.1f}%"


def _pct(v):
    return max(0.0, float(v or 0))


def _metric(d, x, y, label, value, color=TEXT, value_size=40):
    txt(d, x, y, label.upper(), 17, MUTED, True)
    txt(d, x, y + 32, value, value_size, color, True)


def _tiny_icon(d, x, y, kind, color=GREEN, scale=1.0):
    """Anti-aliased vector icons rendered from compact SVG paths."""
    from io import BytesIO
    from PIL import Image
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("Outdoor icons require cairosvg; install it via requirements.txt") from exc
    paths = {
        "mountain": '<path d="M2 27 13 10 20 20 25 13 36 27"/><path d="m9 16 4 4 4-4"/>',
        "clock": '<circle cx="19" cy="21" r="14"/><path d="M19 11v10l7 4M15 3h8M19 3v4M31 8l4-3"/>',
        "distance": '<path d="M10 29C17 29 12 13 24 13" stroke-dasharray="3 4"/><path d="M10 32c-5-6-6-8-6-12a6 6 0 0 1 12 0c0 4-1 6-6 12Z"/><circle cx="10" cy="20" r="2"/><path d="M29 21c-5-6-6-8-6-12a6 6 0 0 1 12 0c0 4-1 6-6 12Z"/><circle cx="29" cy="9" r="2"/>',
        "up": '<path d="M3 30 15 11 22 22 28 14 37 30Z"/><path d="m11 17 4 4 4-4"/><path d="M30 8V2m-4 4 4-4 4 4"/>',
        "down": '<path d="M3 30 15 11 22 22 28 14 37 30Z"/><path d="m11 17 4 4 4-4"/><path d="M30 2v8m-4-4 4 4 4-4"/>',
    }
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><g fill="none" stroke="{color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">{paths.get(kind,paths["mountain"])}</g></svg>'
    dim = max(1,round(40*scale))
    png=cairosvg.svg2png(bytestring=svg.encode(),output_width=dim*3,output_height=dim*3)
    icon=Image.open(BytesIO(png)).convert("RGBA").resize((dim,dim),Image.Resampling.LANCZOS)
    # Draw context's underlying image is available through d._image.
    d._image.paste(icon,(round(x),round(y)),icon)


def _elevation_stat_box(d, x, y, label, value, accent, direction):
    """Draw a compact elevation badge without altering any route metrics."""
    width, height = 174, 66
    bg = "#284A35" if direction == "up" else "#4B302B"
    border = "#5D865A" if direction == "up" else "#895445"
    d.rounded_rectangle((x, y, x + width, y + height), radius=13,
                        fill=bg, outline=border, width=2)
    # Distinct, clean arrow; draw at native resolution (no font glyph dependency).
    arrow_x, arrow_y = x + 17, y + 21
    if direction == "up":
        d.line([(arrow_x, arrow_y + 11), (arrow_x + 14, arrow_y - 3)],
               fill=accent, width=4, joint="curve")
        d.line([(arrow_x + 5, arrow_y - 3), (arrow_x + 14, arrow_y - 3),
                (arrow_x + 14, arrow_y + 6)], fill=accent, width=4, joint="curve")
    else:
        d.line([(arrow_x, arrow_y - 3), (arrow_x + 14, arrow_y + 11)],
               fill=accent, width=4, joint="curve")
        d.line([(arrow_x + 5, arrow_y + 11), (arrow_x + 14, arrow_y + 11),
                (arrow_x + 14, arrow_y + 2)], fill=accent, width=4, joint="curve")
    txt(d, x + 43, y + 9, label.upper(), 14, accent, True)
    txt(d, x + 43, y + 32, value, 23, TEXT, True)


def _row_dividers(d, x, y, w, n):
    for i in range(1, n):
        xx = x + w * i / n
        line(d, [(xx, y), (xx, y+92)], LINE, 2)


def _draw_slope_rows(d, x, y, rows, accent):
    labels = ("PENDIENTE", "DISTANCIA", "% RUTA")
    txt(d,x,y,labels[0],14,MUTED,True)
    txt(d,x+152,y,labels[1],14,MUTED,True)
    txt(d,x+295,y,labels[2],14,MUTED,True)
    line(d,[(x,y+30),(x+372,y+30)])
    for idx,r in enumerate((rows or [])[:4]):
        yy=y+46+idx*38
        d.ellipse((x,yy+8,x+9,yy+17),fill=accent)
        txt(d,x+19,yy,str(r.get('label','')),19,TEXT)
        txt(d,x+152,yy,f"{float(r.get('distance_km',0)):.2f} km",19,TEXT)
        txt(d,x+295,yy,f"{float(r.get('route_pct',0)):.1f}%",19,TEXT)



ANALYSIS_BG = "#14251B"
ANALYSIS_CREAM = "#E6EBD9"
ANALYSIS_MUTED = "#CFD8CC"
ANALYSIS_DIVIDER = "#34443A"
ANALYSIS_UP = "#A3E635"
ANALYSIS_DOWN = "#F87150"


def draw_grade_analysis_card(d, x, y, width, height, rows, distance_km,
                             direction="up", lang="es"):
    """Render one four-row grade analysis card at 2x, without altering metrics."""
    from io import BytesIO
    import cairosvg
    S = 2
    w, h = int(round(width)), int(round(height))
    if w <= 0 or h <= 0:
        return
    layer = Image.new("RGBA", (w*S, h*S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(layer)
    def sc(v): return int(round(v*S))
    def f(sz, weight="regular"): return _time_font(sc(sz), weight)
    def write(px, py, value, size=15, color="#FFFFFF", weight="regular", anchor="lt"):
        hd.text((sc(px), sc(py)), str(value), font=f(size, weight),
                fill=color, anchor=anchor)

    hd.rounded_rectangle((0, 0, sc(w)-1, sc(h)-1), radius=sc(22), fill=ANALYSIS_BG)
    is_up = direction == "up"
    accent = ANALYSIS_UP if is_up else ANALYSIS_DOWN
    title_text = ("Análisis subidas" if is_up else "Análisis bajadas") if lang.startswith("es") else ("Climb analysis" if is_up else "Descent analysis")
    # Official Lucide trending-up / trending-down paths; no handmade arrows.
    path = ('<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>' if is_up
            else '<path d="m22 17-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           f'width="24" height="24"><g fill="none" stroke="{ANALYSIS_CREAM}" '
           f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</g></svg>')
    icon_size = sc(27)
    raw = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=icon_size*2, output_height=icon_size*2)
    icon = Image.open(BytesIO(raw)).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    layer.alpha_composite(icon, (sc(18), sc(17)))
    title_size = 19 if w < 400 else 21
    # Badge remains within the card even for long localized headings.
    badge_value = "N/D" if distance_km is None else f"{float(distance_km):.2f} km"
    badge_size = 13 if w < 400 else 15
    badge_width = max(70 if w < 400 else 84, hd.textlength(badge_value, font=f(badge_size, "bold"))/S+18)
    badge_left = w - 18 - badge_width
    while title_size > 13 and hd.textlength(title_text, font=f(title_size,"bold"))/S > badge_left-52:
        title_size -= 1
    write(49 if w < 400 else 56, 20, title_text, title_size, weight="bold")
    badge_bg = "#2E4B2B" if is_up else "#54352D"
    badge_fg = accent
    hd.rounded_rectangle((sc(badge_left),sc(17),sc(w-18),sc(47)),
                         radius=sc(15), fill=badge_bg)
    write((badge_left+w-18)/2, 32, badge_value, badge_size, badge_fg, "bold", "mm")

    # Columns: label left; both numeric values right-aligned.
    # Symmetric narrow side cards with three genuinely compact columns.
    pad = 17 if w < 400 else max(20, w * .10)
    dist_right = w * (.67 if w < 400 else .60)
    pct_right = w - (13 if w < 400 else w*.16)
    head_size = 10 if w < 400 else 12
    cell_size = 14 if w < 400 else 16
    write(pad, 76, "PENDIENTE" if lang.startswith("es") else "GRADE", head_size, ANALYSIS_MUTED, "semibold")
    write(dist_right, 76, "DISTANCIA" if lang.startswith("es") else "DISTANCE", head_size, ANALYSIS_MUTED, "semibold", "rt")
    write(pct_right, 76, "% RUTA" if lang.startswith("es") else "% ROUTE", head_size, ANALYSIS_MUTED, "semibold", "rt")
    hd.line((sc(pad),sc(100),sc(w-pad),sc(100)), fill=ANALYSIS_DIVIDER, width=sc(.5))
    # Each row has the same baseline spacing and an individual bin accent.
    palette_up = ("#F4D03F", "#D4D65B", "#9BCF67", "#6CA87D")
    palette_down = ("#74AEB1", "#B39E86", "#DE8C6A", "#FA6D4B")
    palette = palette_up if is_up else palette_down
    row_list = list(rows or [])[:4]
    for i, row in enumerate(row_list):
        yy = 111 + i*25
        dot_color = row.get("dot_color") or palette[i]
        hd.ellipse((sc(pad),sc(yy+6),sc(pad+9),sc(yy+15)), fill=dot_color)
        write(pad+15, yy, row.get("label", ""), cell_size)
        distance = row.get("distance_km")
        percentage = row.get("route_pct")
        dist_label = "N/D" if distance is None else f"{float(distance):.2f} km"
        pct_label = "N/D" if percentage is None else f"{float(percentage):.1f}%"
        write(dist_right, yy, dist_label, cell_size, anchor="rt")
        write(pct_right, yy, pct_label, cell_size, anchor="rt")
    if not row_list:
        write(w/2, 155, "Sin datos de pendiente" if lang.startswith("es") else "No grade data", 15, ANALYSIS_MUTED, anchor="mm")
    final = layer.resize((w, h), Image.Resampling.LANCZOS)
    d._image.paste(final, (round(x),round(y)), final)

def draw_flat_sections_card(d, x, y, width, height, metrics, lang="es"):
    """Center column of the uphill / flat / downhill triptych; no metric inference."""
    from io import BytesIO
    import cairosvg
    S = 2
    w, h = round(width), round(height)
    if w <= 0 or h <= 0:
        return
    layer = Image.new("RGBA", (w*S, h*S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(layer)
    hd.rounded_rectangle((0, 0, w*S-1, h*S-1), radius=22*S, fill=ANALYSIS_BG)
    def face(sz, weight="regular"):
        return _time_font(round(sz*S), weight)
    def put(cx, cy, value, sz, color, weight="regular", anchor="mm"):
        hd.text((round(cx*S), round(cy*S)), value, font=face(sz, weight), fill=color, anchor=anchor)

    # Lucide arrow-left-right: standard path, identical visual weight to side icons.
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           f'<g fill="none" stroke="{ANALYSIS_CREAM}" stroke-width="2" '
           f'stroke-linecap="round" stroke-linejoin="round">'
           f'<path d="M8 3 4 7l4 4M4 7h16M16 21l4-4-4-4M20 17H4"/>'
           f'</g></svg>')
    size = 24*S
    raw = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size*2, output_height=size*2)
    icon = Image.open(BytesIO(raw)).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    layer.alpha_composite(icon, (14*S, 18*S))
    heading = "TRAMOS LLANOS" if lang.startswith("es") else "FLAT SECTIONS"
    heading_size = 16
    while heading_size > 12 and hd.textlength(heading, font=face(heading_size,"bold")) > (w-53)*S:
        heading_size -= 1
    put(45, 31, heading, heading_size, "#FFFFFF", "bold", "lm")

    distance = metrics.get("flat_distance_km")
    ratio = metrics.get("flat_ratio_pct")
    value = "N/D" if distance is None else f"{float(distance):.2f} km"
    percentage = "N/D" if ratio is None else f"({float(ratio):.1f}%)"
    put(w/2, 105, value, 31 if w >= 220 else 26, "#A3E635", "bold")
    put(w/2, 143, percentage, 19, "#FFFFFF", "semibold")
    put(w/2, 173, "Pendiente < 1 %" if lang.startswith("es") else "Grade < 1%", 14, ANALYSIS_MUTED)
    # Decorative contour, deliberately restrained and not data-bearing.
    hd.line([(20*S, (h-21)*S), ((w-20)*S, (h-21)*S)], fill="#426047", width=S*2)
    final = layer.resize((w, h), Image.Resampling.LANCZOS)
    d._image.paste(final, (round(x), round(y)), final)


def _distribution(d, x, y, width, metrics):
    ups = list(metrics.get("uphill_table") or [])
    downs = list(metrics.get("downhill_table") or [])
    parts = [(_pct(r.get("route_pct")), GREEN) for r in ups]
    parts += [(_pct(metrics.get("flat_ratio_pct")), NEUTRAL)]
    parts += [(_pct(r.get("route_pct")), ORANGE) for r in downs]
    total=sum(p for p,_ in parts)
    if not total:
        return
    cursor=x
    for i,(v,c) in enumerate(parts):
        seg_w=width*v/total
        if seg_w>0:
            d.rectangle((int(cursor),y,int(cursor+seg_w+0.5),y+25),fill=c)
        cursor+=seg_w
    txt(d,x,y+40,"SUBIDA",17,GREEN,True)
    txt(d,x+width/2,y+40,"LLANO",17,MUTED,True,anchor="mt")
    txt(d,x+width,y+40,"BAJADA",17,ORANGE,True,anchor="ra")



ASSET_DIR = Path(__file__).resolve().parent / "assets"
SLOPE_UP = ("#E95738", "#F18B35", "#EFB742", "#C7DB69")
SLOPE_DOWN = ("#9CC4F0", "#73A5DF", "#4C79C4", "#345B9C")


def scenic_header(img):
    """Composite an illustrated background with a legibility gradient."""
    asset = ASSET_DIR / "mountain-header.jpg"
    with Image.open(asset) as source:
        scene = source.convert("RGB").resize((W, 355), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (W, 355))
    opx = overlay.load()
    for yy in range(355):
        for xx in range(W):
            # Darker at left and bottom, keeping the title readable.
            darkness = int(216 * (1 - xx / W) ** 1.5 + 65 * (yy / 355))
            opx[xx, yy] = (7, 27, 23, min(240, darkness))
    scene = Image.alpha_composite(scene.convert("RGBA"), overlay)
    img.paste(scene.convert("RGB"), (0, 0))


def footer_landscape(img):
    with Image.open(ASSET_DIR / "mountain-footer.png") as source:
        layer = source.convert("RGBA")
        layer = layer.resize((W, 48), Image.Resampling.LANCZOS)
        img.paste(layer, (0, H-layer.height), layer)


def gradient_card(img, box, top, bottom, radius=23):
    x0,y0,x1,y1=map(int,box)
    width,height=x1-x0,y1-y0
    gradient=Image.new("RGB",(width,height))
    gd=ImageDraw.Draw(gradient)
    a=tuple(int(top[i:i+2],16) for i in (1,3,5))
    b=tuple(int(bottom[i:i+2],16) for i in (1,3,5))
    for yy in range(height):
        t=yy/max(1,height-1)
        gd.line((0,yy,width,yy),fill=tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3)))
    mask=Image.new("L",(width,height))
    ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1),radius=radius,fill=255)
    img.paste(gradient,(x0,y0),mask)


def ring(d,cx,cy,r,value,color):
    d.arc((cx-r,cy-r,cx+r,cy+r),0,359,fill="#45665B",width=12)
    if value is not None:
        d.arc((cx-r,cy-r,cx+r,cy+r),-90,-90+max(0,min(100,value))*3.6,fill=color,width=12)
    txt(d,cx,cy-15,_grade(value),29,TEXT,True,anchor="mt")


# Slope distribution uses the nine validated analytics bins in their original order.
DISTRIBUTION_COLORS = (
    "#E95738", "#F18B35", "#F4D03F", "#C7DB69",
    "#81958D", "#9CC4F0", "#73A5DF", "#4C79C4", "#345B9C",
)
DISTRIBUTION_FG = ("#FFFFFF", "#FFFFFF", "#14251B", "#14251B",
                   "#FFFFFF", "#14251B", "#FFFFFF", "#FFFFFF", "#FFFFFF")


def _distribution_bins(metrics):
    ups = list(metrics.get("uphill_table") or [])[:4]
    downs = list(metrics.get("downhill_table") or [])[:4]
    rows = ups + [{"route_pct": metrics.get("flat_ratio_pct"), "label": "< 1%"}] + downs
    if len(ups) != 4 or len(downs) != 4:
        raise ValueError("Slope distribution requires four uphill and four downhill bins")
    values = [max(0., float(r.get("route_pct") or 0.)) for r in rows]
    total = sum(values)
    # Use analytics percentages; only normalize for numerical rounding / missing fractions.
    return [(v / total if total else 0., str(row.get("label") or ""), color, fg)
            for v, row, color, fg in zip(values, rows, DISTRIBUTION_COLORS, DISTRIBUTION_FG)]


def _distribution_font(size, bold=False):
    from PIL import ImageFont
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return _font(size, bold=bold)


def draw_slope_distribution_card(d, x, y, width, height, metrics, lang="es"):
    """Render at 2x, downsample once, and composite into the original canvas."""
    from io import BytesIO
    import cairosvg
    S = 2
    w, h = round(width), round(height)
    layer = Image.new("RGBA", (w*S, h*S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(layer)
    def xy(v): return round(v*S)
    def text_at(cx, top, content, size, color, bold=False, anchor="mm"):
        hd.text((xy(cx), xy(top)), content, font=_distribution_font(xy(size), bold),
                fill=color, anchor=anchor)
    hd.rounded_rectangle((0, 0, xy(w)-1, xy(h)-1), radius=xy(20), fill="#14251B")
    # Lucide 'layers' official paths, native 24x24 viewBox.
    icon_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
                f'viewBox="0 0 24 24" fill="none" stroke="#E6EBD9" '
                f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
                f'<path d="m12.83 2.18 8 4a2 2 0 0 1 0 3.58l-8 4a2 2 0 0 1-1.66 0l-8-4a2 2 0 0 1 0-3.58l8-4a2 2 0 0 1 1.66 0Z"/>'
                f'<path d="m2 12 9.17 4.59a2 2 0 0 0 1.66 0L22 12M2 17l9.17 4.59a2 2 0 0 0 1.66 0L22 17"/>'
                f'</svg>')
    icon = Image.open(BytesIO(cairosvg.svg2png(bytestring=icon_svg.encode(),
                 output_width=xy(25), output_height=xy(25)))).convert("RGBA")
    layer.alpha_composite(icon, (xy(19), xy(13)))
    heading = "Distribución de pendientes" if lang.startswith("es") else "Slope distribution"
    text_at(54, 25, heading, 19, "#FFFFFF", True, "lm")

    # An absent distribution is unknown, not nine measured zero-percent bins.
    # Preserve the card and its dimensions without inventing analytics values.
    has_distribution = (len(metrics.get("uphill_table") or []) >= 4
                        and len(metrics.get("downhill_table") or []) >= 4
                        and metrics.get("flat_ratio_pct") is not None)
    if not has_distribution:
        message = "Sin datos de pendiente" if lang.startswith("es") else "No slope data"
        text_at(w / 2, 95, message, 15, "#CFD8CC", anchor="mm")
        final = layer.resize((w, h), Image.Resampling.LANCZOS)
        d._image.paste(final, (round(x), round(y)), final)
        return

    bins = _distribution_bins(metrics)
    bar_x, bar_y, bar_w, bar_h = 19, 57, w-38, 32
    bar = Image.new("RGBA", (xy(bar_w), xy(bar_h)), "#3B523E")
    bd = ImageDraw.Draw(bar)
    cumulative = 0.
    centers = []
    for fraction, label, color, fg in bins:
        start = round(cumulative * bar.width)
        cumulative += fraction
        end = round(cumulative * bar.width)
        if end > start:
            bd.rectangle((start, 0, end-1, bar.height), fill=color)
        centers.append(bar_x + (start + end)/(2*S))
    mask = Image.new("L", bar.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,bar.width-1,bar.height-1),
                                           radius=xy(16), fill=255)
    layer.paste(bar, (xy(bar_x), xy(bar_y)), mask)
    for (fraction, label, color, fg), center in zip(bins, centers):
        segment_width = fraction * bar_w
        pct_text = f"{fraction*100:.1f}%"
        # Only draw text where it fits; never let one percentage bleed into another bin.
        font = _distribution_font(xy(12), True)
        if segment_width*S >= hd.textlength(pct_text, font=font) + xy(7):
            text_at(center, bar_y+bar_h/2, pct_text, 12, fg, True)
        # Labels remain centered on the exact segment centers; omit when too narrow.
        label_font = _distribution_font(xy(11))
        if segment_width*S >= hd.textlength(label, font=label_font) + xy(4):
            text_at(center, 104, label, 11, "#CFD8CC")
    text_at(19, 132, "▲  SUBIDA FUERTE", 13, "#F4D03F", True, "lm")
    text_at(w-19, 132, "BAJADA FUERTE  ▼", 13, "#FA6D4B", True, "rm")
    final = layer.resize((w, h), Image.Resampling.LANCZOS)
    d._image.paste(final, (round(x), round(y)), final)


def slope_distribution(d, x, y, width, metrics):
    """Legacy compatibility wrapper; prefer draw_slope_distribution_card."""
    draw_slope_distribution_card(d, x, y, width, 150, metrics)


# Tiempos y velocidades: one visual system, independent of analytics.
TIME_ICON_COLOR = "#E6EBD9"
TIME_LABEL_COLOR = "#CFD8CC"
TIME_VALUE_COLOR = "#FFFFFF"
TIME_DIVIDER_COLOR = "#3B5045"  # ~12% white over forest green

# Material Icons: directions_run (filled). Lucide: circle-pause, gauge, timer.
# Keep paths at their native 24x24 viewBox; no hand-built stick figures.
TIME_CARD_ICONS = {
    # Font Awesome Free 6.7.2 person-running (CC BY 4.0), Fonticons, Inc.
    "runner": '<g fill="currentColor" stroke="none" transform="translate(2.8 1.5) scale(0.041)"><path d="M320 48a48 48 0 1 0 -96 0 48 48 0 1 0 96 0zM125.7 175.5c9.9-9.9 23.4-15.5 37.5-15.5c1.9 0 3.8 .1 5.6 .3L137.6 254c-9.3 28 1.7 58.8 26.8 74.5l86.2 53.9-25.4 88.8c-4.9 17 5 34.7 22 39.6s34.7-5 39.6-22l28.7-100.4c5.9-20.6-2.6-42.6-20.7-53.9L238 299l30.9-82.4 5.1 12.3C289 264.7 323.9 288 362.7 288l21.3 0c17.7 0 32-14.3 32-32s-14.3-32-32-32l-21.3 0c-12.9 0-24.6-7.8-29.5-19.7l-6.3-15c-14.6-35.1-44.1-61.9-80.5-73.1l-48.7-15c-11.1-3.4-22.7-5.2-34.4-5.2c-31 0-60.8 12.3-82.7 34.3L57.4 153.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l23.1-23.1zM91.2 352L32 352c-17.7 0-32 14.3-32 32s14.3 32 32 32l69.6 0c19 0 36.2-11.2 43.9-28.5L157 361.6l-9.5-6c-17.5-10.9-30.5-26.8-37.9-44.9L91.2 352z"/></g>',
    "pause": ('<circle cx="12" cy="12" r="10"/><path d="M10 15V9m4 6V9"/>'),
    "gauge": ('<path d="M12 14 8 10"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'),
    "gauge_max": ('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'),
    "stopwatch": ('<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6m-3 0v3m6 2 2-2"/>'),
}


def _time_font(size, weight="regular"):
    """Use native-size uncondensed fonts; no horizontal rescaling."""
    from PIL import ImageFont
    candidates = {
        "bold": ("/usr/share/fonts/opentype/inter/Inter-Bold.otf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        "semibold": ("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        "regular": ("/usr/share/fonts/opentype/inter/Inter-Regular.otf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    }
    for candidate in candidates[weight]:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return font(size, weight != "regular")


def _time_card_icon(d, x, y, kind, size=35, color=TIME_ICON_COLOR):
    """Render standard 24x24 icon paths at 4x then downsample isotropically."""
    from io import BytesIO
    import cairosvg
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           f'width="24" height="24"><g color="{color}" fill="none" '
           f'stroke="{color}" stroke-width="2.4" stroke-linecap="round" '
           f'stroke-linejoin="round">{TIME_CARD_ICONS[kind]}</g></svg>')
    raw = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=size*4, output_height=size*4)
    icon = Image.open(BytesIO(raw)).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    d._image.paste(icon, (round(x), round(y)), icon)


def _time_text(d, xy, value, size, color, weight="regular", spacing=0):
    """Render Unicode text in one shaped run to preserve kerning and accents."""
    face = _time_font(size, weight)
    x, y = xy
    # Pillow's native shaping keeps combining marks attached to their base glyph.
    d.text((round(x), round(y)), str(value), font=face, fill=color,
           anchor="lt", stroke_width=0)


def _time_label(raw):
    """Normalize abbreviations, not accents or the metrics themselves."""
    import unicodedata
    label = unicodedata.normalize("NFC", str(raw)).upper()
    # Protect the conventional low period even if a source label uses a middle dot.
    return label.replace("VEL˙", "VEL.").replace("VEL·", "VEL.")


def draw_times_card(d, x, y, width, height, labels_and_values):
    """Render a balanced 2x2 card; values come from the existing formatters."""
    heading="Tiempos y velocidades" if str(labels_and_values[0][2]).startswith("es") else "Times & speeds"
    _time_card_icon(d,x+22,y+19,"stopwatch",size=32)
    _time_text(d,(x+65,y+21),heading,24,TIME_VALUE_COLOR,"semibold")

    pad=20
    top=y+76
    bottom=y+height-18
    mid_x=x+width/2
    mid_y=(top+bottom)/2
    d.line([(round(mid_x),round(top)),(round(mid_x),round(bottom))],fill=TIME_DIVIDER_COLOR,width=1)
    d.line([(x+pad,round(mid_y)),(x+width-pad,round(mid_y))],fill=TIME_DIVIDER_COLOR,width=1)

    col_width=width/2
    row_height=(bottom-top)/2
    icon_size=36
    gap=12
    for i,(label,value,_) in enumerate(labels_and_values):
        col=i%2
        row=i//2
        left=x+col*col_width
        center_y=top+(row+.5)*row_height
        icon_x=left+19
        # Icon and two-line text block share the same vertical centre.
        icon_y=center_y-icon_size/2
        text_x=icon_x+icon_size+gap
        label_y=center_y-26
        value_y=center_y+1
        _time_card_icon(d,icon_x,icon_y,("runner","pause","gauge","gauge_max")[i],size=icon_size)
        # Use a readable label size while respecting the available half-width.
        available=(left+col_width-9)-text_x
        label=_time_label(label)
        label_size=14
        face=_time_font(label_size,"semibold")
        while label_size>11 and d.textlength(label,font=face)>available:
            label_size-=1
            face=_time_font(label_size,"semibold")
        _time_text(d,(text_x,label_y),label,label_size,TIME_LABEL_COLOR,"semibold")
        value_size=27
        face=_time_font(value_size,"bold")
        while value_size>19 and d.textlength(str(value),font=face)>available:
            value_size-=1
            face=_time_font(value_size,"bold")
        _time_text(d,(text_x,value_y),str(value),value_size,TIME_VALUE_COLOR,"bold")



SLOPE_CARD_BG = "#182A1F"
SLOPE_CARD_TRACK = "#3B523E"
SLOPE_CARD_UP = "#A3E635"
SLOPE_CARD_DOWN = "#F87150"
SLOPE_CARD_CREAM = "#E6EBD9"


def _slope_svg(d, x, y, size, content):
    """Rasterize SVG at 4x; preserve its square aspect ratio."""
    from io import BytesIO
    import cairosvg
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
           f'width="100" height="100">{content}</svg>')
    raw = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=size * 4, output_height=size * 4)
    icon = Image.open(BytesIO(raw)).convert("RGBA").resize(
        (size, size), Image.Resampling.LANCZOS)
    d._image.paste(icon, (round(x), round(y)), icon)


def _slope_ring(d, cx, cy, percentage, accent, diameter=124):
    """SVG-native circles with mathematically exact dash length and round caps."""
    radius = 38
    circumference = 2 * math.pi * radius
    progress = max(0.0, min(100.0, float(percentage or 0)))
    base = (f'<circle cx="50" cy="50" r="{radius}" fill="none" '
            f'stroke="{SLOPE_CARD_TRACK}" stroke-width="9"/>')
    if percentage is not None and progress > 0:
        # A full circle must not show a gap caused by rounded stroke caps.
        if progress >= 100:
            base += (f'<circle cx="50" cy="50" r="{radius}" fill="none" '
                     f'stroke="{accent}" stroke-width="9"/>')
        else:
            base += (f'<circle cx="50" cy="50" r="{radius}" fill="none" '
                     f'stroke="{accent}" stroke-width="9" stroke-linecap="round" '
                     f'stroke-dasharray="{circumference:.9f}" '
                     f'stroke-dashoffset="{(circumference * (1 - progress / 100)):.9f}" '
                     f'transform="rotate(-90 50 50)"/>')
    _slope_svg(d, cx - diameter / 2, cy - diameter / 2, diameter, base)
    value = _grade(percentage)
    size = 21 if len(value) <= 5 else 18
    d.text((round(cx), round(cy)), value, font=_time_font(size, "bold"),
           fill="#FFFFFF", anchor="mm")


def draw_slope_ratios_card(d, x, y, width, height, metrics, labels):
    """Two symmetric slope ratios; all numerical inputs come from analytics."""
    d.rounded_rectangle((x, y, x + width, y + height), radius=22,
                        fill=SLOPE_CARD_BG)
    # Official Lucide 'mountain' outline (24x24 path, scaled by SVG viewBox).
    mountain = ('<g transform="translate(7 8) scale(3.5)" fill="none" '
                f'stroke="{SLOPE_CARD_CREAM}" stroke-width="1.8" '
                'stroke-linecap="round" stroke-linejoin="round">'
                '<path d="m8 3 4 8 5-5 5 15H2L8 3Z"/></g>')
    _slope_svg(d, x + 19, y + 17, 31, mountain)
    heading = _t(labels, "slope_ratios")
    d.text((x + 61, y + 21), heading, font=_time_font(23, "semibold"),
           fill="#FFFFFF", anchor="lt")

    centers = (x + width * .25, x + width * .75)
    ring_y = y + 127
    for cx, value, color, key in (
        (centers[0], metrics.get("uphill_ratio_pct"), SLOPE_CARD_UP, "uphill_ratio"),
        (centers[1], metrics.get("downhill_ratio_pct"), SLOPE_CARD_DOWN, "downhill_ratio"),
    ):
        _slope_ring(d, cx, ring_y, value, color)
        d.text((round(cx), y + 201), _t(labels, key).upper(),
               font=_time_font(14, "semibold"), fill="#CFD8CC", anchor="mt")

    divider_y = y + 222
    d.line([(x + 20, divider_y), (x + width - 20, divider_y)],
           fill="#3B4B40", width=1)
    for cx, value, color, arrow in (
        (centers[0], metrics.get("ascent_per_km"), SLOPE_CARD_UP, "↑"),
        (centers[1], metrics.get("descent_per_km"), SLOPE_CARD_DOWN, "↓"),
    ):
        label = f"{arrow} {_f(abs(value) if value is not None else None, 1, ' m/km')}"
        size = 19
        while size > 14 and d.textlength(label, font=_time_font(size, "semibold")) > width / 2 - 14:
            size -= 1
        d.text((round(cx), y + 240), label, font=_time_font(size, "semibold"),
               fill=color, anchor="mt")

def draw_extreme_grades_card(d, x, y, width, height, metrics, lang="es"):
    """Footer left: four grade statistics, drawn at 2x with no font stretching."""
    from io import BytesIO
    import cairosvg

    scale = 2
    sw, sh = round(width * scale), round(height * scale)
    card = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, sw - 1, sh - 1), radius=22 * scale, fill="#14251B")
    def f(size, bold=False):
        return _time_font(size * scale, "bold" if bold else "regular")
    def center(text, cx, cy, size, color, bold=False):
        cd.text((round(cx * scale), round(cy * scale)), text, font=f(size, bold),
                fill=color, anchor="mm")
    cream, muted, lime, coral = "#E6EBD9", "#CFD8CC", "#A3E635", "#FA6D4B"
    icon_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24"><path d="m2 20 7-11 4 6 3-4 6 9" fill="none" stroke="{cream}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
    png = cairosvg.svg2png(bytestring=icon_svg.encode("utf-8"), output_width=64, output_height=64)
    icon = Image.open(BytesIO(png)).convert("RGBA")
    card.alpha_composite(icon, (19 * scale, 15 * scale))
    heading = "Pendientes extremas" if lang.startswith("es") else "Extreme grades"
    cd.text((58 * scale, 20 * scale), heading, font=f(19, True), fill="#FFFFFF")
    top = 69
    bottom = height - 15
    mid_y = (top + bottom) / 2
    mid_x = width / 2
    divider = (255, 255, 255, 30)
    cd.line((round(mid_x * scale), round(top * scale), round(mid_x * scale), round(bottom * scale)), fill=divider, width=scale)
    cd.line((round(18 * scale), round(mid_y * scale), round((width - 18) * scale), round(mid_y * scale)), fill=divider, width=scale)
    values = [
        ("PEND. MÁX. SUBIDA", metrics.get("max_up_grade_pct"), lime, False),
        ("PEND. MÁX. BAJADA", metrics.get("max_down_grade_pct"), coral, False),
        ("PEND. MEDIA SUBIDA", metrics.get("avg_up_grade_pct"), lime, False),
        ("PEND. MEDIA BAJADA", metrics.get("avg_down_grade_pct"), coral, True),
    ]
    centers = [(width * .25, (top + mid_y) / 2), (width * .75, (top + mid_y) / 2),
               (width * .25, (mid_y + bottom) / 2), (width * .75, (mid_y + bottom) / 2)]
    for (label, value, color, negative), (cx, cy) in zip(values, centers):
        if value is None:
            value_text = "N/D"
        else:
            magnitude = abs(float(value))
            value_text = ("-" if negative else "") + f"{magnitude:.1f}%"
        label_size = 11
        while label_size > 8 and cd.textlength(label, font=f(label_size, True)) > (width / 2 - 15) * scale:
            label_size -= 1
        center(label, cx, cy - 15, label_size, muted, True)
        value_size = 29
        while value_size > 19 and cd.textlength(value_text, font=f(value_size, True)) > (width / 2 - 16) * scale:
            value_size -= 1
        center(value_text, cx, cy + 14, value_size, color, True)
    card = card.resize((round(width), round(height)), Image.Resampling.LANCZOS)
    d._image.paste(card, (round(x), round(y)), card)


def render_outdoor_story(metadata, metrics, chart_path, output_path, lang="es"):
    labels=_load_i18n(lang)
    img=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(img)
    scenic_header(img)
    d=ImageDraw.Draw(img)
    _tiny_icon(d,M,39,"mountain",GREEN,1.15)
    txt(d,M+51,40,"GPX  /  INSIGHT",21,GREEN,True)
    date=_route_date_label(metadata,lang)
    txt(d,M,102,date.upper(),19,MUTED,True)
    name=metadata.get("name") or _t(labels,"unnamed_route")
    # Title area is taller than the old renderer, no clipped line 2.
    title_lines, title_font=_fit_title_lines(d,name,INNER-20,3,51,30)
    ty=139
    for ln in title_lines:
        txt(d,M,ty,ln,title_font.size,TEXT,True)
        ty+=title_font.size+10
    # Hero KPI row, no separate outlined cards
    kpi_palette=[("#1D4D42","#17382F"),("#2B5738","#1A382A"),("#654135","#392D2B"),("#23505A","#17343C")]
    kpi_w=(INNER-18)/4
    for i,(top,bottom) in enumerate(kpi_palette):
        x=M+i*(kpi_w+6)
        gradient_card(img,(x,355,x+kpi_w,525),top,bottom,24)
    d=ImageDraw.Draw(img)
    values=[
        (_t(labels,"total_distance"),_fmt_km(metrics["distance_km"]),TEXT,"distance"),
        (_t(labels,"ascent"),"+"+_fmt_m(metrics["elevation_gain_m"]),GREEN,"up"),
        (_t(labels,"descent"),"-"+_fmt_m(metrics["elevation_loss_m"]),ORANGE,"down"),
        (_t(labels,"total_time"),_fmt_time(metrics["total_time"]),TEXT,"clock"),
    ]
    col=(INNER-18)/4+6
    for i,(lab,val,c,ico) in enumerate(values):
        center=M+i*col+kpi_w/2
        _tiny_icon(d,center-20,365,ico,c,1.0)
        txt(d,center,415,lab.upper(),19,TEXT,True,anchor="mt")
        txt(d,center,456,val,35,c,True,anchor="mt")

    # Display the start and end times provided by the analytics engine.
    txt(d,M+12,545,f"{_t(labels,'start')}: {_fmt_time(metrics['start_time'])}",25,TEXT,True)
    txt(d,W-M-12,545,f"{_t(labels,'end')}: {_fmt_time(metrics['end_time'])}",25,TEXT,True,anchor="ra")
    # Elevation chart: large quiet canvas, original analytical chart preserved
    gradient_card(img,(M,595,W-M,1012),"#1B3C32","#142A26",26)
    d=ImageDraw.Draw(img)
    _tiny_icon(d,M+24,619,"mountain",GREEN,.95)
    title(d,M+66,617,_t(labels,"elevation_profile"))
    # Elevation summary badges: same upper-right area, above the chart.
    badge_y = 609
    badge_gap = 12
    badge_width = 174
    right = W - M - 24
    _elevation_stat_box(d, right - 2 * badge_width - badge_gap, badge_y,
                        _t(labels, "ascent"),
                        "+" + _fmt_m(metrics["elevation_gain_m"]), GREEN, "up")
    _elevation_stat_box(d, right - badge_width, badge_y,
                        _t(labels, "descent"),
                        "-" + _fmt_m(metrics["elevation_loss_m"]), ORANGE, "down")
    with Image.open(chart_path) as chart_src:
        chart=chart_src.convert("RGBA")
        chart.thumbnail((INNER-55,315),Image.Resampling.LANCZOS)
        # Keep aspect ratio; don't stretch a data chart
        box=Image.new("RGBA",(INNER-48,325),(0,0,0,0))
        bx=(box.width-chart.width)//2
        by=(box.height-chart.height)//2
        box.alpha_composite(chart,(bx,by))
        img.paste(box,(M+24,675),box)
    # Secondary data, deliberately not competing with elevation profile
    y=1030
    half=(INNER-16)//2
    gradient_card(img,(M,y,M+half,y+278),"#244D3A","#19362D")
    gradient_card(img,(M+half+16,y,W-M,y+278),"#20443B","#152D29")
    d=ImageDraw.Draw(img)
    time_data=[
        (_t(labels,"moving_time"),_fmt_time(metrics["moving_time"]),lang),
        (_t(labels,"stopped"),_fmt_time(metrics["stopped_time"]),lang),
        (_t(labels,"avg_speed_total"),_fmt_speed(metrics["avg_speed_total"]),lang),
        (_t(labels,"max_speed"),_fmt_speed(metrics["max_speed"]),lang),
    ]
    draw_times_card(d,M,y,half,278,time_data)
    rx=M+half+16
    draw_slope_ratios_card(d, rx, y, half, 278, metrics, labels)
    # Distribution & slope detail, use the existing validated bin data
    y=1325
    d=ImageDraw.Draw(img)
    draw_slope_distribution_card(d, M, y, INNER, 150, metrics, lang)
    y=1492
    d=ImageDraw.Draw(img)
    # Three cards on the same row: climb | flat | descent.
    gap = 10
    center_w = 240
    side_w = (INNER - center_w - 2*gap)//2
    draw_grade_analysis_card(d, M, y, side_w, 258,
                             metrics.get("uphill_table"), metrics.get("uphill_distance_km"),
                             "up", lang)
    draw_flat_sections_card(d, M+side_w+gap, y, center_w, 258, metrics, lang)
    draw_grade_analysis_card(d, M+side_w+gap+center_w+gap, y, side_w, 258,
                             metrics.get("downhill_table"), metrics.get("downhill_distance_km"),
                             "down", lang)
    # Footer cards sit below the three-column grade analysis, without overlap.
    # Keep the analytical values sourced from metrics; never recompute them here.
    y = 1770
    footer_gap = 16
    footer_left_w = (INNER - footer_gap) // 2
    footer_right_x = M + footer_left_w + footer_gap
    footer_right_w = INNER - footer_left_w - footer_gap
    d = ImageDraw.Draw(img)
    draw_extreme_grades_card(d, M, y, footer_left_w, 240, metrics, lang)

    # Preserve the previously displayed start/end altitude information in the
    # right-hand footer area until its dedicated card is redesigned.
    d.rounded_rectangle((footer_right_x, y, footer_right_x + footer_right_w,
                         y + 240), radius=22, fill="#14251B")
    txt(d, footer_right_x + 24, y + 24,
        "ALTITUD" if lang.startswith("es") else "ALTITUDE", 22, TEXT, True)
    txt(d, footer_right_x + 24, y + 91,
        f"{_fmt_m(metrics['elevation_start_m'])} → {_fmt_m(metrics['elevation_end_m'])}",
        27, TEXT, True)
    footer_landscape(img)
    d = ImageDraw.Draw(img)
    txt(d, M, H - 66,
        f"{_t(labels, 'footer')}  ·  {metrics['point_count']} {_t(labels, 'gps_points')}",
        19, MUTED)
    out=Path(output_path)
    out.parent.mkdir(parents=True,exist_ok=True)
    img.save(out)
