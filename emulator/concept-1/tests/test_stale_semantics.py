import time

from emulator.app_controller import EmulatorApp
from emulator.display_ui import is_stale, tdisplay_svg, waveshare_svg, waveshare_7c_svg


def _renders(app):
    return [
        tdisplay_svg(app.config, app.wx),
        waveshare_svg(app.config, app.wx),
        waveshare_7c_svg(app.config, app.wx),
    ]


def test_old_provider_timestamp_does_not_make_recent_fetch_stale():
    app = EmulatorApp(verbose=False)
    app.apply_preset("heat")
    app.wx.date_utc_ms = int((time.time() - 3600) * 1000)
    app.wx.fetched_monotonic = time.monotonic()

    assert not is_stale(app.config, app.wx)
    for svg in _renders(app):
        assert "ONLINE" in svg
        assert "STALE" not in svg


def test_failed_refresh_window_makes_data_stale():
    app = EmulatorApp(verbose=False)
    app.apply_preset("heat")
    app.wx.date_utc_ms = int(time.time() * 1000)
    app.wx.fetched_monotonic = time.monotonic() - app.config.stale_seconds - 1

    assert is_stale(app.config, app.wx)
    for svg in _renders(app):
        assert "STALE" in svg


def test_firmware_uses_fetch_age_for_stale_state():
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    paths = [
        root / "T-Display-S3/src/time_utils.cpp",
        root / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/time_utils.cpp",
        root / "Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/time_utils.cpp",
    ]
    for path in paths:
        src = path.read_text(encoding="utf-8")
        assert "millis() - wx.fetchedMs" in src
        assert "observationAgeSeconds() > cfg.staleSeconds" not in src
