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

CURRENT_URL = "https://api.weather.com/v2/pws/observations/current"
RECENT_1DAY_URL = "https://api.weather.com/v2/pws/observations/all/1day"
RECENT_7DAY_HOURLY_URL = "https://api.weather.com/v2/pws/observations/hourly/7day"
HISTORY_URL = "https://api.weather.com/v2/pws/history/all"
DAILY_HISTORY_URL = "https://api.weather.com/v2/pws/history/daily"

class WundergroundError(RuntimeError):
    pass

def _get_json(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": "HeatIndexDisplay-Emulator/7.11.9-concept1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception as exc:
        raise WundergroundError(str(exc)) from exc

def _f(obj, key):
    try:
        v = obj.get(key)
        return float(v) if v is not None else math.nan
    except (TypeError, ValueError, AttributeError):
        return math.nan

def configured(cfg: AppConfig) -> bool:
    return bool(cfg.wu_api_key and cfg.wu_station_id)

def _parse_local_datetime(value: str):
    if not value:
        return None
    value = str(value).strip().replace("T", " ")
    # Ignore any offset suffix; for comparisons we want provider-local wall time.
    base = value[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(base[:len(datetime.now().strftime(fmt))], fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except Exception:
        return None

def _same_local_time_yesterday_ms(epoch_ms: int) -> int:
    current_local = datetime.fromtimestamp(epoch_ms / 1000.0)
    yesterday_local = current_local - timedelta(days=1)
    return int(yesterday_local.timestamp() * 1000)

def _query_url(base: str, cfg: AppConfig, **extra):
    params = {
        "stationId": cfg.wu_station_id,
        "format": "json",
        "units": "e",
        "numericPrecision": "decimal",
        "apiKey": cfg.wu_api_key,
    }
    params.update(extra)
    return f"{base}?{urllib.parse.urlencode(params)}"

def _observations(url: str, empty_error: str):
    doc = _get_json(url)
    obs = doc.get("observations") or []
    if not obs:
        raise WundergroundError(empty_error)
    return obs

def _history(cfg: AppConfig, date_ymd: str):
    date_arg = date_ymd.replace("-", "")
    return _observations(
        _query_url(HISTORY_URL, cfg, date=date_arg),
        f"Weather Underground history returned no observations for {date_ymd}",
    )

def _daily_history(cfg: AppConfig, date_ymd: str):
    date_arg = date_ymd.replace("-", "")
    return _observations(
        _query_url(DAILY_HISTORY_URL, cfg, date=date_arg),
        f"Weather Underground daily REST returned no observations for {date_ymd}",
    )

def _recent_1day(cfg: AppConfig):
    return _observations(
        _query_url(RECENT_1DAY_URL, cfg),
        "Weather Underground recent 1-day REST returned no observations",
    )

def _recent_7day_hourly(cfg: AppConfig):
    return _observations(
        _query_url(RECENT_7DAY_HOURLY_URL, cfg),
        "Weather Underground recent 7-day hourly REST returned no observations",
    )

def _point_local_dt(point):
    dt = _parse_local_datetime(point.get("obsTimeLocal", ""))
    if dt is not None:
        return dt
    try:
        epoch = int(point.get("epoch") or 0)
    except Exception:
        epoch = 0
    return datetime.fromtimestamp(epoch) if epoch else None

def _point_temp(point):
    imp = point.get("imperial") or {}
    value = _f(imp, "tempAvg")
    if math.isfinite(value):
        return value
    high = _f(imp, "tempHigh")
    low = _f(imp, "tempLow")
    if math.isfinite(high) and math.isfinite(low):
        return (high + low) / 2.0
    if math.isfinite(high):
        return high
    if math.isfinite(low):
        return low
    return _f(imp, "temp")

def _summarize_day(observations, day, current_temp=math.nan, current_gust=math.nan):
    high = math.nan
    low = math.nan
    max_gust = math.nan

    for point in observations:
        local_dt = _point_local_dt(point)
        if local_dt is not None and local_dt.date() != day:
            continue

        imp = point.get("imperial") or {}
        ph = _f(imp, "tempHigh")
        pl = _f(imp, "tempLow")
        pa = _f(imp, "tempAvg")
        pg = _f(imp, "windgustHigh")

        if not math.isfinite(ph) and math.isfinite(pa):
            ph = pa
        if not math.isfinite(pl) and math.isfinite(pa):
            pl = pa

        if math.isfinite(ph):
            high = ph if not math.isfinite(high) else max(high, ph)
        if math.isfinite(pl):
            low = pl if not math.isfinite(low) else min(low, pl)
        if math.isfinite(pg):
            max_gust = pg if not math.isfinite(max_gust) else max(max_gust, pg)

    # Current observation is also provider API data and closes the gap after
    # the latest archived/recent-history bucket.
    if math.isfinite(current_temp):
        high = current_temp if not math.isfinite(high) else max(high, current_temp)
        low = current_temp if not math.isfinite(low) else min(low, current_temp)
    if math.isfinite(current_gust):
        max_gust = current_gust if not math.isfinite(max_gust) else max(max_gust, current_gust)

    return high, low, max_gust

def _nearest_yesterday_temp(observations, target_local_dt):
    best_temp = math.nan
    best_delta = None

    for point in observations:
        local_dt = _point_local_dt(point)
        temp = _point_temp(point)
        if local_dt is None or not math.isfinite(temp):
            continue
        if local_dt.date() != target_local_dt.date():
            continue

        delta = abs((local_dt - target_local_dt).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_temp = temp

    return best_temp

def fetch_current(cfg: AppConfig) -> Tuple[WeatherData, str]:
    if not configured(cfg):
        raise WundergroundError("Weather Underground API key and station ID are not configured")

    doc = _get_json(_query_url(CURRENT_URL, cfg))
    obs_list = doc.get("observations") or []
    if not obs_list:
        raise WundergroundError("Weather Underground returned no current observation")

    obs = obs_list[0]
    imperial = obs.get("imperial") or {}
    temp = _f(imperial, "temp")
    humidity = _f(obs, "humidity")
    if not math.isfinite(temp) or not math.isfinite(humidity) or not 0 <= humidity <= 100:
        raise WundergroundError("Weather Underground returned invalid temperature/humidity")

    wx = WeatherData()
    wx.temp_f = temp
    wx.humidity = humidity
    wx.heat_index_f = nws_heat_index_f(temp, humidity)
    wx.dew_point_f = _f(imperial, "dewpt")
    if not math.isfinite(wx.dew_point_f):
        wx.dew_point_f = dew_point_from_temp_humidity_f(temp, humidity)
    wx.wind_mph = _f(imperial, "windSpeed")
    wx.gust_mph = _f(imperial, "windGust")
    wx.max_daily_gust_mph = wx.gust_mph
    wx.wind_chill_f = nws_wind_chill_f(temp, wx.wind_mph)
    wx.wind_dir_deg = _f(obs, "winddir")
    wx.latitude = _f(obs, "lat")
    wx.longitude = _f(obs, "lon")

    try:
        wx.date_utc_ms = int(obs.get("epoch") or 0) * 1000
    except Exception:
        wx.date_utc_ms = now_ms()
    if not wx.date_utc_ms:
        wx.date_utc_ms = now_ms()

    wx.provider_tz = str(obs.get("tz") or "")
    wx.obs_time_local = str(obs.get("obsTimeLocal") or "")
    wx.fetched_monotonic = time.monotonic()
    wx.valid = True

    station_name = str(obs.get("neighborhood") or obs.get("stationID") or cfg.wu_station_id)
    return wx, station_name

def fetch_summary(cfg: AppConfig, wx: WeatherData) -> None:
    if not wx.valid or not wx.date_utc_ms:
        raise WundergroundError("Current observation is not available")

    current_local_dt = _parse_local_datetime(wx.obs_time_local)
    if current_local_dt is None:
        current_local_dt = datetime.fromtimestamp(wx.date_utc_ms / 1000.0)

    today = current_local_dt.date()
    target_yesterday_local = current_local_dt - timedelta(days=1)

    # First choice for live use: recent 7-day hourly PWS REST data. Unlike
    # archived history, it is designed to contain the current day and yesterday.
    recent_error = None
    recent = None
    try:
        recent = _recent_7day_hourly(cfg)
    except Exception as exc:
        recent_error = exc

    if recent:
        high, low, max_gust = _summarize_day(
            recent, today, wx.temp_f, wx.gust_mph
        )
        yesterday = _nearest_yesterday_temp(recent, target_yesterday_local)

        if math.isfinite(high) and math.isfinite(low):
            wx.today_high_f = high
            wx.today_low_f = low
            wx.max_daily_gust_mph = max_gust
            wx.summary_valid = True
            wx.summary_source = "Weather Underground /observations/hourly/7day"
            wx.summary_fetched_monotonic = time.monotonic()

        if math.isfinite(yesterday):
            wx.yesterday_temp_f = yesterday
            wx.from_yesterday_f = wx.temp_f - yesterday
            wx.summary_fetched_monotonic = time.monotonic()

        if wx.summary_valid and math.isfinite(wx.from_yesterday_f):
            return

    # If recent-hourly is unavailable or incomplete, use the dedicated
    # current-day recent 1-day endpoint before falling back to archived history.
    if not wx.summary_valid:
        try:
            recent_1day = _recent_1day(cfg)
            high, low, max_gust = _summarize_day(
                recent_1day, today, wx.temp_f, wx.gust_mph
            )
            if math.isfinite(high) and math.isfinite(low):
                wx.today_high_f = high
                wx.today_low_f = low
                wx.max_daily_gust_mph = max_gust
                wx.summary_valid = True
                wx.summary_source = "Weather Underground /observations/all/1day"
                wx.summary_fetched_monotonic = time.monotonic()
        except Exception:
            pass

    # Archived REST fallback for today's high/low.
    if not wx.summary_valid:
        today_ymd = today.strftime("%Y-%m-%d")
        try:
            today_obs = _daily_history(cfg, today_ymd)
        except Exception:
            today_obs = _history(cfg, today_ymd)

        high, low, max_gust = _summarize_day(
            today_obs, today, wx.temp_f, wx.gust_mph
        )
        if not math.isfinite(high) or not math.isfinite(low):
            raise WundergroundError(
                "Weather Underground REST data did not contain today's high/low"
            )

        wx.today_high_f = high
        wx.today_low_f = low
        wx.max_daily_gust_mph = max_gust
        wx.summary_valid = True
        wx.summary_source = "Weather Underground /history/daily|all"
        wx.summary_fetched_monotonic = time.monotonic()

    # Archived REST fallback for From Yesterday if recent 7-day did not provide it.
    if not math.isfinite(wx.from_yesterday_f):
        yesterday_ymd = target_yesterday_local.strftime("%Y-%m-%d")
        yesterday_obs = _history(cfg, yesterday_ymd)
        yesterday = _nearest_yesterday_temp(yesterday_obs, target_yesterday_local)

        if not math.isfinite(yesterday):
            detail = f"; recent hourly error: {recent_error}" if recent_error else ""
            raise WundergroundError(
                "Weather Underground REST data did not contain yesterday temperature"
                + detail
            )

        wx.yesterday_temp_f = yesterday
        wx.from_yesterday_f = wx.temp_f - yesterday
        wx.summary_fetched_monotonic = time.monotonic()
