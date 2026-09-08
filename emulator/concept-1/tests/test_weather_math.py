import unittest
from unittest.mock import patch

from emulator.app_state import AppConfig, WeatherData
from emulator.weather_math import (
    nws_heat_index_f, nws_wind_chill_f, direction_text,
    apparent_title, apparent_risk_label, recompute
)
from emulator.display_ui import tdisplay_svg, waveshare_svg
from emulator import weather_source

class WeatherMathTests(unittest.TestCase):
    def test_hot_example(self):
        hi = nws_heat_index_f(98.8, 56.0)
        self.assertTrue(119.0 < hi < 125.0)

    def test_wind_chill_example(self):
        wc = nws_wind_chill_f(28.4, 14.8)
        self.assertAlmostEqual(wc, 17.1, places=1)

    def test_mode_switch(self):
        wx = WeatherData(temp_f=28.4, humidity=64, wind_mph=14.8, valid=True)
        recompute(wx)
        self.assertEqual(apparent_title(wx), "WIND CHILL")
        self.assertEqual(apparent_risk_label(wx), "COLD")

        wx.temp_f = 98.8
        wx.humidity = 56
        wx.wind_mph = 0
        recompute(wx)
        self.assertEqual(apparent_title(wx), "HEAT INDEX")
        self.assertEqual(apparent_risk_label(wx), "DANGER")

    def test_direction(self):
        self.assertEqual(direction_text(0), "N")
        self.assertEqual(direction_text(196), "SSW")
        self.assertEqual(direction_text(270), "W")

    def test_svg_smoke(self):
        cfg = AppConfig(station_name="Cronin Farm")
        wx = WeatherData(temp_f=98.8, humidity=56, wind_mph=0, gust_mph=2.2,
                         wind_dir_deg=196, today_high_f=99.1, today_low_f=72.7,
                         from_yesterday_f=6.3, date_utc_ms=1700000000000, valid=True)
        recompute(wx)
        self.assertIn("HEAT INDEX", tdisplay_svg(cfg, wx))
        self.assertIn('width="240"', waveshare_svg(cfg, wx))

    def test_live_current_survives_summary_failure(self):
        cfg = AppConfig(weather_source="ambient")
        previous = WeatherData(
            temp_f=90.0, humidity=50.0, wind_mph=0.0, valid=True,
            today_high_f=95.0, today_low_f=70.0,
            yesterday_temp_f=88.0, from_yesterday_f=2.0,
            max_daily_gust_mph=12.0, summary_valid=True
        )
        current = WeatherData(
            temp_f=99.0, humidity=55.0, wind_mph=1.0, gust_mph=2.0,
            wind_dir_deg=180.0, valid=True
        )
        recompute(current)

        with patch("emulator.weather_source.ambient_weather.fetch_current",
                   return_value=(current, "AA:BB", "Live Station")), \
             patch("emulator.weather_source.ambient_weather.fetch_summary",
                   side_effect=RuntimeError("history unavailable")):
            result, summary_error = weather_source.poll(cfg, previous)

        self.assertEqual(result.temp_f, 99.0)
        self.assertTrue(result.valid)
        self.assertEqual(result.today_high_f, 95.0)
        self.assertEqual(result.today_low_f, 70.0)
        self.assertIn("history unavailable", summary_error)
        self.assertEqual(cfg.ambient_mac_address, "AA:BB")
        self.assertEqual(cfg.station_name, "Live Station")

if __name__ == "__main__":
    unittest.main()
