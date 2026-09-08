import math
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from emulator.app_state import AppConfig, WeatherData
from emulator import ambient_weather, wunderground_weather


class ProviderRestSummaryTests(unittest.TestCase):
    def test_ambient_populates_summary_and_preserves_colons_in_mac(self):
        cfg = AppConfig(
            ambient_application_key="app",
            ambient_api_key="api",
            ambient_mac_address="AA:BB:CC",
        )
        current_ms = int(datetime(2026, 9, 7, 12, 0, 0).timestamp() * 1000)
        target_ms = ambient_weather._same_local_time_yesterday_ms(current_ms)
        wx = WeatherData(temp_f=95.0, date_utc_ms=current_ms, valid=True)
        calls = []

        def fake_get(url, timeout=15.0):
            calls.append(url)
            q = parse_qs(urlparse(url).query)
            limit = int(q["limit"][0])
            if limit == 288:
                return [
                    {"dateutc": current_ms - 3600000, "tempf": 97.2},
                    {"dateutc": current_ms - 7200000, "tempf": 88.4},
                ]
            return [
                {"dateutc": target_ms - 300000, "tempf": 90.0},
                {"dateutc": target_ms + 300000, "tempf": 91.0},
            ]

        with patch.object(ambient_weather, "_get_json", side_effect=fake_get):
            ambient_weather.fetch_summary(cfg, wx)

        self.assertEqual(len(calls), 2)
        self.assertIn("/AA:BB:CC?", calls[0])
        second = parse_qs(urlparse(calls[1]).query)
        self.assertEqual(second["limit"][0], "24")
        self.assertAlmostEqual(wx.today_high_f, 97.2)
        self.assertAlmostEqual(wx.today_low_f, 88.4)
        self.assertAlmostEqual(wx.yesterday_temp_f, 90.0)
        self.assertAlmostEqual(wx.from_yesterday_f, 5.0)
        self.assertTrue(wx.summary_valid)
        self.assertIn("Ambient Weather", wx.summary_source)

    def test_wu_recent_7day_populates_today_and_yesterday(self):
        cfg = AppConfig(wu_api_key="key", wu_station_id="KTEST1")
        current_local = datetime(2026, 9, 7, 12, 25, 0)
        current_ms = int(current_local.timestamp() * 1000)
        wx = WeatherData(
            temp_f=95.0, gust_mph=4.0, date_utc_ms=current_ms, valid=True,
            obs_time_local="2026-09-07 12:25:00"
        )

        recent = {"observations": [
            {
                "obsTimeLocal": "2026-09-07 10:59:00",
                "epoch": int(datetime(2026,9,7,10,59).timestamp()),
                "imperial": {"tempHigh": 99.1, "tempLow": 72.7, "tempAvg": 91.0, "windgustHigh": 8.1},
            },
            {
                "obsTimeLocal": "2026-09-06 11:59:00",
                "epoch": int(datetime(2026,9,6,11,59).timestamp()),
                "imperial": {"tempHigh": 91.0, "tempLow": 89.0, "tempAvg": 90.5, "windgustHigh": 5.0},
            },
            {
                "obsTimeLocal": "2026-09-06 12:59:00",
                "epoch": int(datetime(2026,9,6,12,59).timestamp()),
                "imperial": {"tempHigh": 92.0, "tempLow": 90.0, "tempAvg": 91.0, "windgustHigh": 5.0},
            },
        ]}

        def fake_get(url, timeout=15.0):
            if "/observations/hourly/7day" in url:
                return recent
            raise AssertionError("Fallback should not be required")

        with patch.object(wunderground_weather, "_get_json", side_effect=fake_get):
            wunderground_weather.fetch_summary(cfg, wx)

        self.assertAlmostEqual(wx.today_high_f, 99.1)
        self.assertAlmostEqual(wx.today_low_f, 72.7)
        self.assertAlmostEqual(wx.max_daily_gust_mph, 8.1)
        self.assertAlmostEqual(wx.yesterday_temp_f, 90.5)
        self.assertAlmostEqual(wx.from_yesterday_f, 4.5)
        self.assertTrue(wx.summary_valid)
        self.assertIn("hourly/7day", wx.summary_source)

    def test_wu_uses_provider_local_time_not_host_epoch_day(self):
        cfg = AppConfig(wu_api_key="key", wu_station_id="KTEST1")
        wx = WeatherData(
            temp_f=80.0, gust_mph=2.0,
            date_utc_ms=int(datetime(2026,9,8,2,30).timestamp()*1000),
            valid=True,
            obs_time_local="2026-09-07 22:30:00",
        )
        recent = {"observations": [
            {"obsTimeLocal": "2026-09-07 21:59:00", "imperial": {"tempHigh": 84.0, "tempLow": 70.0, "tempAvg": 79.0}},
            {"obsTimeLocal": "2026-09-06 21:59:00", "imperial": {"tempHigh": 78.0, "tempLow": 74.0, "tempAvg": 76.0}},
        ]}

        with patch.object(wunderground_weather, "_get_json", return_value=recent):
            wunderground_weather.fetch_summary(cfg, wx)

        self.assertAlmostEqual(wx.today_high_f, 84.0)
        self.assertAlmostEqual(wx.today_low_f, 70.0)
        self.assertAlmostEqual(wx.from_yesterday_f, 4.0)

    def test_wu_falls_back_to_archived_history(self):
        cfg = AppConfig(wu_api_key="key", wu_station_id="KTEST1")
        wx = WeatherData(
            temp_f=95.0, gust_mph=4.0,
            date_utc_ms=int(datetime(2026,9,7,12,0).timestamp()*1000),
            valid=True,
            obs_time_local="2026-09-07 12:00:00",
        )

        def fake_get(url, timeout=15.0):
            if "/observations/hourly/7day" in url or "/observations/all/1day" in url:
                return {"observations": []}
            if "/history/daily" in url:
                return {"observations": [{"obsTimeLocal":"2026-09-07 00:00:00","imperial":{
                    "tempHigh": 98.0, "tempLow": 70.0, "tempAvg": 84.0, "windgustHigh": 9.0
                }}]}
            if "/history/all" in url:
                return {"observations": [{"obsTimeLocal":"2026-09-06 12:01:00","imperial":{
                    "tempHigh": 92.0, "tempLow": 90.0, "tempAvg": 91.0
                }}]}
            raise AssertionError(url)

        with patch.object(wunderground_weather, "_get_json", side_effect=fake_get):
            wunderground_weather.fetch_summary(cfg, wx)

        self.assertAlmostEqual(wx.today_high_f, 98.0)
        self.assertAlmostEqual(wx.today_low_f, 70.0)
        self.assertAlmostEqual(wx.from_yesterday_f, 4.0)
        self.assertIn("history", wx.summary_source)


if __name__ == "__main__":
    unittest.main()
