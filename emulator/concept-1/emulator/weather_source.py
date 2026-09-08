from __future__ import annotations
import math
from .app_state import AppConfig, WeatherData
from . import ambient_weather, wunderground_weather

def source_label(cfg: AppConfig) -> str:
    return "Weather Underground" if cfg.weather_source == "wunderground" else "Ambient Weather"

def configured(cfg: AppConfig) -> bool:
    if cfg.weather_source == "wunderground":
        return wunderground_weather.configured(cfg)
    return ambient_weather.configured(cfg)

def _carry_forward_summary(previous: WeatherData | None, current: WeatherData) -> None:
    """Match production behavior: a history failure must not discard current weather.

    Production retains the last successful summary values when the historical
    request fails. The emulator now does the same.
    """
    if previous is None or not previous.summary_valid:
        return
    current.today_high_f = previous.today_high_f
    current.today_low_f = previous.today_low_f
    current.yesterday_temp_f = previous.yesterday_temp_f
    current.from_yesterday_f = previous.from_yesterday_f
    current.max_daily_gust_mph = (
        previous.max_daily_gust_mph
        if math.isfinite(previous.max_daily_gust_mph)
        else current.max_daily_gust_mph
    )
    current.summary_valid = previous.summary_valid
    current.summary_source = previous.summary_source
    current.summary_fetched_monotonic = previous.summary_fetched_monotonic

def poll(cfg: AppConfig, previous: WeatherData | None = None) -> tuple[WeatherData, str]:
    """Fetch current weather first, then best-effort history.

    Returns (current_weather, summary_error). A historical/summary API failure
    no longer prevents the freshly polled current observation from reaching
    the display.
    """
    if cfg.weather_source == "wunderground":
        wx, name = wunderground_weather.fetch_current(cfg)
        if name:
            cfg.station_name = name
        _carry_forward_summary(previous, wx)
        summary_error = ""
        try:
            wunderground_weather.fetch_summary(cfg, wx)
        except Exception as exc:
            summary_error = str(exc)
        return wx, summary_error

    wx, mac, name = ambient_weather.fetch_current(cfg)
    if mac and not cfg.ambient_mac_address:
        cfg.ambient_mac_address = mac
    if name:
        cfg.station_name = name

    _carry_forward_summary(previous, wx)
    summary_error = ""
    try:
        ambient_weather.fetch_summary(cfg, wx)
    except Exception as exc:
        summary_error = str(exc)
    return wx, summary_error
