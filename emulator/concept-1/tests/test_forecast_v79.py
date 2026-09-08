import math
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from emulator.app_state import AppConfig, WeatherData
from emulator import ambient_weather, wunderground_weather, forecast_weather
from emulator.display_ui import tdisplay_svg, waveshare_svg
from emulator.weather_math import recompute


class ForecastV79Tests(unittest.TestCase):
    def _weather(self):
        wx = WeatherData(
            temp_f=88.0,
            humidity=55.0,
            wind_mph=2.0,
            gust_mph=4.0,
            wind_dir_deg=180.0,
            from_yesterday_f=2.0,
            today_high_f=111.0,  # deliberately different from forecast
            today_low_f=22.0,
            latitude=33.53,
            longitude=-82.13,
            date_utc_ms=1760000000000,
            valid=True,
        )
        recompute(wx)
        return wx

    def test_forecast_fetch_matches_production_query_and_fields(self):
        wx = self._weather()
        seen = {}

        def fake_get(url, timeout=15.0):
            seen['url'] = url
            return {
                'daily': {
                    'temperature_2m_max': [95.5, 91.25],
                    'temperature_2m_min': [70.0, 68.5],
                }
            }, 200

        with patch.object(forecast_weather, '_get_json', side_effect=fake_get):
            code = forecast_weather.fetch_forecast_high_low(wx)

        self.assertEqual(code, 200)
        q = parse_qs(urlparse(seen['url']).query)
        self.assertEqual(q['daily'][0], 'temperature_2m_max,temperature_2m_min')
        self.assertEqual(q['temperature_unit'][0], 'fahrenheit')
        self.assertEqual(q['timezone'][0], 'auto')
        self.assertEqual(q['forecast_days'][0], '2')
        self.assertEqual(wx.forecast_today_high_f, 95.5)
        self.assertEqual(wx.forecast_today_low_f, 70.0)
        self.assertEqual(wx.forecast_tomorrow_high_f, 91.25)
        self.assertEqual(wx.forecast_tomorrow_low_f, 68.5)
        self.assertTrue(wx.forecast_valid)

    def test_forecast_card_alternates_every_30_seconds(self):
        wx = self._weather()
        wx.forecast_valid = True
        wx.forecast_tomorrow_high_f = 90.0
        wx.forecast_tomorrow_low_f = 65.0
        self.assertFalse(forecast_weather.forecast_shows_tomorrow(wx, 0.0))
        self.assertFalse(forecast_weather.forecast_shows_tomorrow(wx, 29.999))
        self.assertTrue(forecast_weather.forecast_shows_tomorrow(wx, 30.0))
        self.assertTrue(forecast_weather.forecast_shows_tomorrow(wx, 59.999))
        self.assertFalse(forecast_weather.forecast_shows_tomorrow(wx, 60.0))

    def test_display_uses_forecast_not_observed_summary(self):
        cfg = AppConfig(station_name='Cronin Farm')
        wx = self._weather()
        wx.forecast_valid = True
        wx.forecast_today_high_f = 95.0
        wx.forecast_today_low_f = 70.0
        wx.forecast_tomorrow_high_f = 91.0
        wx.forecast_tomorrow_low_f = 68.0

        t_today = tdisplay_svg(cfg, wx, forecast_elapsed_seconds=0)
        t_tomorrow = tdisplay_svg(cfg, wx, forecast_elapsed_seconds=30)
        w_today = waveshare_svg(cfg, wx, forecast_elapsed_seconds=0)
        w_tomorrow = waveshare_svg(cfg, wx, forecast_elapsed_seconds=30)

        self.assertIn('95° / 70°', t_today)
        self.assertIn('TODAY HIGH / LOW', t_today)
        self.assertIn('91° / 68°', t_tomorrow)
        self.assertIn('TOMORROW HIGH / LOW', t_tomorrow)
        self.assertNotIn('111.0 / 22.0F', t_today)

        self.assertIn('95°', w_today)
        self.assertIn('TODAY', w_today)
        self.assertIn('91°', w_tomorrow)
        self.assertIn('TOMORROW', w_tomorrow)

    def test_ambient_current_extracts_forecast_coordinates(self):
        cfg = AppConfig(
            ambient_application_key='app',
            ambient_api_key='api',
            ambient_mac_address='AA:BB:CC',
        )
        devices = [{
            'macAddress': 'AA:BB:CC',
            'info': {
                'name': 'Ambient Test',
                'coords': {'coords': {'lat': 33.5, 'lon': -82.1}},
            },
            'lastData': {
                'tempf': 80.0,
                'humidity': 50.0,
                'windspeedmph': 1.0,
                'dateutc': 1760000000000,
            },
        }]
        with patch.object(ambient_weather, '_get_json', return_value=devices):
            wx, mac, name = ambient_weather.fetch_current(cfg)
        self.assertEqual(mac, 'AA:BB:CC')
        self.assertEqual(name, 'Ambient Test')
        self.assertAlmostEqual(wx.latitude, 33.5)
        self.assertAlmostEqual(wx.longitude, -82.1)

    def test_wu_current_extracts_forecast_coordinates(self):
        cfg = AppConfig(wu_api_key='key', wu_station_id='KTEST1')
        doc = {'observations': [{
            'stationID': 'KTEST1',
            'neighborhood': 'WU Test',
            'epoch': 1760000000,
            'obsTimeLocal': '2026-09-07 12:00:00',
            'humidity': 50.0,
            'winddir': 180.0,
            'lat': 33.6,
            'lon': -82.2,
            'imperial': {
                'temp': 80.0,
                'dewpt': 60.0,
                'windSpeed': 1.0,
                'windGust': 2.0,
            },
        }]}
        with patch.object(wunderground_weather, '_get_json', return_value=doc):
            wx, name = wunderground_weather.fetch_current(cfg)
        self.assertEqual(name, 'WU Test')
        self.assertAlmostEqual(wx.latitude, 33.6)
        self.assertAlmostEqual(wx.longitude, -82.2)

    def test_controller_live_poll_updates_forecast_after_provider(self):
        from emulator.app_controller import EmulatorApp
        import emulator.app_controller as app_controller

        app = EmulatorApp(verbose=False)
        app.config.data_mode = "live"
        app.config.weather_source = "ambient"
        app.config.ambient_application_key = "app"
        app.config.ambient_api_key = "api"

        current = self._weather()
        current.latitude = 33.53
        current.longitude = -82.13

        def fake_provider(cfg, previous):
            return current, ""

        def fake_forecast(wx):
            wx.forecast_today_high_f = 94.0
            wx.forecast_today_low_f = 69.0
            wx.forecast_tomorrow_high_f = 90.0
            wx.forecast_tomorrow_low_f = 67.0
            wx.forecast_valid = True
            return 200

        with patch.object(app_controller, "poll", side_effect=fake_provider), \
             patch.object(app_controller, "fetch_forecast_high_low", side_effect=fake_forecast), \
             patch.object(app_controller, "save_config"):
            app.poll_provider()

        self.assertTrue(app.wx.forecast_valid)
        self.assertEqual(app.wx.forecast_today_high_f, 94.0)
        self.assertEqual(app.last_forecast_http_code, 200)
        status = app.status_payload()
        self.assertEqual(status["forecast_source"], "Open-Meteo")
        self.assertEqual(status["forecast_today_high_f"], 94.0)


if __name__ == '__main__':
    unittest.main()
