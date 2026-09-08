from __future__ import annotations
from dataclasses import dataclass, asdict
from math import nan
from typing import Any, Dict
import time

@dataclass
class AppConfig:
    weather_source: str = "ambient"
    station_name: str = "Cronin Farm"
    data_mode: str = "preset"
    preset_name: str = "heat"

    ambient_application_key: str = ""
    ambient_api_key: str = ""
    ambient_mac_address: str = ""

    wu_api_key: str = ""
    wu_station_id: str = ""

    poll_seconds: int = 60
    stale_seconds: int = 180
    host: str = "127.0.0.1"
    port: int = 8765

    def public_dict(self) -> Dict[str, Any]:
        return {
            "weather_source": self.weather_source,
            "station_name": self.station_name,
            "data_mode": self.data_mode,
            "preset_name": self.preset_name,
            "ambient_application_key_set": bool(self.ambient_application_key),
            "ambient_api_key_set": bool(self.ambient_api_key),
            "ambient_mac_address": self.ambient_mac_address,
            "wu_api_key_set": bool(self.wu_api_key),
            "wu_station_id": self.wu_station_id,
            "poll_seconds": self.poll_seconds,
            "stale_seconds": self.stale_seconds,
            "host": self.host,
            "port": self.port,
        }

@dataclass
class WeatherData:
    temp_f: float = nan
    humidity: float = nan
    heat_index_f: float = nan
    dew_point_f: float = nan
    wind_mph: float = nan
    gust_mph: float = nan
    max_daily_gust_mph: float = nan
    wind_chill_f: float = nan
    wind_dir_deg: float = nan
    latitude: float = nan
    longitude: float = nan
    yesterday_temp_f: float = nan
    from_yesterday_f: float = nan
    today_high_f: float = nan
    today_low_f: float = nan
    forecast_today_high_f: float = nan
    forecast_today_low_f: float = nan
    forecast_tomorrow_high_f: float = nan
    forecast_tomorrow_low_f: float = nan
    date_utc_ms: int = 0
    fetched_monotonic: float = 0.0
    summary_fetched_monotonic: float = 0.0
    forecast_fetched_monotonic: float = 0.0
    summary_valid: bool = False
    forecast_valid: bool = False
    summary_source: str = ""
    provider_tz: str = ""
    obs_time_local: str = ""
    valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        import math
        for k, v in list(d.items()):
            if isinstance(v, float) and not math.isfinite(v):
                d[k] = None
        return d

def now_ms() -> int:
    return int(time.time() * 1000)
