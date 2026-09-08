from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request

from .app_state import WeatherData

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_REFRESH_SECONDS = 900
FORECAST_RETRY_SECONDS = 60
FORECAST_CARD_SWITCH_SECONDS = 30

_BOOT_MONOTONIC = time.monotonic()


class ForecastError(RuntimeError):
    def __init__(self, message: str, http_code: int = 0):
        super().__init__(message)
        self.http_code = int(http_code or 0)


def forecast_shows_tomorrow(wx: WeatherData, elapsed_seconds: float | None = None) -> bool:
    """Match production's 30-second alternating forecast card."""
    if (
        not wx.forecast_valid
        or not math.isfinite(wx.forecast_tomorrow_high_f)
        or not math.isfinite(wx.forecast_tomorrow_low_f)
    ):
        return False
    if FORECAST_CARD_SWITCH_SECONDS <= 0:
        return False
    if elapsed_seconds is None:
        elapsed_seconds = max(0.0, time.monotonic() - _BOOT_MONOTONIC)
    return (int(elapsed_seconds // FORECAST_CARD_SWITCH_SECONDS) & 1) != 0


def forecast_card_seconds_remaining(elapsed_seconds: float | None = None) -> int:
    if elapsed_seconds is None:
        elapsed_seconds = max(0.0, time.monotonic() - _BOOT_MONOTONIC)
    period = max(1, FORECAST_CARD_SWITCH_SECONDS)
    inside = elapsed_seconds % period
    return max(1, int(math.ceil(period - inside)))


def copy_forecast(src: WeatherData | None, dst: WeatherData) -> None:
    """Provider polls replace the emulator WeatherData object; production updates it in place.

    Carry these fields forward so the desktop emulator has the same 15-minute
    forecast refresh behavior as the ESP32 firmware.
    """
    if src is None:
        return
    dst.forecast_today_high_f = src.forecast_today_high_f
    dst.forecast_today_low_f = src.forecast_today_low_f
    dst.forecast_tomorrow_high_f = src.forecast_tomorrow_high_f
    dst.forecast_tomorrow_low_f = src.forecast_tomorrow_low_f
    dst.forecast_fetched_monotonic = src.forecast_fetched_monotonic
    dst.forecast_valid = src.forecast_valid


def _get_json(url: str, timeout: float = 15.0) -> tuple[dict, int]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "WS5000-ApparentTemp-Emulator/7.11.9-concept1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code = int(getattr(response, "status", 200) or 200)
            return json.load(response), code
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        if len(body) > 160:
            body = body[:160]
        msg = f"Forecast HTTP {exc.code}"
        if body:
            msg += f": {body}"
        raise ForecastError(msg, exc.code) from exc
    except Exception as exc:
        raise ForecastError(str(exc), 0) from exc


def build_forecast_url(wx: WeatherData) -> str:
    if not wx.valid or not math.isfinite(wx.latitude) or not math.isfinite(wx.longitude):
        raise ForecastError("Weather station coordinates are not available")
    query = urllib.parse.urlencode(
        {
            "latitude": f"{wx.latitude:.6f}",
            "longitude": f"{wx.longitude:.6f}",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 2,
        }
    )
    return f"{OPEN_METEO_FORECAST_URL}?{query}"


def fetch_forecast_high_low(wx: WeatherData) -> int:
    """Fetch exactly the V7.11.9 Concept 1 production high/low forecast payload."""
    url = build_forecast_url(wx)
    doc, code = _get_json(url)
    daily = doc.get("daily") or {}
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    if len(highs) < 2 or len(lows) < 2:
        raise ForecastError(
            "Forecast response did not contain today and tomorrow high/low",
            code,
        )
    try:
        today_high = float(highs[0])
        today_low = float(lows[0])
        tomorrow_high = float(highs[1])
        tomorrow_low = float(lows[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise ForecastError("Forecast returned invalid temperature values", code) from exc

    values = (today_high, today_low, tomorrow_high, tomorrow_low)
    if not all(math.isfinite(v) for v in values):
        raise ForecastError("Forecast returned invalid temperature values", code)

    wx.forecast_today_high_f = today_high
    wx.forecast_today_low_f = today_low
    wx.forecast_tomorrow_high_f = tomorrow_high
    wx.forecast_tomorrow_low_f = tomorrow_low
    wx.forecast_fetched_monotonic = time.monotonic()
    wx.forecast_valid = True
    return code
