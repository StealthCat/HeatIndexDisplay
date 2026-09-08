from __future__ import annotations
import html
import math
import time
from datetime import datetime
from .app_state import AppConfig, WeatherData
from .weather_math import (
    apparent_outdoor_f, apparent_risk_label, apparent_title,
    direction_text, wind_chill_applies
)
from .forecast_weather import forecast_shows_tomorrow

BLACK = "#000000"
WHITE = "#ffffff"
CYAN = "#72caff"
CARD_TEXT = "#d8ecfb"
MUTED = "#9fb7c9"
GREEN = "#75ed4f"
YELLOW = "#ffc12b"
RED = "#ff5c48"

def finite(v):
    return isinstance(v, (float, int)) and math.isfinite(v)

def fmt(v, decimals=1, suffix=""):
    return f"{v:.{decimals}f}{suffix}" if finite(v) else "--"

def signed_delta(v):
    if not finite(v):
        return "--"
    return f"{v:+.1f}°F"

def _defs():
    return '''
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#02080d"/>
        <stop offset="1" stop-color="#000203"/>
      </linearGradient>
      <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#071a28"/>
        <stop offset="0.55" stop-color="#061521"/>
        <stop offset="1" stop-color="#03101a"/>
      </linearGradient>
      <linearGradient id="cardHi" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#0a2638"/>
        <stop offset="1" stop-color="#04111b"/>
      </linearGradient>
      <linearGradient id="heroWarm" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#9a4016"/>
        <stop offset="0.45" stop-color="#6d290e"/>
        <stop offset="1" stop-color="#21140f"/>
      </linearGradient>
      <linearGradient id="heroCold" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#124f86"/>
        <stop offset="0.5" stop-color="#0a345e"/>
        <stop offset="1" stop-color="#071827"/>
      </linearGradient>
      <linearGradient id="riskWarm" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#44190f"/>
        <stop offset="1" stop-color="#2b120d"/>
      </linearGradient>
      <linearGradient id="riskCold" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#0d2c4b"/>
        <stop offset="1" stop-color="#081c31"/>
      </linearGradient>
      <filter id="sunGlow" x="-70%" y="-70%" width="240%" height="240%">
        <feGaussianBlur stdDeviation="2.2" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="0.65" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>'''

def text(x, y, value, size=8, anchor="start", color=WHITE, weight="400",
         letter_spacing=0, opacity=1.0):
    stroke = ""
    try:
        if int(weight) >= 800:
            stroke = f' stroke="{color}" stroke-width="0.14" paint-order="stroke fill"'
    except Exception:
        pass
    spacing = f' letter-spacing="{letter_spacing}"' if letter_spacing else ""
    return (
        f'<text x="{x}" y="{y}" fill="{color}"{stroke}{spacing} opacity="{opacity}" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" dominant-baseline="middle">{html.escape(str(value))}</text>'
    )

def card(x, y, w, h, r=7, highlight=False):
    fill = "url(#cardHi)" if highlight else "url(#card)"
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        f'fill="{fill}" stroke="#174e6c" stroke-width="1"/>'
    )

def _updated_text(wx: WeatherData):
    if not wx.date_utc_ms:
        return "--"
    dt = datetime.fromtimestamp(wx.date_utc_ms / 1000)
    return dt.strftime("%I:%M %p").lstrip("0")

def is_stale(cfg: AppConfig, wx: WeatherData):
    return bool(
        wx.valid
        and wx.date_utc_ms
        and ((time.time() * 1000 - wx.date_utc_ms) > cfg.stale_seconds * 1000)
    )

def icon(kind, x, y, scale=1.0):
    common = f'transform="translate({x} {y}) scale({scale})"'
    if kind == "temp":
        body = (
            '<rect x="8" y="1" width="5" height="12" rx="2.5" fill="none" '
            'stroke="#ff5c4b" stroke-width="2"/>'
            '<rect x="9.5" y="5" width="2" height="9" fill="#ff5c4b"/>'
            '<circle cx="10.5" cy="15" r="5" fill="#ff654e"/>'
            '<circle cx="10.5" cy="15" r="2" fill="#ff9b66"/>'
        )
    elif kind == "drop":
        body = (
            '<path d="M10 1 C8 5 4 9 4 13a6 6 0 0 0 12 0c0-4-4-8-6-12z" '
            'fill="#48baff" stroke="#83d7ff" stroke-width=".7"/>'
        )
    elif kind == "leaf":
        body = (
            '<ellipse cx="10" cy="10" rx="7" ry="5" fill="#7bdc47" '
            'transform="rotate(-35 10 10)"/>'
            '<path d="M4 16L16 4" stroke="#b6ff83" stroke-width="1.3"/>'
        )
    elif kind == "trend":
        body = (
            '<path d="M2 17V3M2 17H18M4 14L8 10L11 12L17 5" fill="none" '
            'stroke="#4bc3ff" stroke-width="2"/>'
            '<path d="M17 5l-3 0 3-3 3 3-3 0z" fill="#4bc3ff"/>'
        )
    elif kind == "wind":
        body = (
            '<path d="M2 6h13l-3-2m3 2-3 2M1 10h17l-3-2m3 2-3 2'
            'M4 14h13l-3-2m3 2-3 2" fill="none" stroke="#4bc3ff" stroke-width="2"/>'
        )
    elif kind == "compass":
        body = (
            '<circle cx="10" cy="10" r="8.5" fill="#071a27" stroke="#4bc3ff" stroke-width="1.8"/>'
            '<path d="M10 3L7 12l3-2 3 5z" fill="#dff7ff"/>'
            '<circle cx="10" cy="10" r="2" fill="#188abd"/>'
        )
    elif kind == "sun":
        body = (
            '<g filter="url(#sunGlow)">'
            '<circle cx="10" cy="10" r="5.4" fill="#ffbf2c" stroke="#ffda60" stroke-width=".8"/>'
            '<g stroke="#ffc33b" stroke-width="2"><path d="M10 0v3M10 17v3M0 10h3M17 10h3'
            'M3 3l2 2M15 15l2 2M3 17l2-2M15 5l2-2"/></g></g>'
        )
    elif kind == "clock":
        body = (
            '<circle cx="10" cy="10" r="7.5" fill="none" stroke="#a8c6d8" stroke-width="1.5"/>'
            '<path d="M10 5v5l4 2" fill="none" stroke="#d8ebf5" stroke-width="1.5" '
            'stroke-linecap="round"/>'
        )
    elif kind == "alert":
        body = (
            '<path d="M10 2L18 17H2z" fill="#ff765e"/>'
            '<rect x="9.2" y="7" width="1.6" height="5" rx=".8" fill="#3b120c"/>'
            '<circle cx="10" cy="14.3" r="1" fill="#3b120c"/>'
        )
    else:
        body = ""
    return f'<g {common}>{body}</g>'

def _hero_palette(wx: WeatherData):
    apparent = apparent_outdoor_f(wx)

    # NWS wind-chill/frostbite guide inspired progression used by production:
    # > -18F deep blue, <= -18F icy blue, <= -32F deeper blue, <= -48F purple.
    if wind_chill_applies(wx):
        if apparent <= -48.0:
            return {
                "top": "#6c3aa8", "bottom": "#1f0f43",
                "border": "#be84f2", "status": "#27124f",
                "accent": "#dbacff", "icon": "wind",
            }
        if apparent <= -32.0:
            return {
                "top": "#2569b8", "bottom": "#0a224e",
                "border": "#63abff", "status": "#091e43",
                "accent": "#8bc6ff", "icon": "wind",
            }
        if apparent <= -18.0:
            return {
                "top": "#4ea6da", "bottom": "#0d3d60",
                "border": "#9edfff", "status": "#0b304c",
                "accent": "#c2ebff", "icon": "wind",
            }
        return {
            "top": "#124f86", "bottom": "#06192c",
            "border": "#58b7ff", "status": "#081c31",
            "accent": "#7bc9ff", "icon": "wind",
        }

    # NWS HeatRisk color progression used as the production visual guide while
    # retaining the firmware's existing Heat Index thresholds and labels.
    if apparent >= 125.0:
        return {
            "top": "#b21585", "bottom": "#37082f",
            "border": "#f457cc", "status": "#4c0a40",
            "accent": "#ff8be4", "icon": "sun",
        }
    if apparent >= 103.0:
        return {
            "top": "#d83b35", "bottom": "#46110f",
            "border": "#ff7168", "status": "#52120e",
            "accent": "#ff8c82", "icon": "sun",
        }
    if apparent >= 90.0:
        return {
            "top": "#dd751d", "bottom": "#471e08",
            "border": "#ffad4b", "status": "#582307",
            "accent": "#ffc06e", "icon": "sun",
        }
    if apparent >= 80.0:
        return {
            "top": "#c59b17", "bottom": "#423207",
            "border": "#ffe45e", "status": "#5b4407",
            "accent": "#ffeb80", "icon": "sun",
        }
    return {
        "top": "#287a45", "bottom": "#0a2314",
        "border": "#61d889", "status": "#123a20",
        "accent": "#8fe8aa", "icon": "sun",
    }


def _hero_gradient_defs(style):
    return (
        '<defs>'
        '<linearGradient id="heroCurrent" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{style["top"]}"/>'
        f'<stop offset="1" stop-color="{style["bottom"]}"/>'
        '</linearGradient>'
        '<linearGradient id="riskCurrent" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{style["status"]}"/>'
        f'<stop offset="1" stop-color="{style["bottom"]}"/>'
        '</linearGradient>'
        '</defs>'
    )

def _apparent_parts(value, layout):
    """Render number, degree symbol and F as independently positioned text.

    The approved Concept 1 layout deliberately places the sun/wind icon at the
    upper-left of the hero panel and the apparent temperature lower/right.
    Explicit coordinates prevent the 3-digit value from colliding with the
    condition icon or pushing °F outside the panel.
    """
    value_s = str(value)

    if layout == "tdisplay":
        # Hero panel: x=8..162. Keep the full 100°F group in bounds.
        if len(value_s) >= 3:
            number_x, number_size = 94, 35
        else:
            number_x, number_size = 98, 38
        baseline = 98
        degree_x, degree_y, degree_size = 125, 84, 8
        f_x, f_y, f_size = 132, 98, 14
    else:
        # Hero panel: x=10..138. 3-digit values sit below the sun rather than
        # across it, while 2-digit values can use a little more size.
        if len(value_s) >= 3:
            number_x, number_size = 82, 42
        else:
            number_x, number_size = 88, 47
        baseline = 145
        degree_x, degree_y, degree_size = 117, 129, 9
        f_x, f_y, f_size = 123, 145, 16

    return "".join([
        text(number_x, baseline, value_s, number_size, "middle", WHITE, "900"),
        text(degree_x, degree_y, "°", degree_size, "start", WHITE, "900"),
        text(f_x, f_y, "F", f_size, "start", WHITE, "800"),
    ])

def _metric(out, x, y, w, h, kind, label, value, icon_scale=.62, label_size=4.8, value_size=8.0):
    out.append(card(x, y, w, h, 6))
    iy = y + (h - (20 * icon_scale)) / 2
    out.append(icon(kind, x + 5, iy, icon_scale))
    out.append(text(x + 25, y + 9, label, label_size, "start", CYAN, "700", .35))
    out.append(text(x + 25, y + 21, value, value_size, "start", WHITE, "900"))

def tdisplay_svg(cfg: AppConfig, wx: WeatherData, api_error: str = "",
                 forecast_elapsed_seconds: float | None = None) -> str:
    w, h = 170, 320
    station = (cfg.station_name or "Weather Station")[:18]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        _defs(),
        '<rect width="170" height="320" fill="url(#bg)"/>',
        text(8, 18, station, 14, "start", WHITE, "900"),
        '<line x1="8" y1="33" x2="20" y2="33" stroke="#7ec8e8" stroke-width=".7"/>',
        text(27, 33, "CURRENT CONDITIONS", 4.6, "start", "#9fbed1", "600", 1.25),
    ]

    if not wx.valid:
        out += [
            card(8, 48, 154, 95, 11, True),
            text(85, 84, "WAITING", 18, "middle", WHITE, "900"),
            text(85, 108, "Weather API error" if api_error else "Fetching weather...",
                 7.2, "middle", MUTED, "600"),
        ]
    else:
        apparent = int(round(apparent_outdoor_f(wx)))
        risk = _hero_palette(wx)
        out.append(_hero_gradient_defs(risk))

        out += [
            f'<rect x="8" y="43" width="154" height="101" rx="11" fill="url(#heroCurrent)" '
            f'stroke="{risk["border"]}" stroke-width="1"/>',
            icon(risk["icon"], 17, 70, 1.72),
            text(118, 59, apparent_title(wx), 9.0, "middle", WHITE, "800", .5),
            _apparent_parts(apparent, "tdisplay"),
            f'<rect x="16" y="116" width="138" height="20" rx="10" fill="url(#riskCurrent)" '
            f'stroke="{risk["accent"]}" stroke-width="1"/>',
            icon("alert", 30, 119, .55),
            text(90, 126, apparent_risk_label(wx), 6.8, "middle", risk["accent"], "900"),
        ]

        _metric(out, 7, 149, 77, 31, "temp", "TEMPERATURE",
                fmt(wx.temp_f, 1, "°F"), .62, 4.2, 8.1)
        _metric(out, 87, 149, 76, 31, "drop", "HUMIDITY",
                fmt(wx.humidity, 0, "%"), .62, 4.4, 8.1)
        _metric(out, 7, 183, 77, 31, "leaf", "DEW POINT",
                fmt(wx.dew_point_f, 1, "°F"), .62, 4.4, 8.1)
        _metric(out, 87, 183, 76, 31, "trend", "VS YDAY",
                signed_delta(wx.from_yesterday_f), .60, 4.4, 8.0)
        _metric(out, 7, 217, 77, 31, "wind", "W/G MPH",
                f"{fmt(wx.wind_mph,1)} / {fmt(wx.gust_mph,1)}", .60, 4.4, 7.2)
        _metric(out, 87, 217, 76, 31, "compass", "DIR",
                (f"{round(wx.wind_dir_deg):.0f}° {direction_text(wx.wind_dir_deg)}"
                 if finite(wx.wind_dir_deg) else "--"),
                .62, 4.4, 7.0)

        tomorrow = forecast_shows_tomorrow(wx, forecast_elapsed_seconds)
        fh = wx.forecast_tomorrow_high_f if tomorrow else wx.forecast_today_high_f
        fl = wx.forecast_tomorrow_low_f if tomorrow else wx.forecast_today_low_f
        forecast_label = "TOMORROW HIGH / LOW" if tomorrow else "TODAY HIGH / LOW"
        forecast_value = (
            f"{int(round(fh))}° / {int(round(fl))}°"
            if wx.forecast_valid and finite(fh) and finite(fl)
            else "-- / --"
        )
        out += [
            card(7, 252, 156, 35, 7, True),
            icon("sun", 13, 260, .72),
            text(40, 260, forecast_label, 4.7, "start", "#9dc8e4", "700", .45),
            text(40, 275, forecast_value, 10.6, "start", WHITE, "900"),
        ]

    out += [card(7, 292, 156, 23, 7, True)]
    if not wx.valid:
        left = "Weather API error" if api_error else "Fetching weather..."
        right = "OFFLINE"
        lc, rc = ("#ff7a67" if api_error else WHITE), "#ff6b5b"
    else:
        stale = is_stale(cfg, wx)
        left = f"Updated {_updated_text(wx)}"
        right = "STALE" if stale else "ONLINE"
        lc = "#ff7a67" if stale else WHITE
        rc = "#ff7a67" if stale else GREEN
    out += [
        icon("clock", 12, 294, .65),
        text(34, 304, left, 5.6, "start", lc, "650"),
        '<line x1="119" y1="297" x2="119" y2="310" stroke="#557385" stroke-width=".7"/>',
        f'<circle cx="130" cy="304" r="2.4" fill="{rc}"/>',
        text(157, 304, right, 5.5, "end", rc, "900"),
        "</svg>",
    ]
    return "".join(out)

def waveshare_svg(cfg: AppConfig, wx: WeatherData, api_error: str = "",
                  forecast_elapsed_seconds: float | None = None) -> str:
    w, h = 240, 320
    station = (cfg.station_name or "Weather Station")[:20]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        _defs(),
        '<rect width="240" height="320" fill="url(#bg)"/>',
        text(12, 21, station, 18, "start", WHITE, "900"),
    ]

    if wx.date_utc_ms:
        dt = datetime.fromtimestamp(wx.date_utc_ms / 1000)
        date_s = dt.strftime("%a, %b %d, %Y").replace(" 0", " ")
        out.append(text(229, 22, date_s, 6.6, "end", "#dbe7ee", "500"))
    out += [
        text(12, 38, "WEATHER STATION", 5.2, "start", "#9db8ca", "600", 1.55),
        '<line x1="12" y1="47" x2="228" y2="47" stroke="#173f55" stroke-width=".7"/>',
    ]

    if not wx.valid:
        out += [
            card(10, 54, 128, 151, 12, True),
            text(74, 112, "WAITING", 23, "middle", WHITE, "900"),
            text(74, 146, "Weather API error" if api_error else "Fetching weather...",
                 8, "middle", MUTED, "600"),
        ]
    else:
        apparent = int(round(apparent_outdoor_f(wx)))
        risk = _hero_palette(wx)
        out.append(_hero_gradient_defs(risk))

        out += [
            f'<rect x="10" y="54" width="128" height="151" rx="12" fill="url(#heroCurrent)" '
            f'stroke="{risk["border"]}" stroke-width="1"/>',
            icon(risk["icon"], 22, 73, 1.82),
            text(101, 76, apparent_title(wx), 9.4, "middle", WHITE, "800", .35),
            _apparent_parts(apparent, "waveshare"),
            f'<rect x="18" y="170" width="112" height="24" rx="12" fill="url(#riskCurrent)" '
            f'stroke="{risk["accent"]}" stroke-width="1"/>',
            icon("alert", 31, 174, .65),
            text(85, 182, apparent_risk_label(wx), 7.2, "middle", risk["accent"], "900"),
        ]

        _metric(out, 143, 54, 87, 34, "temp", "TEMP",
                fmt(wx.temp_f, 1, "°F"), .66, 5.5, 10.2)
        _metric(out, 143, 91, 87, 34, "drop", "HUMIDITY",
                fmt(wx.humidity, 0, "%"), .66, 5.4, 10.2)
        _metric(out, 143, 128, 87, 34, "leaf", "DEW POINT",
                fmt(wx.dew_point_f, 1, "°F"), .66, 5.4, 10.0)
        _metric(out, 143, 165, 87, 40, "trend", "FROM YDAY",
                signed_delta(wx.from_yesterday_f), .64, 5.0, 9.7)

        out += [
            card(10, 210, 62, 52, 8, True),
            card(76, 210, 62, 52, 8, True),
            card(143, 210, 87, 52, 8, True),
        ]

        out += [
            icon("wind", 16, 228, .78),
            text(41, 218, "WIND", 5.5, "middle", "#9dc8e4", "700", .4),
            text(51, 234, fmt(wx.wind_mph,1), 11.5, "middle", WHITE, "900"),
            text(51, 246, "mph", 5.6, "middle", "#b3c7d4", "700"),
            text(41, 253, f"GUST  {fmt(wx.gust_mph,1)}", 4.6, "middle", "#a6d1ea", "700"),
            text(41, 260, f"MAX   {fmt(wx.max_daily_gust_mph,1)}", 4.6, "middle", "#a6d1ea", "700"),
        ]

        out += [
            icon("compass", 82, 227, .80),
            text(107, 218, "DIRECTION", 5.2, "middle", "#9dc8e4", "700", .35),
            text(117, 236,
                 (f"{round(wx.wind_dir_deg):.0f}°" if finite(wx.wind_dir_deg) else "--"),
                 12.2, "middle", WHITE, "900"),
            text(107, 254,
                 (direction_text(wx.wind_dir_deg) if finite(wx.wind_dir_deg) else "--"),
                 6.2, "middle", "#9dc8e4", "800"),
        ]

        tomorrow = forecast_shows_tomorrow(wx, forecast_elapsed_seconds)
        fh = wx.forecast_tomorrow_high_f if tomorrow else wx.forecast_today_high_f
        fl = wx.forecast_tomorrow_low_f if tomorrow else wx.forecast_today_low_f
        forecast_value = (
            f"{int(round(fh))}° / {int(round(fl))}°"
            if wx.forecast_valid and finite(fh) and finite(fl)
            else "-- / --"
        )
        out += [
            icon("sun", 150, 228, .80),
            text(188, 217, "TOMORROW" if tomorrow else "TODAY",
                 5.3, "middle", "#9dc8e4", "700", .35),
            text(188, 228, "HIGH / LOW F", 4.6, "middle", "#9db6c6", "650"),
            text(194, 248, forecast_value, 10.4, "middle", WHITE, "900"),
        ]

    out += [card(10, 272, 220, 36, 9, True)]
    if not wx.valid:
        left = "Weather API error" if api_error else "Fetching weather..."
        right = "OFFLINE"
        lc, rc = ("#ff7a67" if api_error else WHITE), "#ff6b5b"
    else:
        stale = is_stale(cfg, wx)
        left = f"Updated {_updated_text(wx)}"
        right = "STALE" if stale else "ONLINE"
        lc = "#ff7a67" if stale else WHITE
        rc = "#ff7a67" if stale else GREEN

    out += [
        icon("clock", 17, 280, .78),
        text(45, 290, left, 7.2, "start", lc, "650"),
        '<line x1="169" y1="280" x2="169" y2="300" stroke="#557385" stroke-width=".8"/>',
        f'<circle cx="190" cy="290" r="3" fill="{rc}" filter="url(#softGlow)"/>',
        text(221, 290, right, 7.2, "end", rc, "900"),
        "</svg>",
    ]
    return "".join(out)
