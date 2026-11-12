"""Outdoor Minimal: deterministic Pillow renderer, presentation only.

No calculations are performed here; every number comes from analytics.metrics.
The original canvas renderer remains available for other themes.
"""
from __future__ import annotations

from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

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
W, H = 1080, 1920
M = 40
GAP = 16
TOP_MARGIN = 0
BOTTOM_MARGIN = 0
ROW_HEIGHTS = (220, 100, 35, 462, 230, 150, 260, 200, 135)
assert TOP_MARGIN + BOTTOM_MARGIN + sum(ROW_HEIGHTS) + GAP * (len(ROW_HEIGHTS) - 1) == H
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



ANALYSIS_BG = "#112217"
ANALYSIS_BORDER = "#3C4A41"  # white at 18% over #112217
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

    hd.rounded_rectangle((0, 0, sc(w)-1, sc(h)-1), radius=sc(23), fill=ANALYSIS_BG, outline=ANALYSIS_BORDER, width=sc(1))
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
    cell_size = 15 if w < 400 else 16
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
        yy = 112 + i * ((h - 32 - 112) / 3)
        dot_color = row.get("dot_color") or palette[i]
        label = row.get("label", "")
        # Anchor 'lt' positions the visible top of the glyphs at yy.
        # Center the accent dot against that glyph box, not a guessed offset.
        bounds = hd.textbbox((0, 0), str(label), font=f(cell_size), anchor="lt")
        glyph_height = (bounds[3] - bounds[1]) / S
        dot_center = yy + glyph_height / 2
        dot_radius = 4.5
        hd.ellipse((sc(pad), sc(dot_center-dot_radius),
                    sc(pad+9), sc(dot_center+dot_radius)), fill=dot_color)
        write(pad+15, yy, label, cell_size)
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
    hd.rounded_rectangle((0, 0, w*S-1, h*S-1), radius=23*S,
                         fill=ANALYSIS_BG, outline=ANALYSIS_BORDER, width=S)
    # Low-contrast meadow / level-path watermark, drawn behind all text.
    # Use restrained colors close to the panel background; no metric data.
    horizon = "#192D1E"
    contour = "#1C3524"
    hd.polygon([(12*S, 214*S), (48*S, 204*S), (83*S, 211*S),
                (123*S, 199*S), (160*S, 206*S), (205*S, 198*S),
                ((w-12)*S, 208*S), ((w-12)*S, (h-15)*S),
                (12*S, (h-15)*S)], fill=horizon)
    for offset in (0, 12, 24):
        points = [(16*S, (214+offset)*S), (52*S, (208+offset)*S),
                  (96*S, (215+offset)*S), (141*S, (209+offset)*S),
                  (194*S, (213+offset)*S), ((w-16)*S, (208+offset)*S)]
        hd.line(points, fill=contour, width=S)
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


def scenic_header(img, height=220):
    """Cover-crop the header photo and shade its lower half for readable text."""
    if not 220 <= height <= 320:
        raise ValueError("Header height must be between 220 and 320 px")
    asset = ASSET_DIR / "mountain-header.jpg"
    with Image.open(asset) as source:
        scene = ImageOps.fit(source.convert("RGB"), (W, height),
                             method=Image.Resampling.LANCZOS,
                             centering=(0.5, 0.5)).convert("RGBA")
    # A transparent-to-dark green gradient confined to the lower half.
    overlay = Image.new("RGBA", (1, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for yy in range(height // 2, height):
        fraction = (yy - height // 2) / max(1, height - height // 2 - 1)
        od.point((0, yy), fill=(7, 23, 20, round(210 * fraction)))
    overlay = overlay.resize((W, height))
    scene = Image.alpha_composite(scene, overlay)
    img.paste(scene.convert("RGB"), (0, 0))


def _header_title_lines(draw, raw_title, max_width=INNER, size=38):
    """Remove Wikiloc prefix and fit at most two measured lines with '...' truncation."""
    clean = str(raw_title or "").strip()
    if clean.startswith("Wikiloc - "):
        clean = clean[len("Wikiloc - "):].strip()
    font_obj = font(size, True)
    words = clean.split()
    lines = []
    current = ""
    for index, word in enumerate(words):
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=font_obj) <= max_width:
            current = candidate
            continue
        if len(lines) == 1:
            # Include the overflowing word in the truncated second line.
            remaining = (current + " " + " ".join(words[index:])).strip()
            while remaining and draw.textlength(remaining + "...", font=font_obj) > max_width:
                remaining = remaining[:-1]
            return [lines[0], remaining.rstrip() + "..."]
        if current:
            lines.append(current)
            current = word
        else:
            # An individual word can exceed the available width.
            remaining = word
            while remaining and draw.textlength(remaining + "...", font=font_obj) > max_width:
                remaining = remaining[:-1]
            return [remaining.rstrip() + "..."]
    if current:
        lines.append(current)
    return lines[:2]


def footer_landscape(img, point_count, lang="es", background_path=None, top=None, height=100):
    """Natural continuous mountain landscape; 2x supersampling, no anisotropic scaling.

    Fits the allocated bottom band below the footer cards. The supplied optional
    image uses aspect-preserving cover/crop. The generated scene is deterministic.
    """
    import random
    from PIL import ImageOps

    scale = 2
    width = W
    sw, sh = width * scale, height * scale
    top = img.height - height if top is None else top
    scene = Image.new("RGB", (sw, sh), "#14251B")
    d = ImageDraw.Draw(scene)
    rng = random.Random(67421)

    if background_path is not None:
        with Image.open(background_path) as source:
            scene = ImageOps.fit(source.convert("RGB"), (sw, sh),
                                 method=Image.Resampling.LANCZOS,
                                 centering=(0.5, 0.5))
        scene = Image.blend(scene, Image.new("RGB", (sw, sh), "#14251B"), 0.32)
        d = ImageDraw.Draw(scene)
    else:
        # Full-height atmospheric gradient, drawn at the final 2x canvas ratio.
        for y in range(sh):
            t = y / max(1, sh - 1)
            t = t * t * (3 - 2 * t)
            c0, c1 = (15, 31, 23), (54, 79, 62)
            d.line((0, y, sw, y), fill=tuple(round(a*(1-t)+b*t) for a,b in zip(c0,c1)))

        # Continuous asymmetric ridge: broad distant shoulders on the left,
        # one dominant rugged summit at ~76% of the width, no cloned triangles.
        anchors = [(0,.63),(.10,.61),(.20,.56),(.30,.61),(.39,.51),
                   (.48,.56),(.56,.45),(.64,.49),(.71,.36),(.765,.19),
                   (.80,.30),(.84,.36),(.89,.48),(.95,.43),(1,.53)]
        def ridge_at(x):
            u=x/sw
            for i in range(len(anchors)-1):
                u0,v0=anchors[i]; u1,v1=anchors[i+1]
                if u <= u1:
                    f=max(0,min(1,(u-u0)/(u1-u0)))
                    base=v0+(v1-v0)*f
                    # Small-scale irregularity, vanishing near the left text area.
                    detail=(.011*math.sin(u*91)+.006*math.sin(u*183+1.4))*(.35+.65*u)
                    return round(sh*(base+detail))
            return round(sh*anchors[-1][1])
        ridge=[(x,ridge_at(x)) for x in range(0,sw+1,3)]
        d.polygon(ridge+[(sw,sh),(0,sh)],fill="#526E5C")
        # Terrain facet under the dominant summit, integrated with the ridge.
        peak_x=int(sw*.765); peak_y=ridge_at(peak_x)
        d.polygon([(peak_x,peak_y),(int(sw*.68),ridge_at(int(sw*.68))),
                   (int(sw*.73),int(sh*.64)),(int(sw*.81),int(sh*.79)),
                   (int(sw*.805),ridge_at(int(sw*.805)))],fill="#718B77")
        d.polygon([(peak_x,peak_y),(int(sw*.805),ridge_at(int(sw*.805))),
                   (int(sw*.89),int(sh*.75)),(int(sw*.82),int(sh*.68))],fill="#354E40")
        # Broken rock/snow facets, not a flat white triangular cap.
        d.polygon([(peak_x,peak_y),(peak_x-42,peak_y+32),
                   (peak_x-17,peak_y+23),(peak_x+9,peak_y+47),
                   (peak_x+28,peak_y+26)],fill="#DCE8D8")
        d.polygon([(peak_x+28,peak_y+26),(peak_x+9,peak_y+47),
                   (peak_x+55,peak_y+68),(peak_x+75,peak_y+84)],fill="#90A897")
        # A smaller connected rocky shoulder, mostly shadowed.
        shoulder=int(sw*.56); sy=ridge_at(shoulder)
        d.polygon([(shoulder,sy),(shoulder-24,sy+27),
                   (shoulder+8,sy+16),(shoulder+37,sy+37)],fill="#A5B9A7")

        # Layered, smooth continuous foothills, without horizontal baselines.
        for base,amp,freq,color,phase in [(.70,.050,2.5,"#304B39",.4),
                                           (.79,.042,3.3,"#203A2B",1.6),
                                           (.88,.038,4.1,"#152B20",2.1)]:
            curve=[]
            for x in range(0,sw+1,4):
                u=x/sw
                y=sh*(base+amp*math.sin(2*math.pi*freq*u+phase)
                      +.012*math.sin(2*math.pi*7.1*u+phase*.8))
                curve.append((x,round(y)))
            d.polygon(curve+[(sw,sh),(0,sh)],fill=color)

        # Dense overlapping conifers in three depth planes, 140+ varied trees.
        # Their trunks terminate below the canvas; no flat dark strip at bottom.
        for layer, count, bottom, color, hmin,hmax in [
            (0,56,.98,"#1B3326",22,61),
            (1,65,1.06,"#11261B",30,84),
            (2,76,1.12,"#0B1610",40,103),
        ]:
            positions=sorted(rng.uniform(-25,sw+25) for _ in range(count))
            for x in positions:
                h=rng.uniform(hmin,hmax)
                by=sh*bottom+rng.uniform(-8,13)
                tip=by-h
                trunk=max(2.0,h*.045)
                d.rectangle((x-trunk,tip+h*.35,x+trunk,by+8),fill=color)
                # Overlapping tapered foliage tiers, varying crown shape.
                for j in range(3):
                    y=tip+j*h*.21
                    spread=h*(.16+j*.062)*rng.uniform(.88,1.16)
                    d.polygon([(x,y),(x-spread,y+h*.49),
                               (x+spread,y+h*.49)],fill=color)

    # Dedicated subtle text-safe gradient on the LEFT only. No stretch, no crop
    # after text drawing, and the text is always drawn on the 2x canvas.
    veil=Image.new("RGBA",(sw,sh),(0,0,0,0))
    vd=ImageDraw.Draw(veil)
    for x in range(int(sw*.65)):
        a=round(115*(1-x/(sw*.65))**1.8)
        vd.line((x,0,x,int(sh*.43)),fill=(8,23,16,a))
    scene=Image.alpha_composite(scene.convert("RGBA"),veil)
    d=ImageDraw.Draw(scene)
    label="Análisis técnico de ruta" if lang=="es" else "Technical route analysis"
    suffix="puntos GPS" if lang=="es" else "GPS points"
    caption=f"{label} · {point_count} {suffix}"
    fonts=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf"]
    font_path=next((f for f in fonts if Path(f).is_file()),None)
    text_font=ImageFont.truetype(font_path, 19*scale) if font_path else _font(19*scale)
    d.text((40*scale,25*scale),caption,font=text_font,fill="#E4F0E3",
           stroke_width=0)
    scene=scene.convert("RGB").resize((width,height),Image.Resampling.LANCZOS)
    img.paste(scene,(0,top))


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
    hd.rounded_rectangle((0, 0, xy(w)-1, xy(h)-1), radius=xy(23),
                         fill="#112217", outline=(255, 255, 255, 46), width=xy(1))
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
    bar_x, bar_y, bar_w, bar_h = 19, 53, w-38, 44
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
                                           radius=xy(22), fill=255)
    layer.paste(bar, (xy(bar_x), xy(bar_y)), mask)
    for (fraction, label, color, fg), center in zip(bins, centers):
        segment_width = fraction * bar_w
        pct_text = f"{fraction*100:.1f}%"
        # Only draw text where it fits; never let one percentage bleed into another bin.
        font = _distribution_font(xy(16), True)
        if segment_width*S >= hd.textlength(pct_text, font=font) + xy(7):
            text_at(center, bar_y+bar_h/2, pct_text, 16, "#1C2833" if color == "#F4D03F" else "#FFFFFF", True)
        # Labels remain centered on the exact segment centers; omit when too narrow.
        label_font = _distribution_font(xy(13))
        if segment_width*S >= hd.textlength(label, font=label_font) + xy(4):
            text_at(center, 110, label, 13, "#CFD8CC")
    text_at(19, 137, "▲  SUBIDA FUERTE", 13, "#F4D03F", True, "lm")
    text_at(w-19, 137, "BAJADA FUERTE  ▼", 13, "#FA6D4B", True, "rm")
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
        "bold": ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",),
        "semibold": ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",),
        "regular": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",),
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
    """Draw the four metrics at their final pixel size, without stretching text."""
    heading = ("Tiempos y velocidades" if str(labels_and_values[0][2]).startswith("es")
               else "Times & speeds")
    # Match the elevation profile: forest background and 18% white outline.
    forest = (17, 34, 23)
    border = tuple(round(c * .82 + 255 * .18) for c in forest)
    d.rounded_rectangle((x, y, x + width - 1, y + height - 1),
                        radius=23, fill="#112217", outline=border, width=1)
    _time_card_icon(d, x + 20, y + 16, "stopwatch", size=28)
    _time_text(d, (x + 58, y + 18), heading, 20, "#FFFFFF", "bold")

    pad = 16
    top = y + 35
    bottom = y + height - 12
    mid_x = x + width / 2
    mid_y = (top + bottom) / 2
    d.line([(round(mid_x), round(y + 53)), (round(mid_x), round(bottom))],
           fill=TIME_DIVIDER_COLOR, width=1)
    d.line([(round(x + pad), round(mid_y)), (round(x + width - pad), round(mid_y))],
           fill=TIME_DIVIDER_COLOR, width=1)

    col_width = width / 2
    row_height = (bottom - top) / 2
    icon_size = 30
    gap = 13
    for i, (label, value, _) in enumerate(labels_and_values):
        col, row = i % 2, i // 2
        left = x + col * col_width
        center_y = top + (row + .5) * row_height
        icon_x = left + 13
        text_x = icon_x + icon_size + gap
        available = left + col_width - 8 - text_x
        label = _time_label(label)
        label_size = 13
        while label_size > 10 and d.textlength(label, font=_time_font(label_size, "bold")) > available:
            label_size -= 1
        value_size = 26
        while value_size > 18 and d.textlength(str(value), font=_time_font(value_size, "bold")) > available:
            value_size -= 1
        label_font = _time_font(label_size, "bold")
        value_font = _time_font(value_size, "bold")
        label_h = d.textbbox((0, 0), label, font=label_font, anchor="lt")[3]
        value_h = d.textbbox((0, 0), str(value), font=value_font, anchor="lt")[3]
        spacing = 8
        text_top = center_y - (label_h + spacing + value_h) / 2
        _time_card_icon(d, icon_x, center_y - icon_size / 2,
                        ("runner", "pause", "gauge", "gauge_max")[i], size=icon_size)
        d.text((round(text_x), round(text_top)), label, font=label_font,
               fill=TIME_LABEL_COLOR, anchor="lt")
        d.text((round(text_x), round(text_top + label_h + spacing)), str(value),
               font=value_font, fill=TIME_VALUE_COLOR, anchor="lt")


SLOPE_CARD_BG = "#112217"
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
    # Forest background and subtle 18% white perimeter, matching the times card.
    forest = (17, 34, 23)
    border = tuple(round(c * .82 + 255 * .18) for c in forest)
    d.rounded_rectangle((x, y, x + width - 1, y + height - 1), radius=23,
                        fill=SLOPE_CARD_BG, outline=border, width=1)
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
           fill=TIME_DIVIDER_COLOR, width=1)
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



def draw_altitude_card(d, x, y, width, height, metrics, lang="es"):
    """Right footer card: start/end altitude, rendered at 2x without metric mutation."""
    from io import BytesIO
    import cairosvg

    scale = 2
    w, h = round(width), round(height)
    layer = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    def px(n):
        return round(n * scale)
    def f(size, bold=False):
        return _time_font(px(size), "bold" if bold else "regular")

    draw.rounded_rectangle((0, 0, px(w)-1, px(h)-1), radius=px(22), fill="#14251B")
    # The same official Lucide 'layers' paths used in the slope distribution card.
    icon_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                'fill="none" stroke="#E6EBD9" stroke-width="1.8" '
                'stroke-linecap="round" stroke-linejoin="round">'
                '<path d="m12.83 2.18 8 4a2 2 0 0 1 0 3.58l-8 4a2 2 0 0 1-1.66 0l-8-4a2 2 0 0 1 0-3.58l8-4a2 2 0 0 1 1.66 0Z"/>'
                '<path d="m2 12 9.17 4.59a2 2 0 0 0 1.66 0L22 12M2 17l9.17 4.59a2 2 0 0 0 1.66 0L22 17"/>'
                '</svg>')
    icon = Image.open(BytesIO(cairosvg.svg2png(bytestring=icon_svg.encode("utf-8"),
                     output_width=px(26), output_height=px(26)))).convert("RGBA")
    layer.alpha_composite(icon, (px(19), px(15)))
    heading = "Altitud" if lang.startswith("es") else "Altitude"
    draw.text((px(58), px(18)), heading, font=f(19, True), fill="#FFFFFF")

    # Two balanced columns: prominent altitude above its descriptive label.
    # A centered separator replaces the old horizontal row divider.
    mid = w / 2
    draw.line((px(mid), px(76), px(mid), px(h - 24)),
              fill=(255, 255, 255, 31), width=scale)
    columns = [
        ("Altura inicio" if lang.startswith("es") else "Start altitude",
         metrics.get("elevation_start_m"), "#D2DFD0", "#64B5F6", w / 4),
        ("Altura fin" if lang.startswith("es") else "End altitude",
         metrics.get("elevation_end_m"), "#F5B041", "#F5B041", 3 * w / 4),
    ]
    for label, value, dot_color, value_color, cx in columns:
        value_text = "N/D" if value is None else f"{int(round(value)):,} m"
        value_size = 29
        label_size = 18
        max_text_width = w / 2 - 42
        while value_size > 18 and draw.textlength(value_text, font=f(value_size, True)) > px(max_text_width):
            value_size -= 1
        while label_size > 13 and draw.textlength(label, font=f(label_size, True)) > px(max_text_width - 18):
            label_size -= 1
        draw.text((px(cx), px(123)), value_text, font=f(value_size, True),
                  fill=value_color, anchor="mm")
        label_width = draw.textlength(label, font=f(label_size, True)) / scale
        dot_radius = 5
        gap = 12
        group_width = dot_radius * 2 + gap + label_width
        left = cx - group_width / 2
        draw.ellipse((px(left), px(181-dot_radius), px(left+dot_radius*2), px(181+dot_radius)),
                     fill=dot_color)
        draw.text((px(left+dot_radius*2+gap), px(181)), label,
                  font=f(label_size, True), fill="#FFFFFF", anchor="lm")
    layer = layer.resize((w, h), Image.Resampling.LANCZOS)
    d._image.paste(layer, (round(x), round(y)), layer)


def _draw_scaled_card(img, painter, x, y, width, height, native_height, *args):
    """Preserve existing card internals; fit their native rendering to a layout row."""
    layer = Image.new("RGB", (int(width), int(native_height)), BG)
    if painter is draw_times_card:
        gradient_card(layer, (0, 0, width, native_height), "#244D3A", "#19362D")
    elif painter is draw_slope_ratios_card:
        gradient_card(layer, (0, 0, width, native_height), "#20443B", "#152D29")
    painter(ImageDraw.Draw(layer), 0, 0, int(width), int(native_height), *args)
    if native_height != height:
        layer = layer.resize((int(width), int(height)), Image.Resampling.LANCZOS)
    img.paste(layer, (int(x), int(y)))


def draw_elevation_profile_card(img, x, y, width, height, metrics, labels,
                                chart_path=None, lang="es"):
    """Render the elevation profile and its three anchored callouts in Pillow.

    The input series and ascent/descent metrics are used unchanged. When the
    series is absent, the existing chart asset remains the fallback.
    """
    from PIL import ImageChops

    w, h = int(width), int(height)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=25,
                        fill="#112217", outline=(255, 255, 255, 46), width=1)
    d.text((26, 21), _t(labels, "elevation_profile"),
           font=font(27, True), fill="#F0F1E3")

    def pill(bx, by, label, accent, bg, border):
        bw, bh = 161, 49
        d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=22,
                            fill=bg, outline=border, width=1)
        d.text((bx + bw / 2, by + bh / 2), label,
               font=font(20, True), fill=accent, anchor="mm")

    def fmt_signed(value, prefix):
        return prefix + (_fmt_m(value) if value is not None else "N/D")

    pill(w - 352, 13, "↑ " + fmt_signed(metrics.get("elevation_gain_m"), "+"),
         "#A3E635", "#1D3824", "#567C3C")
    pill(w - 179, 13, "↓ " + fmt_signed(metrics.get("elevation_loss_m"), "-"),
         "#FA6D4B", "#392621", "#805044")

    distances = metrics.get("distance_series_km") or []
    elevations = metrics.get("elevation_series_m") or []
    pairs = [(float(km), float(z)) for km, z in zip(distances, elevations)
             if km is not None and z is not None and math.isfinite(float(km))
             and math.isfinite(float(z))]
    left, right = 125, w - 30
    top, bottom = 116, h - 52
    if len(pairs) < 2 or pairs[-1][0] <= pairs[0][0]:
        if chart_path:
            with Image.open(chart_path) as src:
                chart = src.convert("RGBA")
                chart.thumbnail((right - left, bottom - top), Image.Resampling.LANCZOS)
                layer.alpha_composite(chart, (left + (right-left-chart.width)//2,
                                               top + (bottom-top-chart.height)//2))
    else:
        zmin = min(z for _, z in pairs)
        zmax = max(z for _, z in pairs)
        span = max(1.0, zmax - zmin)
        # Headroom is reserved for the peak label; plot remains tall.
        floor = zmin - span * .10
        ceiling = zmax + span * .23
        xmin, xmax = pairs[0][0], pairs[-1][0]
        def xy(km, z):
            return (left + (km - xmin) / (xmax - xmin) * (right-left),
                    bottom - (z - floor) / (ceiling-floor) * (bottom-top))
        coords = [xy(km, z) for km, z in pairs]
        for j in range(4):
            yy = top + (bottom-top)*j/3
            d.line((left, yy, right, yy), fill=(128, 169, 116, 38), width=1)
        # A clipped alpha mask ensures the fill vanishes at the chart baseline.
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        md.polygon(coords + [(right, bottom), (left, bottom)], fill=255)
        gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gradient)
        for yy in range(top, bottom + 1):
            alpha = round(122 * (1 - (yy-top)/max(1,bottom-top))**1.2)
            gd.line((left, yy, right, yy), fill=(163, 230, 53, alpha))
        gradient.putalpha(ImageChops.multiply(gradient.getchannel("A"), mask))
        layer.alpha_composite(gradient)
        d = ImageDraw.Draw(layer)
        d.line(coords, fill="#C6F135", width=3, joint="curve")

        # Distance ticks and axis caption occupy the final 35 px of the card.
        for i in range(5):
            xx = left + (right-left)*i/4
            d.text((xx, bottom + 7), f"{xmin+(xmax-xmin)*i/4:.1f}",
                   font=font(14), fill="#B9CDAF", anchor="mt")
        axis_name = "Distancia (km)" if lang.startswith("es") else "Distance (km)"
        d.text((w/2, h-15), axis_name, font=font(16),
               fill="#D1E1C4", anchor="mm")

        def callout(point, value, kind):
            cx, cy = point
            label = ("▲ " if kind == "peak" else "") + f"{round(value):,} m"
            fnt = font(18, True)
            tw = d.textbbox((0,0), label, font=fnt)[2]
            bw, bh = tw + 25, 35
            if kind == "start":
                bx = cx + 15
            elif kind == "end":
                bx = cx - bw - 15
            else:
                bx = cx - bw/2
            bx = max(8, min(w-bw-8, bx))
            by = max(72, cy - bh - 19)
            # Keep callouts from colliding with the upper stat pills.
            by = max(75, by)
            anchor_x = bx + (8 if kind == "start" else bw-8 if kind == "end" else bw/2)
            d.line((anchor_x, by+bh, cx, cy), fill=(240, 246, 229, 190), width=1)
            d.rounded_rectangle((bx, by, bx+bw, by+bh), radius=9,
                                fill="#16281D", outline=(255,255,255,65), width=1)
            d.text((bx+bw/2, by+bh/2), label, font=fnt,
                   fill="#F5F5E8", anchor="mm")
            d.ellipse((cx-5,cy-5,cx+5,cy+5), fill="#FFFFFF")

        peak_idx = max(range(len(pairs)), key=lambda i: pairs[i][1])
        # Paint peak first so endpoint labels stay legible on short routes.
        callout(coords[peak_idx], pairs[peak_idx][1], "peak")
        callout(coords[0], pairs[0][1], "start")
        callout(coords[-1], pairs[-1][1], "end")

        # Draw the altitude axis last so its labels remain above the fill.
        axis_color = "#DDE8D2"
        d.line((left, top, left, bottom), fill=(198, 225, 184, 180), width=2)
        for i in range(5):
            altitude = floor + (ceiling - floor) * i / 4
            tick_y = bottom - (bottom - top) * i / 4
            d.line((left - 7, tick_y, left, tick_y), fill=axis_color, width=2)
            d.text((left - 13, tick_y), f"{altitude:,.0f}",
                   font=font(18, True), fill=axis_color, anchor="rm")
        d.text((left - 8, top - 24), "ALTITUD (m)" if lang.startswith("es")
               else "ELEVATION (m)", font=font(15, True),
               fill=axis_color, anchor="rm")

    # Border last: remains crisp over gradient, grid, and profile.
    d.rounded_rectangle((0, 0, w-1, h-1), radius=25,
                        outline=(255, 255, 255, 46), width=1)
    img.paste(layer, (round(x), round(y)), layer)


def render_outdoor_story(metadata, metrics, chart_path, output_path, lang="es"):
    labels = _load_i18n(lang)
    img = Image.new("RGB", (W, H), BG)
    y_cursor = TOP_MARGIN

    # Header photo occupies 220 px; summary begins exactly one GAP below.
    scenic_header(img, ROW_HEIGHTS[0])
    d = ImageDraw.Draw(img)
    _tiny_icon(d, M, y_cursor + 8, "mountain", GREEN, 1.15)
    txt(d, M + 51, y_cursor + 9, "GPX  /  INSIGHT", 21, GREEN, True)
    date = _route_date_label(metadata, lang)
    txt(d, M, y_cursor + 62, date.upper(), 19, MUTED, True)
    name = metadata.get("name") or _t(labels, "unnamed_route")
    title_lines = _header_title_lines(d, name, INNER, 38)
    ty = y_cursor + 101
    for ln in title_lines:
        txt(d, M, ty, ln, 38, TEXT, True)
        ty += 50
    y_cursor += ROW_HEIGHTS[0] + GAP

    # Four summary tiles: use the full 100 px row.
    kpi_palette = [("#1D4D42", "#17382F"), ("#2B5738", "#1A382A"),
                   ("#654135", "#392D2B"), ("#23505A", "#17343C")]
    kpi_w = (INNER - 18) / 4
    for i, (top, bottom) in enumerate(kpi_palette):
        x = M + i * (kpi_w + 6)
        gradient_card(img, (x, y_cursor, x + kpi_w, y_cursor + ROW_HEIGHTS[1]), top, bottom, 18)
    d = ImageDraw.Draw(img)
    values = [
        (_t(labels, "total_distance"), _fmt_km(metrics["distance_km"]), TEXT, "distance"),
        (_t(labels, "ascent"), "+" + _fmt_m(metrics["elevation_gain_m"]), GREEN, "up"),
        (_t(labels, "descent"), "-" + _fmt_m(metrics["elevation_loss_m"]), ORANGE, "down"),
        (_t(labels, "total_time"), _fmt_time(metrics["total_time"]), TEXT, "clock"),
    ]
    col = kpi_w + 6
    for i, (lab, val, color, ico) in enumerate(values):
        center = M + i * col + kpi_w / 2
        _tiny_icon(d, center - 15, y_cursor + 5, ico, color, .75)
        txt(d, center, y_cursor + 41, lab.upper(), 15, TEXT, True, anchor="mt")
        txt(d, center, y_cursor + 65, val, 27, color, True, anchor="mt")
    y_cursor += ROW_HEIGHTS[1] + GAP

    # Start/end row.
    d = ImageDraw.Draw(img)
    txt(d, M + 12, y_cursor + 4, f"{_t(labels,'start')}: {_fmt_time(metrics['start_time'])}", 25, TEXT, True)
    txt(d, W - M - 12, y_cursor + 4, f"{_t(labels,'end')}: {_fmt_time(metrics['end_time'])}", 25, TEXT, True, anchor="ra")
    y_cursor += ROW_HEIGHTS[2] + GAP

    # Elevation profile is drawn from the existing metric series, without
    # recalculating elevation, distance, or any route statistics.
    draw_elevation_profile_card(img, M, y_cursor, INNER, ROW_HEIGHTS[3],
                                metrics, labels, chart_path, lang)
    y_cursor += ROW_HEIGHTS[3] + GAP

    # Two columns. Existing card painters are unchanged.
    half = (INNER - GAP) // 2
    time_data = [
        (_t(labels, "moving_time"), _fmt_time(metrics["moving_time"]), lang),
        (_t(labels, "stopped"), _fmt_time(metrics["stopped_time"]), lang),
        (_t(labels, "avg_speed_total"), _fmt_speed(metrics["avg_speed_total"]), lang),
        (_t(labels, "max_speed"), _fmt_speed(metrics["max_speed"]), lang),
    ]
    # Draw at native 230 px height: never resize the card anisotropically.
    draw_times_card(ImageDraw.Draw(img), M, y_cursor, half, ROW_HEIGHTS[4], time_data)
    rx = M + half + GAP
    _draw_scaled_card(img, draw_slope_ratios_card, rx, y_cursor, half, ROW_HEIGHTS[4], 278, metrics, labels)
    y_cursor += ROW_HEIGHTS[4] + GAP

    _draw_scaled_card(img, draw_slope_distribution_card, M, y_cursor, INNER,
                      ROW_HEIGHTS[5], 150, metrics, lang)
    y_cursor += ROW_HEIGHTS[5] + GAP

    # Three columns.
    center_w = 240
    side_w = (INNER - center_w - 2 * GAP) // 2
    _draw_scaled_card(img, draw_grade_analysis_card, M, y_cursor, side_w,
                      ROW_HEIGHTS[6], 258, metrics.get("uphill_table"),
                      metrics.get("uphill_distance_km"), "up", lang)
    _draw_scaled_card(img, draw_flat_sections_card, M + side_w + GAP, y_cursor,
                      center_w, ROW_HEIGHTS[6], 258, metrics, lang)
    _draw_scaled_card(img, draw_grade_analysis_card, M + side_w + GAP + center_w + GAP,
                      y_cursor, side_w, ROW_HEIGHTS[6], 258, metrics.get("downhill_table"),
                      metrics.get("downhill_distance_km"), "down", lang)
    y_cursor += ROW_HEIGHTS[6] + GAP

    # Bottom analytical cards.
    left_w = (INNER - GAP) // 2
    right_x = M + left_w + GAP
    _draw_scaled_card(img, draw_extreme_grades_card, M, y_cursor, left_w,
                      ROW_HEIGHTS[7], 240, metrics, lang)
    _draw_scaled_card(img, draw_altitude_card, right_x, y_cursor, INNER - left_w - GAP,
                      ROW_HEIGHTS[7], 240, metrics, lang)
    y_cursor += ROW_HEIGHTS[7] + GAP

    assert y_cursor == H - ROW_HEIGHTS[8], "Footer must begin at the bottom-anchored band"
    footer_landscape(img, metrics["point_count"], lang, top=y_cursor, height=ROW_HEIGHTS[8])
    y_cursor += ROW_HEIGHTS[8]
    assert y_cursor + BOTTOM_MARGIN == H
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
