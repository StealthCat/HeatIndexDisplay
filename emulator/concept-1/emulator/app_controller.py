from __future__ import annotations

import math
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer

from .app_state import WeatherData, now_ms
from .config_store import load_config, save_config, update_config
from .display_ui import tdisplay_svg, waveshare_svg, waveshare_7c_svg
from .forecast_weather import (
    FORECAST_REFRESH_SECONDS,
    FORECAST_RETRY_SECONDS,
    ForecastError,
    copy_forecast,
    fetch_forecast_high_low,
    forecast_card_seconds_remaining,
    forecast_shows_tomorrow,
)
from .weather_math import recompute, apparent_title, apparent_risk_label
from .weather_source import poll, configured, source_label
from .web_ui import handler_factory

VALID_PRESETS = ("heat", "wind", "normal", "stale", "waiting")


class EmulatorApp:
    def __init__(self, verbose=True):
        self.config = load_config()
        self.wx = WeatherData()
        self.lock = threading.RLock()
        self.last_api_error = ""
        self.last_http_code = 0
        self.last_summary_error = ""
        self.last_live_poll_monotonic = 0.0
        self.last_forecast_error = ""
        self.last_forecast_http_code = 0
        self.last_forecast_poll_monotonic = 0.0
        self.last_forecast_latitude = math.nan
        self.last_forecast_longitude = math.nan
        self.verbose = verbose
        self._stop = threading.Event()

        if self.config.data_mode == "live":
            self.wx = WeatherData()
        else:
            preset = self.config.preset_name if self.config.preset_name in VALID_PRESETS else "heat"
            if self.config.preset_name != preset:
                self.config.preset_name = preset
                save_config(self.config)
            self._apply_preset_values(preset)

    def state_payload(self):
        with self.lock:
            return {
                "weather": self.wx.to_dict(),
                "config": self.config.public_dict(),
                "status": self.status_payload(),
            }

    def status_payload(self):
        with self.lock:
            tomorrow = forecast_shows_tomorrow(self.wx)
            forecast_high = (
                self.wx.forecast_tomorrow_high_f if tomorrow else self.wx.forecast_today_high_f
            )
            forecast_low = (
                self.wx.forecast_tomorrow_low_f if tomorrow else self.wx.forecast_today_low_f
            )
            return {
                "data_mode": self.config.data_mode,
                "preset": self.config.preset_name if self.config.data_mode == "preset" else None,
                "source": source_label(self.config),
                "configured": configured(self.config),
                "valid": self.wx.valid,
                "display_mode": apparent_title(self.wx) if self.wx.valid else "WAITING",
                "risk": apparent_risk_label(self.wx) if self.wx.valid else "",
                "last_api_error": self.last_api_error,
                "last_summary_error": self.last_summary_error,
                "summary_valid": self.wx.summary_valid,
                "summary_source": self.wx.summary_source,
                "observed_today_high_f": None if not math.isfinite(self.wx.today_high_f) else round(self.wx.today_high_f, 2),
                "observed_today_low_f": None if not math.isfinite(self.wx.today_low_f) else round(self.wx.today_low_f, 2),
                "yesterday_temp_f": None if not math.isfinite(self.wx.yesterday_temp_f) else round(self.wx.yesterday_temp_f, 2),
                "from_yesterday_f": None if not math.isfinite(self.wx.from_yesterday_f) else round(self.wx.from_yesterday_f, 2),
                "latitude": None if not math.isfinite(self.wx.latitude) else round(self.wx.latitude, 6),
                "longitude": None if not math.isfinite(self.wx.longitude) else round(self.wx.longitude, 6),
                "forecast_source": "Open-Meteo" if self.config.data_mode == "live" else "Preset forecast",
                "forecast_valid": self.wx.forecast_valid,
                "forecast_today_high_f": None if not math.isfinite(self.wx.forecast_today_high_f) else round(self.wx.forecast_today_high_f, 2),
                "forecast_today_low_f": None if not math.isfinite(self.wx.forecast_today_low_f) else round(self.wx.forecast_today_low_f, 2),
                "forecast_tomorrow_high_f": None if not math.isfinite(self.wx.forecast_tomorrow_high_f) else round(self.wx.forecast_tomorrow_high_f, 2),
                "forecast_tomorrow_low_f": None if not math.isfinite(self.wx.forecast_tomorrow_low_f) else round(self.wx.forecast_tomorrow_low_f, 2),
                "forecast_card": "tomorrow" if tomorrow else "today",
                "forecast_card_high_f": None if not math.isfinite(forecast_high) else round(forecast_high, 2),
                "forecast_card_low_f": None if not math.isfinite(forecast_low) else round(forecast_low, 2),
                "forecast_switch_seconds_remaining": forecast_card_seconds_remaining(),
                "forecast_refresh_seconds": FORECAST_REFRESH_SECONDS,
                "last_forecast_http_code": self.last_forecast_http_code,
                "last_forecast_error": self.last_forecast_error,
                "live_polling": self.config.data_mode == "live",
                "poll_seconds": self.config.poll_seconds,
            }

    def render_tdisplay(self):
        with self.lock:
            return tdisplay_svg(self.config, self.wx, self.last_api_error)

    def render_waveshare(self):
        with self.lock:
            return waveshare_svg(self.config, self.wx, self.last_api_error)

    def render_waveshare_7c(self):
        with self.lock:
            return waveshare_7c_svg(self.config, self.wx, self.last_api_error)

    def apply_manual(self, data):
        with self.lock:
            self.config.data_mode = "preset"
            self.config.preset_name = "manual"
            for key in (
                "temp_f", "humidity", "dew_point_f", "wind_mph", "gust_mph",
                "wind_dir_deg", "from_yesterday_f", "today_high_f", "today_low_f",
                "forecast_today_high_f", "forecast_today_low_f",
                "forecast_tomorrow_high_f", "forecast_tomorrow_low_f",
            ):
                if key in data and data[key] is not None:
                    setattr(self.wx, key, float(data[key]))
            self.wx.date_utc_ms = now_ms()
            self.wx.valid = True
            self.wx.summary_valid = (
                math.isfinite(self.wx.today_high_f) and math.isfinite(self.wx.today_low_f)
            )
            self.wx.forecast_valid = all(
                math.isfinite(v)
                for v in (
                    self.wx.forecast_today_high_f,
                    self.wx.forecast_today_low_f,
                    self.wx.forecast_tomorrow_high_f,
                    self.wx.forecast_tomorrow_low_f,
                )
            )
            recompute(self.wx)
            self.last_api_error = ""
            self.last_summary_error = ""
            self.last_forecast_error = ""
            save_config(self.config)

    def _apply_preset_values(self, name):
        if name == "waiting":
            self.wx = WeatherData()
            self.last_api_error = ""
            self.last_summary_error = ""
            self.last_forecast_error = ""
            return

        self.config.station_name = self.config.station_name or "Cronin Farm"
        self.wx = WeatherData(valid=True, date_utc_ms=now_ms())
        # Generic Evans/Augusta-area coordinates are used only for the preset
        # status display. Preset mode never contacts Open-Meteo.
        self.wx.latitude = 33.53
        self.wx.longitude = -82.13

        if name == "wind":
            self.wx.temp_f = 28.4
            self.wx.humidity = 64.0
            self.wx.dew_point_f = 17.8
            self.wx.wind_mph = 14.8
            self.wx.gust_mph = 20.2
            self.wx.max_daily_gust_mph = 26.5
            self.wx.wind_dir_deg = 315.0
            self.wx.yesterday_temp_f = 39.6
            self.wx.from_yesterday_f = -11.2
            self.wx.today_high_f = 31.2
            self.wx.today_low_f = 22.6
            self.wx.forecast_today_high_f = 33.0
            self.wx.forecast_today_low_f = 21.0
            self.wx.forecast_tomorrow_high_f = 37.0
            self.wx.forecast_tomorrow_low_f = 24.0
        elif name == "normal":
            self.wx.temp_f = 72.0
            self.wx.humidity = 48.0
            self.wx.dew_point_f = 51.0
            self.wx.wind_mph = 2.0
            self.wx.gust_mph = 4.2
            self.wx.wind_dir_deg = 85.0
            self.wx.yesterday_temp_f = 71.4
            self.wx.from_yesterday_f = 0.6
            self.wx.today_high_f = 74.2
            self.wx.today_low_f = 58.1
            self.wx.forecast_today_high_f = 76.0
            self.wx.forecast_today_low_f = 59.0
            self.wx.forecast_tomorrow_high_f = 78.0
            self.wx.forecast_tomorrow_low_f = 61.0
        else:
            self.wx.temp_f = 98.8
            self.wx.humidity = 56.0
            self.wx.dew_point_f = 80.3
            self.wx.wind_mph = 0.0
            self.wx.gust_mph = 2.2
            self.wx.max_daily_gust_mph = 8.1
            self.wx.wind_dir_deg = 196.0
            self.wx.yesterday_temp_f = 92.5
            self.wx.from_yesterday_f = 6.3
            self.wx.today_high_f = 99.1
            self.wx.today_low_f = 72.7
            self.wx.forecast_today_high_f = 100.0
            self.wx.forecast_today_low_f = 73.0
            self.wx.forecast_tomorrow_high_f = 96.0
            self.wx.forecast_tomorrow_low_f = 72.0

        self.wx.summary_valid = True
        self.wx.summary_source = "Preset provider history"
        self.wx.forecast_valid = True
        self.wx.forecast_fetched_monotonic = time.monotonic()
        recompute(self.wx)
        if name == "stale":
            self.wx.date_utc_ms = now_ms() - (self.config.stale_seconds + 60) * 1000
        self.last_api_error = ""
        self.last_summary_error = ""
        self.last_forecast_error = ""
        self.last_forecast_http_code = 0

    def apply_preset(self, name):
        with self.lock:
            if name not in VALID_PRESETS:
                name = "heat"
            self.config.data_mode = "preset"
            self.config.preset_name = name
            self._apply_preset_values(name)
            save_config(self.config)

    def set_data_mode(self, mode, preset_name=None, poll_now=True):
        mode = "live" if str(mode).lower() == "live" else "preset"

        with self.lock:
            self.config.data_mode = mode
            if mode == "preset":
                if preset_name not in VALID_PRESETS:
                    preset_name = (
                        self.config.preset_name
                        if self.config.preset_name in VALID_PRESETS
                        else "heat"
                    )
                self.config.preset_name = preset_name
                self._apply_preset_values(preset_name)
                save_config(self.config)
                return

            self.wx = WeatherData()
            self.last_api_error = ""
            self.last_summary_error = ""
            self.last_forecast_error = ""
            self.last_forecast_http_code = 0
            self.last_forecast_poll_monotonic = 0.0
            self.last_forecast_latitude = math.nan
            self.last_forecast_longitude = math.nan
            save_config(self.config)

        if poll_now and configured(self.config):
            self.poll_provider()

    def apply_config(self, data):
        with self.lock:
            old_mode = self.config.data_mode
            old_source = self.config.weather_source
            update_config(self.config, data)
            new_mode = self.config.data_mode

            if new_mode == "preset":
                preset = self.config.preset_name
                if preset not in VALID_PRESETS:
                    preset = "heat"
                    self.config.preset_name = preset
                self._apply_preset_values(preset)
                save_config(self.config)
            elif old_mode != "live" or old_source != self.config.weather_source:
                self.wx = WeatherData()
                self.last_api_error = ""
                self.last_summary_error = ""
                self.last_forecast_error = ""
                self.last_forecast_http_code = 0
                self.last_forecast_poll_monotonic = 0.0
                self.last_forecast_latitude = math.nan
                self.last_forecast_longitude = math.nan

    def _forecast_location_changed(self) -> bool:
        if not math.isfinite(self.wx.latitude) or not math.isfinite(self.wx.longitude):
            return False
        if not math.isfinite(self.last_forecast_latitude) or not math.isfinite(self.last_forecast_longitude):
            return True
        return (
            abs(self.wx.latitude - self.last_forecast_latitude) > 0.0001
            or abs(self.wx.longitude - self.last_forecast_longitude) > 0.0001
        )

    def _poll_forecast_if_due(self, force=False):
        if self.config.data_mode != "live":
            return self.wx.forecast_valid
        if not self.wx.valid or not math.isfinite(self.wx.latitude) or not math.isfinite(self.wx.longitude):
            return False

        now = time.monotonic()
        location_changed = self._forecast_location_changed()
        interval = FORECAST_REFRESH_SECONDS if self.wx.forecast_valid else FORECAST_RETRY_SECONDS

        # Production fetches immediately on first valid coordinates, then every
        # 15 minutes; failed first forecasts retry every 60 seconds. Keep the
        # same cadence while avoiding sub-second retry loops after a location change.
        if self.last_forecast_poll_monotonic:
            elapsed = now - self.last_forecast_poll_monotonic
            if not force and not location_changed and elapsed < interval:
                return self.wx.forecast_valid
            if location_changed and elapsed < FORECAST_RETRY_SECONDS:
                return self.wx.forecast_valid

        self.last_forecast_poll_monotonic = now
        try:
            code = fetch_forecast_high_low(self.wx)
        except ForecastError as exc:
            self.last_forecast_http_code = exc.http_code
            self.last_forecast_error = str(exc)
            return False
        except Exception as exc:
            self.last_forecast_error = str(exc)
            return False

        self.last_forecast_http_code = code
        self.last_forecast_error = ""
        self.last_forecast_latitude = self.wx.latitude
        self.last_forecast_longitude = self.wx.longitude
        return True

    def poll_provider(self):
        # Current observations and provider history update first. The V7.11.9 Concept 1
        # forecast is then fetched independently from Open-Meteo using the
        # station coordinates returned by the configured provider.
        with self.lock:
            was_live = self.config.data_mode == "live"
            previous = self.wx if was_live and self.wx.valid else None
            self.config.data_mode = "live"
            if not was_live:
                self.wx = WeatherData()
            try:
                new_wx, summary_error = poll(self.config, previous)
                copy_forecast(previous, new_wx)
                self.wx = new_wx
                self.last_api_error = ""
                self.last_summary_error = summary_error
                self.last_live_poll_monotonic = time.monotonic()
                self._poll_forecast_if_due(force=False)
                save_config(self.config)
            except Exception as exc:
                self.last_api_error = str(exc)
                save_config(self.config)
                raise

    def _poll_loop(self):
        next_provider_poll = 0.0
        while not self._stop.wait(0.5):
            if self.config.data_mode != "live" or not configured(self.config):
                next_provider_poll = 0.0
                continue

            now = time.monotonic()
            if not next_provider_poll or now >= next_provider_poll:
                try:
                    self.poll_provider()
                except Exception:
                    pass
                next_provider_poll = now + max(15, self.config.poll_seconds)

            with self.lock:
                self._poll_forecast_if_due(force=False)

    def run(self):
        host, port = self.config.host, int(self.config.port)
        server = ThreadingHTTPServer((host, port), handler_factory(self))
        threading.Thread(target=self._poll_loop, daemon=True).start()

        url = f"http://{host}:{port}/"
        print(f"HeatIndexDisplay V7.11.9 Concept 1 emulator listening on {url}")
        print("V7.11.9 Concept 1 uses provider coordinates + Open-Meteo for forecast high/low.")
        print("Forecast card alternates Today's/Tomorrow every 30 seconds.")
        print("Press Ctrl+C to stop.")

        try:
            webbrowser.open(url)
        except Exception:
            pass

        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("\nStopping emulator...")
        finally:
            self._stop.set()
            server.server_close()
