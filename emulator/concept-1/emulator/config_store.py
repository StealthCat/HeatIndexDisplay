from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from .app_state import AppConfig

CONFIG_PATH = Path(__file__).resolve().parent.parent / "emulator_config.json"

def load_config() -> AppConfig:
    cfg = AppConfig()
    if not CONFIG_PATH.exists():
        return cfg
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    for key, value in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    cfg.weather_source = "wunderground" if str(cfg.weather_source).lower() == "wunderground" else "ambient"
    cfg.data_mode = "live" if str(getattr(cfg, "data_mode", "preset")).lower() == "live" else "preset"
    if str(getattr(cfg, "preset_name", "heat")).lower() not in ("heat", "wind", "normal", "stale", "waiting", "manual"):
        cfg.preset_name = "heat"
    cfg.poll_seconds = max(15, int(cfg.poll_seconds))
    cfg.stale_seconds = max(30, int(cfg.stale_seconds))
    return cfg

def save_config(cfg: AppConfig) -> None:
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")

def update_config(cfg: AppConfig, data: dict) -> None:
    for key in ("weather_source", "station_name", "ambient_mac_address", "wu_station_id", "data_mode", "preset_name"):
        if key in data:
            setattr(cfg, key, str(data[key]).strip())

    for key in ("ambient_application_key", "ambient_api_key", "wu_api_key"):
        if key in data and str(data[key]).strip():
            setattr(cfg, key, str(data[key]).strip())

    if "poll_seconds" in data:
        cfg.poll_seconds = max(15, int(data["poll_seconds"]))
    if "stale_seconds" in data:
        cfg.stale_seconds = max(30, int(data["stale_seconds"]))
    cfg.weather_source = "wunderground" if cfg.weather_source == "wunderground" else "ambient"
    cfg.data_mode = "live" if cfg.data_mode == "live" else "preset"
    if cfg.preset_name not in ("heat", "wind", "normal", "stale", "waiting", "manual"):
        cfg.preset_name = "heat"
    save_config(cfg)
