import unittest

from emulator.app_controller import EmulatorApp
from emulator.display_ui import waveshare_7c_svg


class Waveshare7CBoxTests(unittest.TestCase):
    def setUp(self):
        self.app = EmulatorApp(verbose=False)
        self.app.apply_preset("heat")

    def test_native_dimensions_and_core_cards(self):
        svg = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('width="800"', svg)
        self.assertIn('height="480"', svg)
        self.assertIn('x="33" y="82" width="427" height="225"', svg)
        self.assertIn('TEMP', svg)
        self.assertIn('HUMIDITY', svg)
        self.assertIn('DEW POINT', svg)
        self.assertIn('FROM YDAY', svg)
        self.assertIn('DIRECTION', svg)
        self.assertIn('HIGH / LOW F', svg)

    def test_today_tomorrow_rotation(self):
        today = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        tomorrow = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=30)
        self.assertIn('TODAY', today)
        self.assertIn('TOMORROW', tomorrow)

    def test_dynamic_heat_palette(self):
        self.app.wx.temp_f = 105.0
        self.app.wx.humidity = 70.0
        from emulator.weather_math import recompute
        recompute(self.app.wx)
        svg = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertTrue('#d83b35' in svg or '#b21585' in svg)

    def test_wind_chill_palette_and_title(self):
        self.app.apply_preset("wind")
        svg = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('WIND CHILL', svg)
        self.assertTrue(any(c in svg for c in ('#124f86', '#4ea6da', '#2569b8', '#6c3aa8')))

    def test_waiting_state(self):
        self.app.apply_preset("waiting")
        svg = waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('WAITING', svg)
        self.assertIn('OFFLINE', svg)

    def test_controller_exposes_renderer(self):
        svg = self.app.render_waveshare_7c()
        self.assertIn('viewBox="0 0 800 480"', svg)


if __name__ == '__main__':
    unittest.main()
