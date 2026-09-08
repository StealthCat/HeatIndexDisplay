import unittest
from pathlib import Path
from emulator.app_controller import EmulatorApp
from emulator.display_ui import tdisplay_svg, waveshare_svg, waveshare_7c_svg

ROOT = Path(__file__).resolve().parents[3]

class FirmwareVisualParityTests(unittest.TestCase):
    def setUp(self):
        self.app = EmulatorApp(verbose=False)
        self.app.apply_preset("heat")

    def test_risk_pills_have_no_legacy_warning_icon(self):
        for render in (tdisplay_svg, waveshare_svg, waveshare_7c_svg):
            svg = render(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
            self.assertNotIn("M10 2L18 17H2z", svg)

    def test_current_conditions_headers_match_firmware(self):
        self.assertIn("CURRENT CONDITIONS", tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertIn("CURRENT CONDITIONS", waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertIn("CURRENT CONDITIONS", waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertNotIn(">WEATHER STATION</text>", waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))

    def test_production_card_and_pill_fills(self):
        for render in (tdisplay_svg, waveshare_svg, waveshare_7c_svg):
            svg = render(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
            self.assertIn("#041622", svg)
            self.assertIn("#071d2c", svg)
            self.assertIn('x2="0" y2="1"', svg)
            self.assertNotIn('fill="url(#riskCurrent)"', svg)

    def test_firmware_sources_contain_current_pill_contract(self):
        targets = [
            ROOT / "T-Display-S3/src/display_ui.cpp",
            ROOT / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp",
            ROOT / "Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp",
        ]
        for path in targets:
            src = path.read_text()
            self.assertIn("apparentRiskLabel()", src)
            self.assertNotIn("ICON_ALERT", src)
        self.assertIn('"CURRENT CONDITIONS"', targets[1].read_text())

if __name__ == "__main__":
    unittest.main()
