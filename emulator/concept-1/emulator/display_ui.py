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
    fill = "#071d2c" if highlight else "#041622"
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
    # Match firmware: stale means no successful fetch within the stale
    # interval. Provider observation timestamps can legitimately lag.
    return bool(
        wx.valid
        and wx.fetched_monotonic
        and ((time.monotonic() - wx.fetched_monotonic) > cfg.stale_seconds)
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
            '<g>'
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
        '<linearGradient id="heroCurrent" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{style["top"]}"/>'
        f'<stop offset="1" stop-color="{style["bottom"]}"/>'
        '</linearGradient>'
        '</defs>'
    )


def _hero_icon(layout, cold):
    if layout == "tdisplay":
        if cold:
            x, y = 18, 82
            return (
                f'<path d="M{x} {y}H{x+30} M{x+24} {y-4}L{x+30} {y}L{x+24} {y+4} '
                f'M{x-3} {y+9}H{x+25} M{x+19} {y+5}L{x+25} {y+9}L{x+19} {y+13} '
                f'M{x+3} {y+18}H{x+29}" fill="none" stroke="#52beff" stroke-width="1"/>'
            )
        cx, cy, r = 32, 88, 10
        rays = [(12,88,17,88),(47,88,52,88),(32,68,32,73),(32,103,32,108),
                (19,75,23,79),(41,97,45,101),(19,101,23,97),(41,79,45,75)]
    elif layout == "waveshare":
        if cold:
            x, y = 20, 88
            return (
                f'<path d="M{x} {y}H{x+36} M{x+29} {y-5}L{x+36} {y}L{x+29} {y+5} '
                f'M{x-2} {y+11}H{x+30} M{x+23} {y+6}L{x+30} {y+11}L{x+23} {y+16} '
                f'M{x+4} {y+22}H{x+35}" fill="none" stroke="#52beff" stroke-width="1"/>'
            )
        cx, cy, r = 36, 96, 13
        rays = [(14,96,21,96),(52,96,59,96),(36,74,36,81),(36,112,36,119),
                (19,79,24,84),(48,108,53,113),(19,113,24,108),(48,84,53,79)]
    else:
        if cold:
            x, y = 66, 143
            return (
                f'<path d="M{x} {y}H{x+78} M{x+63} {y-10}L{x+78} {y}L{x+63} {y+10} '
                f'M{x-5} {y+25}H{x+65} M{x+50} {y+15}L{x+65} {y+25}L{x+50} {y+35} '
                f'M{x+10} {y+50}H{x+76}" fill="none" stroke="#52beff" stroke-width="1.5"/>'
            )
        cx, cy, r = 110, 160, 28
        rays = [(60,160,74,160),(147,160,161,160),(110,110,110,124),(110,197,110,211),
                (71,121,83,133),(137,187,149,199),(71,199,83,187),(137,133,149,121)]
    lines = ''.join(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ffc12b" stroke-width="1.5"/>'
        for x1, y1, x2, y2 in rays
    )
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#ffc12b" stroke="#ffdc60" stroke-width="1"/>{lines}'


def _clock_icon(cx, cy, r):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#a8c6d8" stroke-width="1.5"/>'
        f'<line x1="{cx}" y1="{cy-r+3}" x2="{cx}" y2="{cy}" stroke="#a8c6d8" stroke-width="1.5"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{cx + max(3, r//2)}" y2="{cy + max(2, r//3)}" stroke="#a8c6d8" stroke-width="1.5"/>'
    )


def _apparent_parts(value, layout):
    value_s = str(value)
    if layout == "tdisplay":
        if len(value_s) >= 3:
            number_x, degree_x, f_x = 98, 133, 145
        else:
            number_x, degree_x, f_x = 102, 132, 144
        return "".join([
            text(number_x, 98, value_s, 35, "middle", WHITE, "900"),
            f'<circle cx="{degree_x}" cy="83" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
            text(f_x, 101, "F", 14, "middle", WHITE, "800"),
        ])
    if len(value_s) >= 3:
        return "".join([
            text(55, 138, value_s, 32, "start", WHITE, "900"),
            f'<circle cx="119" cy="123" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
            text(125, 142, "F", 16, "start", WHITE, "800"),
        ])
    return "".join([
        text(57, 136, value_s, 40, "start", WHITE, "900"),
        f'<circle cx="118" cy="119" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
        text(124, 140, "F", 16, "start", WHITE, "800"),
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
    station = cfg.station_name or "Weather Station"
    if len(station) > 14:
        station = station[:14]
    station_size = 14 if len(station) <= 7 else 9
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        _defs(),
        '<rect width="170" height="320" fill="#000000"/>',
        text(8, 18, station, station_size, "start", WHITE, "900"),
        '<line x1="8" y1="33" x2="20" y2="33" stroke="#7ec8e8" stroke-width=".7"/>',
        text(27, 33, "CURRENT CONDITIONS", 4.6, "start", "#9fbed1", "600", 1.25),
    ]
    date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")
    out.append(text(162, 18, date_s, 4.6, "end", "#dbe7ee", "500"))

    if not wx.valid:
        out += [
            card(8, 43, 154, 244, 11, True),
            text(85, 148, "WAITING", 18, "middle", WHITE, "900"),
            text(85, 177, "Weather API error" if api_error else "Preparing display",
                 7.2, "middle", MUTED, "600"),
            text(85, 199, "Check provider configuration" if api_error else "Fetching weather...",
                 6.0, "middle", CYAN, "600"),
        ]
    else:
        apparent = int(round(apparent_outdoor_f(wx)))
        risk = _hero_palette(wx)
        out.append(_hero_gradient_defs(risk))

        out += [
            f'<rect x="8" y="43" width="154" height="101" rx="11" fill="url(#heroCurrent)" '
            f'stroke="{risk["border"]}" stroke-width="1"/>',
            _hero_icon("tdisplay", wind_chill_applies(wx)),
            text(118, 59, apparent_title(wx), 9.0, "middle", WHITE, "800", .5),
            _apparent_parts(apparent, "tdisplay"),
            f'<rect x="16" y="116" width="138" height="20" rx="10" fill="{risk["status"]}" '
            f'stroke="{risk["accent"]}" stroke-width="1"/>',
            text(85, 126, apparent_risk_label(wx), 6.8, "middle", risk["accent"], "900"),
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
        _clock_icon(18, 304, 6),
        text(34, 304, left, 5.6, "start", lc, "650"),
        '<line x1="119" y1="297" x2="119" y2="310" stroke="#557385" stroke-width=".7"/>',
        f'<circle cx="130" cy="304" r="2.4" fill="{rc}"/>',
        text(136, 304, right, 5.5, "start", rc, "900"),
        "</svg>",
    ]
    return "".join(out)

def waveshare_svg(cfg: AppConfig, wx: WeatherData, api_error: str = "",
                  forecast_elapsed_seconds: float | None = None) -> str:
    w, h = 240, 320
    station = (cfg.station_name or "Weather Station")[:16]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        _defs(),
        '<rect width="240" height="320" fill="#000000"/>',
        text(12, 21, station, 18, "start", WHITE, "900"),
    ]

    date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")
    out.append(text(229, 22, date_s, 6.6, "end", "#dbe7ee", "500"))
    out += [
        text(12, 38, "CURRENT CONDITIONS", 5.2, "start", "#9db8ca", "800", 1.55),
        '<line x1="12" y1="47" x2="228" y2="47" stroke="#173f55" stroke-width=".7"/>',
    ]

    if not wx.valid:
        out += [
            card(10, 54, 220, 208, 12, True),
            text(120, 143, "WAITING", 23, "middle", WHITE, "900"),
            text(120, 176, "Weather API error" if api_error else "Preparing display",
                 8, "middle", MUTED, "600"),
            text(120, 199, "Check provider configuration" if api_error else "Fetching weather...",
                 7.0, "middle", CYAN, "600"),
        ]
    else:
        apparent = int(round(apparent_outdoor_f(wx)))
        risk = _hero_palette(wx)
        out.append(_hero_gradient_defs(risk))

        out += [
            f'<rect x="10" y="54" width="128" height="151" rx="12" fill="url(#heroCurrent)" '
            f'stroke="{risk["border"]}" stroke-width="1"/>',
            _hero_icon("waveshare", wind_chill_applies(wx)),
            text(101, 76, apparent_title(wx), 9.4, "middle", WHITE, "800", .35),
            _apparent_parts(apparent, "waveshare"),
            f'<rect x="18" y="170" width="112" height="24" rx="12" fill="{risk["status"]}" '
            f'stroke="{risk["accent"]}" stroke-width="1"/>',
            text(74, 182, apparent_risk_label(wx), 7.2, "middle", risk["accent"], "900"),
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
        _clock_icon(24, 290, 7),
        text(45, 290, left, 7.2, "start", lc, "650"),
        '<line x1="169" y1="280" x2="169" y2="300" stroke="#557385" stroke-width=".8"/>',
        f'<circle cx="187" cy="290" r="3" fill="{rc}"/>',
        text(194, 290, right, 7.2, "start", rc, "900"),
        "</svg>",
    ]
    return "".join(out)


def _metric_7c(out, x, y, w, h, kind, label, value, value_size=25):
    """Production-aligned metric card used by the 800x480 7C-BOX."""
    out.append(card(x, y, w, h, 12, False))
    out.append(icon(kind, x + 12, y + (h - 40) / 2, 2.0))
    out.append(text(x + 64, y + 18, label, 16, "start", CYAN, "800", .5))
    out.append(text(x + 64, y + 39, value, value_size, "start", WHITE, "900"))


def _apparent_parts_7c(value):
    value_s = str(value)
    text_size = 8 if len(value_s) >= 3 else 9
    number_font = text_size * 8
    number_w = len(value_s) * 6 * text_size
    group_w = number_w + 18 + 24
    start_x = 320 - group_w / 2
    degree_x = start_x + number_w + 7
    f_x = start_x + number_w + 16
    return "".join([
        text(start_x, 143 + number_font / 2, value_s, number_font, "start", WHITE, "900"),
        f'<circle cx="{degree_x}" cy="150" r="4" fill="none" stroke="{WHITE}" stroke-width="1.5"/>',
        text(f_x, 179, "F", 32, "start", WHITE, "800"),
    ])


def waveshare_7c_svg(cfg: AppConfig, wx: WeatherData, api_error: str = "",
                     forecast_elapsed_seconds: float | None = None) -> str:
    """Emulate the production Waveshare ESP32-S3-Touch-LCD-7C-BOX (800x480)."""
    w, h = 800, 480
    station = (cfg.station_name or "Weather Station")[:20]
    station_size = 30 if len(station) <= 13 else 24
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        _defs(),
        '<rect width="800" height="480" fill="#000000"/>',
        text(30, 34, station, station_size, "start", WHITE, "900"),
    ]

    date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")
    out.append(text(770, 35, date_s, 16, "end", "#dbe7ee", "500"))
    out += [
        text(30, 64, "CURRENT CONDITIONS", 15, "start", "#9db8ca", "800", 1.2),
        '<line x1="30" y1="76" x2="770" y2="76" stroke="#173f55" stroke-width="1"/>',
    ]

    if not wx.valid:
        out += [
            card(33, 82, 734, 310, 18, True),
            text(400, 188, "WAITING", 52, "middle", WHITE, "900"),
            text(400, 245, "Weather API error" if api_error else "Preparing display",
                 24, "middle", MUTED, "600"),
            text(400, 289, "Fetching weather..." if not api_error else "Check provider configuration",
                 18, "middle", "#72caff", "600"),
        ]
    else:
        apparent = int(round(apparent_outdoor_f(wx)))
        risk = _hero_palette(wx)
        out.append(_hero_gradient_defs(risk))
        cold = wind_chill_applies(wx)

        out += [
            f'<rect x="33" y="82" width="427" height="225" rx="18" fill="url(#heroCurrent)" '
            f'stroke="{risk["border"]}" stroke-width="1.5"/>',
            _hero_icon("7c", cold),
            text(325, 116, apparent_title(wx), 24, "middle", WHITE, "900", 1.0),
            _apparent_parts_7c(apparent),
            f'<rect x="60" y="260" width="373" height="34" rx="17" fill="{risk["status"]}" '
            f'stroke="{risk["accent"]}" stroke-width="1.4"/>',
            text(246, 277, apparent_risk_label(wx), 15, "middle", risk["accent"], "900", 1.0),
        ]

        _metric_7c(out, 477, 82, 290, 50, "temp", "TEMP", fmt(wx.temp_f, 1, "°F"))
        _metric_7c(out, 477, 137, 290, 50, "drop", "HUMIDITY", fmt(wx.humidity, 0, "%"))
        _metric_7c(out, 477, 192, 290, 50, "leaf", "DEW POINT", fmt(wx.dew_point_f, 1, "°F"))
        _metric_7c(out, 477, 247, 290, 60, "trend", "FROM YDAY", signed_delta(wx.from_yesterday_f))

        out += [
            card(33, 316, 207, 76, 14, True),
            icon("wind", 48, 337, 2.0),
            text(136, 330, "WIND", 15, "middle", "#9dc8e4", "800"),
            text(160, 355, fmt(wx.wind_mph, 1), 30, "middle", WHITE, "900"),
            text(160, 376, "mph", 10, "middle", "#9fb7c9", "700"),
            text(136, 386, f"GUST {fmt(wx.gust_mph,1)}", 10, "middle", "#a6d1ea", "700"),
            text(225, 386, f"MAX {fmt(wx.max_daily_gust_mph,1)}", 10, "end", "#a6d1ea", "700"),

            card(253, 316, 207, 76, 14, True),
            icon("compass", 270, 337, 2.0),
            text(356, 330, "DIRECTION", 15, "middle", "#9dc8e4", "800"),
            text(385, 356, (f"{round(wx.wind_dir_deg):.0f}°" if finite(wx.wind_dir_deg) else "--"),
                 30, "middle", WHITE, "900"),
            text(356, 384, (direction_text(wx.wind_dir_deg) if finite(wx.wind_dir_deg) else "--"),
                 16, "middle", "#9dc8e4", "800"),
        ]

        tomorrow = forecast_shows_tomorrow(wx, forecast_elapsed_seconds)
        fh = wx.forecast_tomorrow_high_f if tomorrow else wx.forecast_today_high_f
        fl = wx.forecast_tomorrow_low_f if tomorrow else wx.forecast_today_low_f
        forecast_value = (
            f"{int(round(fh))}° / {int(round(fl))}°"
            if wx.forecast_valid and finite(fh) and finite(fl) else "-- / --"
        )
        out += [
            card(477, 316, 290, 76, 14, True),
            icon("sun", 493, 335, 2.0),
            text(620, 330, "TOMORROW" if tomorrow else "TODAY", 15, "middle", "#9dc8e4", "800"),
            text(620, 348, "HIGH / LOW F", 10, "middle", "#9db6c6", "650"),
            text(635, 371, forecast_value, 30, "middle", WHITE, "900"),
        ]

    out += [card(33, 410, 734, 52, 14, True)]
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
        _clock_icon(67, 436, 12),
        text(94, 436, left, 15, "start", lc, "700"),
        '<line x1="570" y1="419" x2="570" y2="453" stroke="#557385" stroke-width="1"/>',
        f'<circle cx="664" cy="436" r="5" fill="{rc}"/>',
        text(677, 436, right, 15, "start", rc, "900", 1.0),
        "</svg>",
    ]
    return "".join(out)

