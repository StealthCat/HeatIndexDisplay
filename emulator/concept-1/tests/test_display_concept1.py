import unittest
from emulator.app_controller import EmulatorApp
from emulator.display_ui import tdisplay_svg, waveshare_svg
from emulator.weather_math import recompute

class Concept1DisplayTests(unittest.TestCase):
    def setUp(self):
        self.app = EmulatorApp(verbose=False)
        self.app.apply_preset("heat")

    def set_100_heat_index(self):
        self.app.wx.temp_f = 88.2
        self.app.wx.humidity = 68.0
        self.app.wx.wind_mph = 0.0
        recompute(self.app.wx)

    def test_tdisplay_concept1_features(self):
        svg = tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        for literal in [
            "CURRENT CONDITIONS", "TEMPERATURE", "HUMIDITY", "DEW POINT",
            "VS YDAY", "W/G MPH", "TODAY HIGH / LOW", "ONLINE"
        ]:
            self.assertIn(literal, svg)
        self.assertIn('fill="url(#heroCurrent)"', svg)
        self.assertIn('id="heroCurrent"', svg)

    def test_waveshare_concept1_features(self):
        svg = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        for literal in [
            "CURRENT CONDITIONS", ">TEMP</text>", ">HUMIDITY</text>",
            ">DEW POINT</text>", ">FROM YDAY</text>", ">WIND</text>",
            ">DIRECTION</text>", ">TODAY</text>", ">ONLINE</text>"
        ]:
            self.assertIn(literal, svg)

    def test_waveshare_100_matches_firmware_group(self):
        self.set_100_heat_index()
        svg = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('>100</text>', svg)
        self.assertIn('cx="119" cy="123" r="3"', svg)
        self.assertIn('x="125" y="142"', svg)
        self.assertNotIn('M10 2L18 17H2z', svg)

    def test_tdisplay_100_keeps_unit_inside_panel(self):
        self.set_100_heat_index()
        svg = tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('x="98" y="98"', svg)
        self.assertIn('cx="133" cy="83" r="3"', svg)
        self.assertIn('x="145" y="101"', svg)
        self.assertNotIn('M10 2L18 17H2z', svg)

    def test_forecast_alternates(self):
        today = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        tomorrow = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=30)
        self.assertIn(">TODAY</text>", today)
        self.assertIn(">TOMORROW</text>", tomorrow)

    def test_wind_chill_uses_cold_palette(self):
        self.app.apply_preset("wind")
        svg = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn("WIND CHILL", svg)
        self.assertIn('fill="url(#heroCurrent)"', svg)
        self.assertIn('stop-color="#124f86"', svg)
        self.assertIn(">COLD</text>", svg)

if __name__ == "__main__":
    unittest.main()
