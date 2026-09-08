from __future__ import annotations
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Tuple

from .app_state import AppConfig, WeatherData, now_ms
from .weather_math import dew_point_from_temp_humidity_f, nws_heat_index_f, nws_wind_chill_f

AMBIENT_DEVICES_URL = "https://rt.ambientweather.net/v1/devices"

class AmbientError(RuntimeError):
    pass

def _get_json(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": "HeatIndexDisplay-Emulator/7.11.9-concept1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception as exc:
        raise AmbientError(str(exc)) from exc

def _f(obj, *keys):
    for key in keys:
        if key in obj and obj[key] is not None:
            try:
                return float(obj[key])
            except (TypeError, ValueError):
                pass
    return math.nan

def configured(cfg: AppConfig) -> bool:
    return bool(cfg.ambient_application_key and cfg.ambient_api_key)

def _same_local_time_yesterday_ms(epoch_ms: int) -> int:
    """Return the epoch for the same local wall-clock time one calendar day ago.

    Using local calendar arithmetic instead of subtracting 86,400,000 ms mirrors
    the production V7.11.9 Concept 1 firmware and preserves the wall-clock comparison across
    daylight-saving transitions.
    """
    current_local = datetime.fromtimestamp(epoch_ms / 1000.0)
    yesterday_local = current_local - timedelta(days=1)
    return int(yesterday_local.timestamp() * 1000)

def _history(cfg: AppConfig, end_date_ms: int, limit: int):
    query = urllib.parse.urlencode({
        "apiKey": cfg.ambient_api_key,
        "applicationKey": cfg.ambient_application_key,
        "endDate": int(end_date_ms),
        "limit": int(limit),
    })
    history = _get_json(
        f"{AMBIENT_DEVICES_URL}/{urllib.parse.quote(cfg.ambient_mac_address, safe=':')}?{query}"
    )
    if not isinstance(history, list) or not history:
        raise AmbientError("Ambient REST history returned no observations")
    return history

def fetch_current(cfg: AppConfig) -> Tuple[WeatherData, str, str]:
    if not configured(cfg):
        raise AmbientError("Ambient Application Key and API Key are not configured")

    query = urllib.parse.urlencode({
        "apiKey": cfg.ambient_api_key,
        "applicationKey": cfg.ambient_application_key,
    })
    devices = _get_json(f"{AMBIENT_DEVICES_URL}?{query}")
    if not isinstance(devices, list) or not devices:
        raise AmbientError("Ambient account returned no devices")

    wanted = cfg.ambient_mac_address.replace(":", "").replace("-", "").upper()
    selected = None
    for device in devices:
        mac = str(device.get("macAddress", "")).replace(":", "").replace("-", "").upper()
        if wanted and mac == wanted:
            selected = device
            break
    if selected is None:
        if wanted:
            raise AmbientError("Configured station MAC was not found")
        selected = devices[0]

    last = selected.get("lastData") or {}
    temp = _f(last, "tempf")
    humidity = _f(last, "humidity")
    if not math.isfinite(temp) or not math.isfinite(humidity) or not 0 <= humidity <= 100:
        raise AmbientError("Selected station returned invalid tempf/humidity")

    wx = WeatherData()
    wx.temp_f = temp
    wx.humidity = humidity
    wx.heat_index_f = nws_heat_index_f(temp, humidity)
    wx.dew_point_f = _f(last, "dewPoint", "dewPointf")
    if not math.isfinite(wx.dew_point_f):
        wx.dew_point_f = dew_point_from_temp_humidity_f(temp, humidity)
    wx.wind_mph = _f(last, "windspeedmph")
    wx.gust_mph = _f(last, "windgustmph", "gustmph")
    wx.max_daily_gust_mph = _f(last, "maxdailygust")
    wx.wind_chill_f = nws_wind_chill_f(temp, wx.wind_mph)
    wx.wind_dir_deg = _f(last, "winddir")

    # V7.11.9 Concept 1 forecast location: mirror production extraction from
    # info.coords.coords.{lat,lon}, with GeoJSON [lon, lat] fallback.
    info = selected.get("info") or {}
    coords_container = info.get("coords") or {}
    coords = coords_container.get("coords") or {}
    wx.latitude = _f(coords, "lat")
    wx.longitude = _f(coords, "lon")
    if not math.isfinite(wx.latitude) or not math.isfinite(wx.longitude):
        geo = (coords_container.get("geo") or {}).get("coordinates") or []
        if isinstance(geo, (list, tuple)) and len(geo) >= 2:
            try:
                wx.longitude = float(geo[0])
                wx.latitude = float(geo[1])
            except (TypeError, ValueError):
                wx.latitude = math.nan
                wx.longitude = math.nan
    wx.date_utc_ms = int(last.get("dateutc") or now_ms())
    wx.fetched_monotonic = time.monotonic()
    wx.valid = True

    mac = str(selected.get("macAddress", ""))
    station = str((selected.get("info") or {}).get("name") or cfg.station_name or "Weather Station")
    return wx, mac, station

def fetch_summary(cfg: AppConfig, wx: WeatherData) -> None:
    if not cfg.ambient_mac_address:
        raise AmbientError("Ambient station MAC is not configured")
    if not wx.valid or not wx.date_utc_ms:
        raise AmbientError("Current observation is not available")

    # The Ambient REST device-history endpoint is the authoritative source
    # for Today's High/Low and From Yesterday.
    today_history = _history(cfg, wx.date_utc_ms, 288)
    current_local_date = datetime.fromtimestamp(wx.date_utc_ms / 1000.0).date()

    high = math.nan
    low = math.nan
    for p in today_history:
        try:
            point_ms = int(p.get("dateutc") or 0)
        except Exception:
            point_ms = 0
        point_temp = _f(p, "tempf")
        if not point_ms or not math.isfinite(point_temp):
            continue
        if datetime.fromtimestamp(point_ms / 1000.0).date() == current_local_date:
            high = point_temp if not math.isfinite(high) else max(high, point_temp)
            low = point_temp if not math.isfinite(low) else min(low, point_temp)

    # Include the current provider observation in today's extrema. This still
    # remains provider API data, and protects the edge between the last
    # archived history sample and the live observation.
    if math.isfinite(wx.temp_f):
        high = wx.temp_f if not math.isfinite(high) else max(high, wx.temp_f)
        low = wx.temp_f if not math.isfinite(low) else min(low, wx.temp_f)

    if not math.isfinite(high) or not math.isfinite(low):
        raise AmbientError("Ambient REST history did not contain today's temperature data")

    wx.today_high_f = high
    wx.today_low_f = low
    wx.summary_valid = True
    wx.summary_source = "Ambient Weather /v1/devices/{MAC}"
    wx.summary_fetched_monotonic = time.monotonic()

    target_yesterday_ms = _same_local_time_yesterday_ms(wx.date_utc_ms)

    # Ambient returns observations descending from endDate. End the query
    # slightly after the target and request enough records to straddle the
    # same local clock time even for 30-minute storage intervals.
    search_end_ms = target_yesterday_ms + (30 * 60 * 1000)
    yesterday_history = _history(cfg, search_end_ms, 24)

    yesterday = math.nan
    best_delta = None
    for p in yesterday_history:
        try:
            point_ms = int(p.get("dateutc") or 0)
        except Exception:
            point_ms = 0
        point_temp = _f(p, "tempf")
        if not point_ms or not math.isfinite(point_temp):
            continue
        delta = abs(point_ms - target_yesterday_ms)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            yesterday = point_temp

    if not math.isfinite(yesterday):
        raise AmbientError("Ambient REST history did not contain yesterday temperature")

    wx.yesterday_temp_f = yesterday
    wx.from_yesterday_f = wx.temp_f - yesterday
    wx.summary_fetched_monotonic = time.monotonic()

