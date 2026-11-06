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
W, H = WIDTH, HEIGHT
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


def slope_distribution(d,x,y,width,metrics):
    ups=list(metrics.get("uphill_table") or [])
    downs=list(metrics.get("downhill_table") or [])
    values=[(_pct(row.get("route_pct")),SLOPE_UP[i],str(row.get("label",""))) for i,row in enumerate(ups[:4])]
    values.append((_pct(metrics.get("flat_ratio_pct")),NEUTRAL,"< 1%"))
    values += [(_pct(row.get("route_pct")),SLOPE_DOWN[i],str(row.get("label",""))) for i,row in enumerate(downs[:4])]
    total=sum(v for v,_,_ in values)
    if total<=0:
        return
    cursor=x
    for v,color,label in values:
        sw=width*v/total
        if sw>1:
            d.rounded_rectangle((int(cursor),y,int(cursor+sw),y+27),radius=3,fill=color)
        if sw>43:
            txt(d,cursor+sw/2,y+4,f"{v:.1f}%",13,"#FFFFFF",True,anchor="mt")
            txt(d,cursor+sw/2,y+34,label,13,MUTED,anchor="mt")
        cursor+=sw


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
    txt(d,W-M-27,628,
        f"+{_fmt_m(metrics['elevation_gain_m'])}   /   -{_fmt_m(metrics['elevation_loss_m'])}",
        21,GREEN,True,anchor="ra")
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
    title(d,M+24,y+21,_t(labels,"times_and_speeds"))
    time_data=[
        (_t(labels,"moving_time"),_fmt_time(metrics["moving_time"])),
        (_t(labels,"stopped"),_fmt_time(metrics["stopped_time"])),
        (_t(labels,"avg_speed_total"),_fmt_speed(metrics["avg_speed_total"])),
        (_t(labels,"max_speed"),_fmt_speed(metrics["max_speed"])),
    ]
    for i,(lab,val) in enumerate(time_data):
        xx=M+24+(i%2)*226
        yy=y+85+(i//2)*91
        _metric(d,xx,yy,lab,val,TEXT,26)
    rx=M+half+16
    title(d,rx+24,y+21,_t(labels,"slope_ratios"))
    ring(d,rx+135,y+144,48,metrics["uphill_ratio_pct"],GREEN)
    ring(d,rx+350,y+144,48,metrics["downhill_ratio_pct"],ORANGE)
    txt(d,rx+135,y+207,_t(labels,"uphill_ratio").upper(),14,MUTED,True,anchor="mt")
    txt(d,rx+350,y+207,_t(labels,"downhill_ratio").upper(),14,MUTED,True,anchor="mt")
    line(d,[(rx+24,y+234),(W-M-24,y+234)])
    txt(d,rx+24,y+240,f"+ {_f(metrics['ascent_per_km'],1,' m/km')}",24,GREEN,True)
    txt(d,rx+260,y+240,f"− {_f(metrics['descent_per_km'],1,' m/km')}",24,ORANGE,True)
    # Distribution & slope detail, use the existing validated bin data
    y=1325
    gradient_card(img,(M,y,W-M,y+150),"#1D4235","#15342B")
    d=ImageDraw.Draw(img)
    title(d,M+24,y+16,"Distribución de pendientes" if lang.startswith("es") else "Slope distribution")
    slope_distribution(d,M+24,y+65,INNER-48,metrics)
    y=1492
    gradient_card(img,(M,y,M+half,y+260),"#204334","#153128")
    gradient_card(img,(M+half+16,y,W-M,y+260),"#24413A","#183029")
    d=ImageDraw.Draw(img)
    title(d,M+24,y+18,_t(labels,"uphill_analysis"))
    title(d,M+half+40,y+18,_t(labels,"downhill_analysis"))
    _draw_slope_rows(d,M+24,y+74,metrics["uphill_table"],GREEN)
    _draw_slope_rows(d,M+half+40,y+74,metrics["downhill_table"],ORANGE)
    txt(d,M+half-22,y+25,f"{metrics['uphill_distance_km']:.2f} km",20,GREEN,True,anchor="ra")
    txt(d,W-M-22,y+25,f"{metrics['downhill_distance_km']:.2f} km",20,ORANGE,True,anchor="ra")
    # Compact final data, preserving extreme grades and endpoints
    y=1770
    line(d,[(M,y),(W-M,y)])
    txt(d,M,y+15,"PENDIENTES" if lang.startswith("es") else "GRADES",17,MUTED,True)
    txt(d,M,y+47,f"↑ {_grade(metrics['max_up_grade_pct'])}",27,GREEN,True)
    txt(d,M+180,y+47,f"↓ {_grade(metrics['max_down_grade_pct'])}",27,ORANGE,True)
    txt(d,M+430,y+15,"ALTITUD" if lang.startswith("es") else "ALTITUDE",17,MUTED,True)
    txt(d,M+430,y+47,f"{_fmt_m(metrics['elevation_start_m'])} → {_fmt_m(metrics['elevation_end_m'])}",27,TEXT,True)
    footer_landscape(img)
    d=ImageDraw.Draw(img)
    txt(d,M,1854,f"{_t(labels,'footer')}  ·  {metrics['point_count']} {_t(labels,'gps_points')}",19,MUTED)
    out=Path(output_path)
    out.parent.mkdir(parents=True,exist_ok=True)
    img.save(out)
