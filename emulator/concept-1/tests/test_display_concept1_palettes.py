import unittest

from emulator.app_controller import EmulatorApp
from emulator.display_ui import _hero_palette, tdisplay_svg, waveshare_svg
from emulator.weather_math import recompute, apparent_outdoor_f

class Concept1PaletteTests(unittest.TestCase):
    def setUp(self):
        self.app = EmulatorApp(verbose=False)

    def heat_case(self, temp, humidity):
        self.app.apply_preset("heat")
        self.app.wx.temp_f = temp
        self.app.wx.humidity = humidity
        self.app.wx.wind_mph = 0.0
        recompute(self.app.wx)
        return apparent_outdoor_f(self.app.wx), _hero_palette(self.app.wx)

    def cold_case(self, temp, wind):
        self.app.apply_preset("wind")
        self.app.wx.temp_f = temp
        self.app.wx.wind_mph = wind
        self.app.wx.gust_mph = wind
        recompute(self.app.wx)
        return apparent_outdoor_f(self.app.wx), _hero_palette(self.app.wx)

    def test_heat_palette_progression(self):
        cases = [
            (70.5, 48.0, "#287a45", 80.0),
            (84.0, 30.0, "#c59b17", 90.0),
            (89.5, 53.0, "#dd751d", 103.0),
            (89.5, 78.0, "#d83b35", 125.0),
            (117.0, 24.0, "#b21585", 999.0),
        ]
        for temp, rh, expected, upper in cases:
            apparent, palette = self.heat_case(temp, rh)
            self.assertEqual(palette["top"], expected)
            self.assertLess(apparent, upper)

    def test_wind_chill_palette_progression(self):
        cases = [
            (14.0, 43.5, "#124f86", -18.0),
            (9.0, 59.5, "#4ea6da", -32.0),
            (-8.0, 25.5, "#2569b8", -48.0),
            (-12.0, 58.0, "#6c3aa8", -999.0),
        ]
        for temp, wind, expected, lower in cases:
            apparent, palette = self.cold_case(temp, wind)
            self.assertEqual(palette["top"], expected)
            if lower != -999.0:
                self.assertGreater(apparent, lower)

    def test_renderers_use_same_dynamic_gradient(self):
        # Deliberately target the red Heat Index band (~110°F).
        self.app.apply_preset("heat")
        self.app.wx.temp_f = 89.5
        self.app.wx.humidity = 78.0
        self.app.wx.wind_mph = 0.0
        recompute(self.app.wx)

        for svg in (
            tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0),
            waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0),
        ):
            self.assertIn('id="heroCurrent"', svg)
            self.assertIn('stop-color="#d83b35"', svg)
            self.assertIn('fill="url(#heroCurrent)"', svg)
            self.assertIn('id="riskCurrent"', svg)
            self.assertIn('stop-color="#52120e"', svg)

if __name__ == "__main__":
    unittest.main()
