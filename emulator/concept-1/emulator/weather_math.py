from __future__ import annotations
import math
from .app_state import WeatherData

def dew_point_from_temp_humidity_f(t_f: float, rh: float) -> float:
    if not math.isfinite(t_f) or not math.isfinite(rh) or rh <= 0.0 or rh > 100.0:
        return math.nan
    t_c = (t_f - 32.0) * 5.0 / 9.0
    a = 17.625
    b = 243.04
    gamma = math.log(rh / 100.0) + (a * t_c) / (b + t_c)
    dp_c = (b * gamma) / (a - gamma)
    return dp_c * 9.0 / 5.0 + 32.0

def nws_heat_index_f(t: float, rh: float) -> float:
    simple = 0.5 * (t + 61.0 + ((t - 68.0) * 1.2) + (rh * 0.094))
    simple = (simple + t) * 0.5
    if simple < 80.0:
        return simple

    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )

    if rh < 13.0 and 80.0 <= t <= 112.0:
        inside = (17.0 - abs(t - 95.0)) / 17.0
        if inside > 0.0:
            hi -= ((13.0 - rh) / 4.0) * math.sqrt(inside)
    elif rh > 85.0 and 80.0 <= t <= 87.0:
        hi += ((rh - 85.0) / 10.0) * ((87.0 - t) / 5.0)
    return hi

def nws_wind_chill_f(t: float, wind_mph: float) -> float:
    if not math.isfinite(t) or not math.isfinite(wind_mph):
        return t
    if t > 50.0 or wind_mph <= 3.0:
        return t
    v16 = wind_mph ** 0.16
    return 35.74 + 0.6215 * t - 35.75 * v16 + 0.4275 * t * v16

def wind_chill_applies(wx: WeatherData) -> bool:
    return (
        wx.valid
        and math.isfinite(wx.temp_f)
        and math.isfinite(wx.wind_mph)
        and wx.temp_f <= 50.0
        and wx.wind_mph > 3.0
    )

def apparent_outdoor_f(wx: WeatherData) -> float:
    return wx.wind_chill_f if wind_chill_applies(wx) else wx.heat_index_f

def apparent_title(wx: WeatherData) -> str:
    return "WIND CHILL" if wind_chill_applies(wx) else "HEAT INDEX"

def risk_label(hi: float) -> str:
    if hi >= 125.0:
        return "EXTREME DANGER"
    if hi >= 103.0:
        return "DANGER"
    if hi >= 90.0:
        return "EXTREME CAUTION"
    if hi >= 80.0:
        return "CAUTION"
    return "NORMAL"

def cold_risk_label(wc: float) -> str:
    if wc <= -35.0:
        return "EXTREME DANGER"
    if wc <= -20.0:
        return "DANGER"
    if wc <= 0.0:
        return "VERY COLD"
    if wc <= 20.0:
        return "COLD"
    return "CHILLY"

def apparent_risk_label(wx: WeatherData) -> str:
    return cold_risk_label(wx.wind_chill_f) if wind_chill_applies(wx) else risk_label(wx.heat_index_f)

def direction_text(deg: float) -> str:
    if not math.isfinite(deg):
        return "--"
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    idx = int(math.floor((deg + 11.25) / 22.5)) % 16
    return dirs[idx]

def direction_long_text(deg: float) -> str:
    if not math.isfinite(deg):
        return "--"
    dirs = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
    idx = int(math.floor((deg + 22.5) / 45.0)) % 8
    return dirs[idx]

def recompute(wx: WeatherData) -> None:
    wx.heat_index_f = nws_heat_index_f(wx.temp_f, wx.humidity)
    wx.wind_chill_f = nws_wind_chill_f(wx.temp_f, wx.wind_mph)
    if not math.isfinite(wx.dew_point_f):
        wx.dew_point_f = dew_point_from_temp_humidity_f(wx.temp_f, wx.humidity)
